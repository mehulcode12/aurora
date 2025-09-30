"""
Real-Time Audio AI Agent - Full Duplex Pattern
Using Cerebras for Ultra-Fast LLM Inference

Requirements:
pip install sounddevice numpy webrtcvad faster-whisper TTS cerebras_cloud_sdk torch

Before running:
1. Get free Cerebras API key: https://cloud.cerebras.ai/
2. Set environment variable: export CEREBRAS_API_KEY=your_key_here
"""

import sounddevice as sd
import numpy as np
import webrtcvad
import asyncio
import queue
import struct
import wave
import tempfile
import os
from faster_whisper import WhisperModel
from TTS.api import TTS
from cerebras.cloud.sdk import Cerebras
import os
from pathlib import Path
import threading

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
    CEREBRAS_MODEL = "llama3.1-8b"  # Ultra-fast inference on Cerebras
    TTS_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"  # Fast, good quality

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

class AudioPlayer:
    """Plays audio output"""
    
    def __init__(self, config: Config):
        self.config = config
        self.playback_queue = queue.Queue()
        self.is_playing = False
        
    def play(self, audio_file: str):
        """Add audio file to playback queue"""
        self.playback_queue.put(audio_file)
    
    def playback_worker(self):
        """Worker thread for playing audio"""
        while True:
            try:
                audio_file = self.playback_queue.get(timeout=1)
                if audio_file is None:  # Stop signal
                    break
                
                # Read and play audio file
                data, fs = self._read_audio_file(audio_file)
                sd.play(data, fs)
                sd.wait()
                
                # Cleanup temp file
                try:
                    os.unlink(audio_file)
                except:
                    pass
                    
            except queue.Empty:
                continue
    
    def _read_audio_file(self, filename):
        """Read audio file"""
        with wave.open(filename, 'rb') as wf:
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio, sample_rate
    
    def start(self):
        """Start playback thread"""
        self.playback_thread = threading.Thread(target=self.playback_worker, daemon=True)
        self.playback_thread.start()
    
    def stop(self):
        """Stop playback thread"""
        self.playback_queue.put(None)

# ============================================================================
# AI COMPONENTS
# ============================================================================
class SpeechToText:
    """Converts speech to text using Faster Whisper"""
    
    def __init__(self, config: Config):
        print(f"Loading Whisper model '{config.WHISPER_MODEL}'...")
        self.model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        print("✓ Whisper loaded")
    
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
            print(" CEREBRAS_API_KEY not found!")
            print("Get your free API key at: https://cloud.cerebras.ai/")
            print("Then set it: export CEREBRAS_API_KEY=your_key_here")
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
                max_tokens=1000 if is_urgent else 2000,  # Allow longer critical responses
                temperature=0.3,  # Lower temperature for more reliable safety instructions
            )
            
            assistant_message = response.choices[0].message.content
            
            # Log critical situations
            if is_urgent:
                print(f"\n  CRITICAL SITUATION DETECTED")
                print(f" Alert: Emergency response triggered")
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 12:  # Keep system prompt + last 10 messages
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            return assistant_message
            
        except Exception as e:
            print(f" Cerebras API error: {e}")
            return "Emergency system error. Please call your supervisor immediately and follow standard emergency procedures."

class TextToSpeech:
    """Converts text to speech using Coqui TTS"""
    
    def __init__(self, config: Config):
        print(f"Loading TTS model '{config.TTS_MODEL}'...")
        self.tts = TTS(config.TTS_MODEL)
        print("✓ TTS loaded")
        self.temp_dir = tempfile.gettempdir()
    
    def synthesize(self, text: str) -> str:
        """Convert text to speech and return audio file path"""
        # Create temp file
        output_file = os.path.join(self.temp_dir, f"tts_{id(text)}.wav")
        
        # Generate speech
        self.tts.tts_to_file(text=text, file_path=output_file)
        
        return output_file

# ============================================================================
# MAIN AGENT
# ============================================================================
class RealTimeAgent:
    """Full duplex real-time audio agent"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        print("\n Initializing Real-Time Audio Agent...")
        self.audio_capture = AudioCapture(config)
        self.audio_player = AudioPlayer(config)
        self.stt = SpeechToText(config)
        self.llm = LanguageModel(config)
        self.tts = TextToSpeech(config)
        
        # State
        self.is_running = False
        self.speech_buffer = []
        self.silence_frames = 0
        
        print("✓ Agent ready!\n")
    
    def process_speech(self):
        """Process accumulated speech buffer"""
        if not self.speech_buffer:
            return
        
        # Concatenate audio chunks
        audio_data = np.concatenate(self.speech_buffer)
        self.speech_buffer = []
        
        print("\n Processing speech...")
        
        # 1. Speech to Text
        print("  → Transcribing...")
        text = self.stt.transcribe(audio_data, self.config.SAMPLE_RATE)
        
        if not text:
            print("  ✗ No speech detected")
            return
        
        print(f"  👤 You: {text}")
        
        # 2. LLM Response
        print("  → Generating response...")
        response = self.llm.generate_response(text)
        print(f"  AI: {response}")
        
        # 3. Text to Speech
        print("  → Synthesizing speech...")
        audio_file = self.tts.synthesize(response)
        
        # 4. Play audio
        print("  → Playing response...")
        self.audio_player.play(audio_file)
    
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
        print("AURORA - EMERGENCY FIELD ASSISTANT")
        print("=" * 70)
        print("\nInstructions:")
        print("  • Describe your situation clearly")
        print("  • Mention specific locations (zones, valves, equipment)")
        print("  • Aurora will provide immediate safety guidance")
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
            print("\n\nStopping agent...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False
        self.audio_capture.stop()
        self.audio_player.stop()
        print(" Agent stopped")

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    config = Config()
    agent = RealTimeAgent(config)
    
    try:
        agent.run()
    except Exception as e:
        print(f"\n Error: {e}")
        print("\nMake sure you have:")
        print("1. Installed all dependencies: pip install sounddevice numpy webrtcvad faster-whisper TTS cerebras_cloud_sdk torch")
        print("2. Set your Cerebras API key: export CEREBRAS_API_KEY=your_key_here")
        print("3. Get free API key at: https://cloud.cerebras.ai/")


# # Add at the end of agent.py
# def test_aurora():
#     """Test Aurora with simulated scenarios"""
#     config = Config()
#     llm = LanguageModel(config)
    
#     test_scenarios = [
#         "Strong smell of gas in Zone B near Valve 3",
#         "Worker fell from ladder, bleeding from head",
#         "Press machine making loud noise and smoking",
#         "Small fire in electrical panel Zone C",
#         "Chemical barrel leaking in storage room"
#     ]
    
#     for scenario in test_scenarios:
#         print(f"\n{'='*70}")
#         print(f"👤 Worker: {scenario}")
#         response = llm.generate_response(scenario)
#         print(f"🤖 Aurora: {response}")
#         print(f"{'='*70}")

# if __name__ == "__main__":
#     # Uncomment to test without audio:
#     # test_aurora()
    
#     # Normal operation:
#     config = Config()
#     agent = RealTimeAgent(config)
#     agent.run()