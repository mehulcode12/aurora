"""
Real-Time Audio AI Agent - Full Duplex with STREAMING Audio Output
Using Cerebras for Ultra-Fast LLM Inference + Streaming TTS

Requirements:
pip install sounddevice numpy webrtcvad faster-whisper TTS cerebras_cloud_sdk torch python-dotenv pydub

Before running:
1. Get free Cerebras API key: https://cloud.cerebras.ai/
2. Create .env file with: CEREBRAS_API_KEY=your_key_here
   OR set environment variable: export CEREBRAS_API_KEY=your_key_here
"""

import sounddevice as sd
import numpy as np
import webrtcvad
import asyncio
import queue
import wave
import tempfile
import os
from faster_whisper import WhisperModel
from TTS.api import TTS
from cerebras.cloud.sdk import Cerebras
from pathlib import Path
import threading
import time
import requests
from urllib3.exceptions import IncompleteRead
from dotenv import load_dotenv
import re
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    # Audio settings
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_DURATION_MS = 30  # VAD works with 10, 20, or 30 ms frames
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
    
    # VAD settings
    VAD_AGGRESSIVENESS = 3  # 0-3, higher = more aggressive filtering
    SILENCE_DURATION_MS = 800  # Silence duration to consider speech ended
    
    # Model settings
    WHISPER_MODEL = "base"  # tiny, base, small, medium, large
    WHISPER_FALLBACK_MODEL = "tiny"  # Fallback if base fails to download
    CEREBRAS_MODEL = "llama3.1-8b"  # Ultra-fast inference on Cerebras
    TTS_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"  # Fast, good quality
    TTS_FALLBACK_MODEL = "tts_models/en/ljspeech/glow-tts"  # Alternative TTS model
    
    # Streaming settings
    ENABLE_STREAMING = True  # Enable sentence-by-sentence TTS streaming
    SENTENCE_CHUNK_SIZE = 1  # Process 1 sentence at a time for lowest latency
    
    # Download settings
    MAX_DOWNLOAD_RETRIES = 3
    DOWNLOAD_TIMEOUT = 300  # 5 minutes

# ============================================================================
# AUDIO COMPONENTS
# ============================================================================
class AudioCapture:
    """Captures audio from microphone with VAD"""
    
    def __init__(self, config: Config):
        self.config = config
        self.vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
        self.audio_queue = queue.Queue()
        self.is_running = False
        
    def callback(self, indata, frames, time, status):
        """Called for each audio chunk"""
        if status:
            print(f"Audio input status: {status}")
        
        # Convert to int16 for VAD
        audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
        
        # Check if speech is detected
        is_speech = self.vad.is_speech(
            audio_int16.tobytes(), 
            self.config.SAMPLE_RATE
        )
        
        self.audio_queue.put((audio_int16, is_speech))
    
    def start(self):
        """Start capturing audio"""
        self.is_running = True
        self.stream = sd.InputStream(
            samplerate=self.config.SAMPLE_RATE,
            channels=self.config.CHANNELS,
            dtype=np.float32,
            blocksize=self.config.CHUNK_SIZE,
            callback=self.callback
        )
        self.stream.start()
        print("🎤 Microphone started. Speak now...")
    
    def stop(self):
        """Stop capturing audio"""
        self.is_running = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()

class StreamingAudioPlayer:
    """Plays audio output with streaming support for lowest latency"""
    
    def __init__(self, config: Config):
        self.config = config
        self.playback_queue = queue.Queue()
        self.is_playing = False
        self.current_stream = None
        self.stream_lock = threading.Lock()
        
    def play(self, audio_file: str):
        """Add audio file to playback queue"""
        self.playback_queue.put(('file', audio_file))
    
    def play_audio_data(self, audio_data: np.ndarray, sample_rate: int):
        """Play audio data directly (for streaming)"""
        self.playback_queue.put(('data', audio_data, sample_rate))
    
    def playback_worker(self):
        """Worker thread for playing audio with streaming support"""
        while True:
            try:
                item = self.playback_queue.get(timeout=1)
                if item is None:  # Stop signal
                    break
                
                if item[0] == 'file':
                    # Play from file
                    audio_file = item[1]
                    data, fs = self._read_audio_file(audio_file)
                    if data is not None and fs is not None:
                        self._play_audio(data, fs)
                    
                    # Cleanup temp file
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
                        
                elif item[0] == 'data':
                    # Play audio data directly (streaming)
                    audio_data, sample_rate = item[1], item[2]
                    self._play_audio(audio_data, sample_rate)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"  ⚠️ Playback error: {e}")
    
    def _play_audio(self, data: np.ndarray, sample_rate: int):
        """Play audio data through speakers"""
        try:
            with self.stream_lock:
                sd.play(data, sample_rate)
                sd.wait()
        except Exception as e:
            print(f"  ⚠️ Audio playback failed: {e}")
    
    def _read_audio_file(self, filename):
        """Read audio file with error handling"""
        try:
            if not os.path.exists(filename):
                print(f"  ⚠️ Audio file not found: {filename}")
                return None, None
            
            file_size = os.path.getsize(filename)
            if file_size < 1000:  # Less than 1KB is suspicious
                print(f"  ⚠️ Audio file too small: {file_size} bytes")
                return None, None
            
            with wave.open(filename, 'rb') as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                
                if not frames:
                    print(f"  ⚠️ Empty audio file: {filename}")
                    return None, None
                
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Check if audio is all zeros (silence/gibberish)
                if np.max(np.abs(audio)) < 0.001:
                    print(f"  ⚠️ Audio appears to be silence: {filename}")
                    return None, None
                
                return audio, sample_rate
                
        except Exception as e:
            print(f"  ✗ Error reading audio file {filename}: {e}")
            return None, None
    
    def start(self):
        """Start playback thread"""
        self.playback_thread = threading.Thread(target=self.playback_worker, daemon=True)
        self.playback_thread.start()
    
    def stop(self):
        """Stop playback thread"""
        self.playback_queue.put(None)

# ============================================================================
# MODEL DOWNLOADER
# ============================================================================
class ModelDownloader:
    """Handles robust model downloading with retry logic"""
    
    @staticmethod
    def download_whisper_model(model_name: str, max_retries: int = None) -> bool:
        """Download Whisper model with retry logic"""
        if max_retries is None:
            max_retries = 3  # Default retries
            
        print(f"Attempting to download Whisper model '{model_name}'...")
        
        for attempt in range(max_retries):
            try:
                print(f"  Attempt {attempt + 1}/{max_retries}...")
                
                # Set environment variables for better download handling
                os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
                
                # Try to download the model
                model = WhisperModel(model_name, device="cpu", compute_type="int8")
                print(f"✓ Successfully downloaded model '{model_name}'")
                return True
                
            except (IncompleteRead, requests.exceptions.ChunkedEncodingError, 
                   requests.exceptions.ConnectionError, Exception) as e:
                print(f"  ✗ Download attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    print(f"  ✗ All download attempts failed for model '{model_name}'")
                    return False
        
        return False
    
    @staticmethod
    def check_model_cached(model_name: str) -> bool:
        """Check if model is already cached locally"""
        try:
            from huggingface_hub import snapshot_download
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_cache_path = os.path.join(cache_dir, f"models--Systran--faster-whisper-{model_name}")
            
            if os.path.exists(model_cache_path):
                print(f"✓ Found cached model '{model_name}'")
                return True
        except Exception:
            pass
        return False

# ============================================================================
# AI COMPONENTS
# ============================================================================
class SpeechToText:
    """Converts speech to text using Faster Whisper"""
    
    def __init__(self, config: Config):
        print(f"Loading Whisper model '{config.WHISPER_MODEL}'...")
        
        # First check if model is already cached
        if ModelDownloader.check_model_cached(config.WHISPER_MODEL):
            try:
                self.model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
                print("✓ Whisper loaded from cache")
                return
            except Exception as e:
                print(f"  ✗ Failed to load from cache: {e}")
                print("  Attempting fresh download...")
        
        # Try to download with retry logic
        if ModelDownloader.download_whisper_model(config.WHISPER_MODEL, config.MAX_DOWNLOAD_RETRIES):
            try:
                self.model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
                print("✓ Whisper loaded successfully")
            except Exception as e:
                print(f"✗ Failed to initialize Whisper model: {e}")
                raise
        else:
            # Try fallback model
            print(f"\nTrying fallback model '{config.WHISPER_FALLBACK_MODEL}'...")
            if ModelDownloader.download_whisper_model(config.WHISPER_FALLBACK_MODEL, config.MAX_DOWNLOAD_RETRIES):
                try:
                    self.model = WhisperModel(config.WHISPER_FALLBACK_MODEL, device="cpu", compute_type="int8")
                    print(f"✓ Whisper fallback model '{config.WHISPER_FALLBACK_MODEL}' loaded successfully")
                except Exception as e:
                    print(f"✗ Failed to initialize fallback model: {e}")
                    raise
            else:
                raise RuntimeError("Failed to download any Whisper model after multiple attempts")
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Transcribe audio to text"""
        # Whisper expects float32 normalized to [-1, 1]
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        segments, info = self.model.transcribe(
            audio_float,
            language="en",
            beam_size=1,  # Faster inference
            vad_filter=True
        )
        
        text = " ".join([segment.text for segment in segments])
        return text.strip()

class LanguageModel:
    """Interacts with Cerebras Cloud for ultra-fast LLM inference"""
    
    def __init__(self, config: Config):
        self.config = config
        self.conversation_history = []
        
        print(f"Initializing Cerebras LLM '{config.CEREBRAS_MODEL}'...")
        
        # Get API key from environment
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            print("❌ CEREBRAS_API_KEY not found!")
            print("Get your free API key at: https://cloud.cerebras.ai/")
            print("Then set it in .env file: CEREBRAS_API_KEY=your_key_here")
            raise ValueError("Missing CEREBRAS_API_KEY")
        
        # Initialize Cerebras client
        self.client = Cerebras(api_key=api_key)
        
        # Add system prompt for Aurora - Emergency Field Assistant
        self.conversation_history.append({
            "role": "system",
            "content": """You are Aurora, a fast AI field assistant for frontline workers in industrial/emergency situations.

Your core mission:
- Provide IMMEDIATE, ACTIONABLE safety guidance to workers
- Identify hazards quickly (gas leaks, fires, injuries, equipment failures)
- Give clear step-by-step instructions for emergency response
- Prioritize worker safety above all else

Response guidelines:
1. Be DIRECT and CONCISE - workers need fast answers, not explanations
2. Use imperative commands: "Evacuate", "Shut down", "Call emergency"
3. Keep responses under 4 short sentences unless critical details are needed
4. Structure urgent replies: Action → Safety → Alert
5. For emergencies, always include: evacuation steps, immediate actions, who to call
6. Mention specific zones, valves, equipment when the worker provides them
7. If situation is CRITICAL (gas leak, fire, injury), explicitly state severity

Zone layout:
- Zone A: Manufacturing floor, press machines
- Zone B: Gas line corridor, Valves 1-5
- Zone C: Chemical storage, flammable materials
- Zone D: Assembly line, low-risk area
- Zone E: Maintenance workshop
- Zone F: Loading dock

Emergency categories you handle:
- Gas leaks → evacuate, shut valves, eliminate ignition, call gas team + fire brigade
- Fire → evacuate, activate alarms, use extinguisher only if safe, call fire brigade
- Chemical spill → evacuate, contain if safe, call hazmat team
- Equipment failure → shut down equipment, isolate area, call maintenance
- Injury → first aid, call ambulance, don't move victim unless immediate danger
- Electrical → don't touch, shut off power if possible, call electrical team

Always assume the worker is in the field and needs actionable steps RIGHT NOW."""
        })
        
        print("✓ Cerebras connected (ultra-fast inference enabled)")
    
    def generate_response(self, user_input: str) -> str:
        """Generate emergency response from Cerebras LLM"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            # Detect urgency keywords for priority processing
            urgent_keywords = ['gas', 'leak', 'fire', 'injured', 'emergency', 'help', 'danger', 'smoke', 'bleeding']
            is_urgent = any(keyword in user_input.lower() for keyword in urgent_keywords)
            
            # Call Cerebras API - blazingly fast for emergency response!
            response = self.client.chat.completions.create(
                model=self.config.CEREBRAS_MODEL,
                messages=self.conversation_history,
                max_tokens=250 if is_urgent else 200,  # Allow longer critical responses
                temperature=0.3,  # Lower temperature for more reliable safety instructions
            )
            
            assistant_message = response.choices[0].message.content
            
            # Log critical situations
            if is_urgent:
                print(f"\n  ⚠️ CRITICAL SITUATION DETECTED")
                print(f"  📝 Alert: Emergency response triggered")
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 12:
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            return assistant_message
            
        except Exception as e:
            print(f"❌ Cerebras API error: {e}")
            return "Emergency system error. Please call your supervisor immediately and follow standard emergency procedures."

class StreamingTextToSpeech:
    """Converts text to speech with sentence-by-sentence streaming for lowest latency"""
    
    def __init__(self, config: Config):
        self.config = config
        self.temp_dir = tempfile.gettempdir()
        
        print(f"Loading TTS model '{config.TTS_MODEL}'...")
        try:
            self.tts = TTS(config.TTS_MODEL)
            print("✓ TTS loaded (streaming enabled)")
        except Exception as e:
            print(f"✗ Primary TTS model failed: {e}")
            print(f"Trying fallback TTS model '{config.TTS_FALLBACK_MODEL}'...")
            try:
                self.tts = TTS(config.TTS_FALLBACK_MODEL)
                print("✓ Fallback TTS loaded (streaming enabled)")
            except Exception as e2:
                print(f"✗ Fallback TTS also failed: {e2}")
                raise RuntimeError("Both TTS models failed to load")
    
    def split_into_sentences(self, text: str) -> list:
        """Split text into sentences for streaming"""
        # Use regex to split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def sanitize_text(self, text: str) -> str:
        """Clean text to prevent TTS gibberish"""
        if not text or not text.strip():
            return ""
        
        # Remove problematic characters
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{2,}', '.', text)
        text = re.sub(r'[^\w\s.,!?\-:;()\']', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure proper punctuation
        if text and not text[-1] in '.!?':
            text += '.'
        
        return text
    
    def synthesize_sentence(self, sentence: str) -> tuple:
        """Synthesize a single sentence and return audio data + sample rate"""
        try:
            clean_text = self.sanitize_text(sentence)
            
            if not clean_text or len(clean_text) < 2:
                return None, None
            
            # Create temp file
            output_file = os.path.join(self.temp_dir, f"tts_stream_{int(time.time() * 1000000)}.wav")
            
            # Generate speech
            self.tts.tts_to_file(text=clean_text, file_path=output_file)
            
            # Read the generated audio immediately
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                with wave.open(output_file, 'rb') as wf:
                    sample_rate = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Cleanup
                try:
                    os.unlink(output_file)
                except:
                    pass
                
                return audio, sample_rate
            
            return None, None
            
        except Exception as e:
            print(f"  ⚠️ Sentence TTS failed: {e}")
            return None, None
    
    def synthesize_streaming(self, text: str, audio_player):
        """
        Synthesize text sentence-by-sentence and stream to audio player
        Returns immediately after starting, doesn't wait for completion
        """
        if not self.config.ENABLE_STREAMING:
            # Fallback to non-streaming
            return self.synthesize_batch(text)
        
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            print("  ⚠️ No valid sentences to synthesize")
            return
        
        print(f"  🎵 Streaming {len(sentences)} sentence(s)...")
        
        # Process sentences in a separate thread for true streaming
        def stream_worker():
            first_sentence = True
            for i, sentence in enumerate(sentences):
                if first_sentence:
                    print(f"  → Playing sentence 1/{len(sentences)} (streaming)...")
                    first_sentence = False
                
                audio_data, sample_rate = self.synthesize_sentence(sentence)
                
                if audio_data is not None and sample_rate is not None:
                    # Send directly to audio player - no waiting!
                    audio_player.play_audio_data(audio_data, sample_rate)
                else:
                    print(f"  ⚠️ Skipped sentence {i+1}")
        
        # Start streaming in background thread
        stream_thread = threading.Thread(target=stream_worker, daemon=True)
        stream_thread.start()
        
        # Return immediately - streaming happens in background!
        return stream_thread
    
    def synthesize_batch(self, text: str) -> str:
        """Fallback: synthesize entire text at once (non-streaming)"""
        try:
            clean_text = self.sanitize_text(text)
            
            if not clean_text:
                return None
            
            output_file = os.path.join(self.temp_dir, f"tts_batch_{int(time.time() * 1000)}.wav")
            self.tts.tts_to_file(text=clean_text, file_path=output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                return output_file
            
            return None
            
        except Exception as e:
            print(f"  ✗ Batch TTS failed: {e}")
            return None

# ============================================================================
# MAIN AGENT
# ============================================================================
class RealTimeAgent:
    """Full duplex real-time audio agent with streaming TTS"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        print("\n🚀 Initializing Real-Time Audio Agent (STREAMING MODE)...")
        self.audio_capture = AudioCapture(config)
        self.audio_player = StreamingAudioPlayer(config)
        self.stt = SpeechToText(config)
        self.llm = LanguageModel(config)
        self.tts = StreamingTextToSpeech(config)
        
        # State
        self.is_running = False
        self.speech_buffer = []
        self.silence_frames = 0
        
        print("✓ Agent ready! (Streaming audio enabled)\n")
    
    def process_speech(self):
        """Process accumulated speech buffer with streaming audio output"""
        if not self.speech_buffer:
            return
        
        # Concatenate audio chunks
        audio_data = np.concatenate(self.speech_buffer)
        self.speech_buffer = []
        
        print("\n🎯 Processing speech...")
        
        # 1. Speech to Text
        print("  → Transcribing...")
        start_time = time.time()
        text = self.stt.transcribe(audio_data, self.config.SAMPLE_RATE)
        stt_time = time.time() - start_time
        
        if not text:
            print("  ✗ No speech detected")
            return
        
        print(f"  👤 You: {text}")
        print(f"  ⏱️ STT took: {stt_time:.2f}s")
        
        # 2. LLM Response
        print("  → Generating response...")
        start_time = time.time()
        response = self.llm.generate_response(text)
        llm_time = time.time() - start_time
        
        print(f"  🤖 AI: {response}")
        print(f"  ⏱️ LLM took: {llm_time:.2f}s")
        
        # 3. Text to Speech (STREAMING!)
        print("  → Synthesizing speech (streaming)...")
        start_time = time.time()
        
        if self.config.ENABLE_STREAMING:
            # Stream audio sentence by sentence - LOWEST LATENCY!
            stream_thread = self.tts.synthesize_streaming(response, self.audio_player)
            tts_start_time = time.time() - start_time
            print(f"  ⏱️ First audio chunk started in: {tts_start_time:.2f}s")
            print(f"  🎵 Streaming audio in background...")
        else:
            # Fallback to batch processing
            audio_file = self.tts.synthesize_batch(response)
            if audio_file:
                self.audio_player.play(audio_file)
                print(f"  ⏱️ TTS completed in: {time.time() - start_time:.2f}s")
            else:
                print("  ⚠️ TTS failed")
    
    async def audio_processing_loop(self):
        """Main async loop for processing audio"""
        max_silence_frames = int(
            self.config.SILENCE_DURATION_MS / self.config.CHUNK_DURATION_MS
        )
        
        while self.is_running:
            try:
                # Get audio chunk (non-blocking)
                audio_chunk, is_speech = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.audio_capture.audio_queue.get,
                    True,  # block
                    0.1    # timeout
                )
                
                if is_speech:
                    self.speech_buffer.append(audio_chunk)
                    self.silence_frames = 0
                else:
                    if self.speech_buffer:
                        self.silence_frames += 1
                        
                        # If silence detected after speech, process it
                        if self.silence_frames >= max_silence_frames:
                            # Process in separate thread to not block audio capture
                            await asyncio.get_event_loop().run_in_executor(
                                None,
                                self.process_speech
                            )
                            self.silence_frames = 0
                            
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)
    
    def run(self):
        """Start the agent"""
        print("=" * 70)
        print("🚨 AURORA - EMERGENCY FIELD ASSISTANT (STREAMING MODE)")
        print("=" * 70)
        print("\nInstructions:")
        print("  • Describe your situation clearly")
        print("  • Mention specific locations (zones, valves, equipment)")
        print("  • Aurora will provide immediate safety guidance")
        print("  • ⚡ STREAMING: Audio starts playing within 1-2 seconds!")
        print("  • For critical emergencies, follow instructions immediately")
        print("  • Press Ctrl+C to stop")
        print("\n" + "=" * 70)
        print("\nExample: 'Strong smell of gas in Zone B near Valve 3'")
        print("=" * 70 + "\n")
        
        self.is_running = True
        
        # Start components
        self.audio_capture.start()
        self.audio_player.start()
        
        # Run async loop
        try:
            asyncio.run(self.audio_processing_loop())
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping agent...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False
        self.audio_capture.stop()
        self.audio_player.stop()
        print("✓ Agent stopped")

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    try:
        config = Config()
        agent = RealTimeAgent(config)
        agent.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Installed all dependencies: pip install sounddevice numpy webrtcvad faster-whisper TTS cerebras_cloud_sdk torch python-dotenv")
        print("2. Created .env file with: CEREBRAS_API_KEY=your_key_here")
        print("3. Get free API key at: https://cloud.cerebras.ai/")