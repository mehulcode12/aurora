# 🎓 Complete Guide: Real-Time Audio AI Agent

Let me break down **everything** that's happening in this system, step by step.

---

## 📋 Table of Contents
1. [High-Level Overview](#high-level-overview)
2. [Detailed Component Breakdown](#detailed-component-breakdown)
3. [How Data Flows](#how-data-flows)
4. [Setup & Installation Guide](#setup--installation-guide)
5. [Running the Agent](#running-the-agent)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 High-Level Overview

### What This System Does:
```
You speak → AI hears → AI thinks → AI responds → You hear
```

### The Magic:
- **Full Duplex** = Can listen while speaking (like a phone call)
- **Real-time** = Processes audio continuously, not in batches
- **Async** = Multiple things happen at once without blocking

---

## 🔍 Detailed Component Breakdown

### **1. Configuration (Config Class)**

```python
class Config:
    SAMPLE_RATE = 16000  # 16kHz - phone quality (enough for voice)
    CHANNELS = 1         # Mono audio (stereo not needed)
    CHUNK_DURATION_MS = 30  # Process audio every 30 milliseconds
    VAD_AGGRESSIVENESS = 3  # How aggressive to filter noise (0-3)
```

**What this means:**
- Audio is captured in **tiny 30ms chunks**
- Each chunk is only 480 samples (16000 Hz × 0.03 sec)
- This allows near-instant response to voice activity

---

### **2. AudioCapture Class** 
*Captures your voice from the microphone*

#### How It Works:

```python
def callback(self, indata, frames, time, status):
    # This function is called 33 times per second! (every 30ms)
    
    # Step 1: Convert audio to the right format
    audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
    
    # Step 2: Check if it's speech or noise
    is_speech = self.vad.is_speech(audio_int16.tobytes(), SAMPLE_RATE)
    
    # Step 3: Put it in a queue for processing
    self.audio_queue.put((audio_int16, is_speech))
```

**Key Concepts:**

**Voice Activity Detection (VAD):**
- Uses Google's WebRTC algorithm
- Filters out: keyboard clicks, background noise, silence
- Only processes actual speech
- Saves CPU and improves accuracy

**Queue Pattern:**
```
Microphone → [Callback] → Queue → [Processing Thread]
             (33x/sec)              (reads when ready)
```

**Why this matters:**
- Recording never stops (full duplex!)
- Processing happens separately
- No audio is lost

---

### **3. SpeechToText Class**
*Converts your voice to text*

```python
def transcribe(self, audio_data, sample_rate):
    # Uses Faster-Whisper (optimized version of OpenAI Whisper)
    segments, info = self.model.transcribe(
        audio_float,
        language="en",
        beam_size=1,  # Lower = faster (less accuracy)
        vad_filter=True  # Remove silence
    )
```

**What Happens:**
1. **Input:** Raw audio array (your voice recording)
2. **Process:** Neural network converts audio patterns to text
3. **Output:** "Hello, how are you?"

**Model Options:**
- `tiny` - 39M parameters, very fast, less accurate
- `base` - 74M parameters, **balanced** (we use this)
- `small` - 244M parameters, slower, more accurate
- `medium` - 769M parameters, much slower
- `large` - 1.5B parameters, slowest, best quality

**Performance:**
- Base model: ~1-2 seconds for 5 seconds of speech
- Runs on CPU (no GPU needed for demo)

---

### **4. LanguageModel Class**
*The AI brain that generates responses*

```python
def generate_response(self, user_input):
    # Add your message to conversation history
    self.conversation_history.append({"role": "user", "content": user_input})
    
    # Call Cerebras API
    response = self.client.chat.completions.create(
        model="llama3.1-8b",
        messages=self.conversation_history,
        max_tokens=200,  # Limit response length
        temperature=0.7  # Creativity level (0=robotic, 1=creative)
    )
```

**Conversation History:**
```python
[
    {"role": "system", "content": "You are a helpful AI..."},
    {"role": "user", "content": "What's the weather?"},
    {"role": "assistant", "content": "I don't have real-time data..."},
    {"role": "user", "content": "Tell me a joke"}  # Current input
]
```

**Why Cerebras?**
- **Speed:** 1000-2000 tokens/second
- Normal APIs: 40-80 tokens/second
- **Result:** Response in ~0.1-0.3 seconds instead of 2-5 seconds

**What the LLM does:**
1. Reads entire conversation history
2. Understands context
3. Generates natural response
4. Returns text: "Why did the chicken cross the road?..."

---

### **5. TextToSpeech Class**
*Converts AI text to natural voice*

```python
def synthesize(self, text):
    # Uses Tacotron2 + vocoder neural network
    output_file = "temp_speech.wav"
    self.tts.tts_to_file(text=text, file_path=output_file)
    return output_file
```

**How TTS Works:**
1. **Text Analysis:** Breaks down words, punctuation, emphasis
2. **Mel-Spectrogram:** Converts to frequency representation
3. **Vocoder:** Converts spectrogram to audio waveform
4. **Output:** Natural-sounding speech file

**Model Used:** Tacotron2-DDC
- Female voice (LJSpeech dataset)
- Clear, professional quality
- ~1-2 seconds per sentence

---

### **6. AudioPlayer Class**
*Plays AI responses through speakers*

```python
def playback_worker(self):
    while True:
        audio_file = self.playback_queue.get()  # Wait for audio
        data, fs = self._read_audio_file(audio_file)
        sd.play(data, fs)  # Play through speakers
        sd.wait()  # Wait until finished
```

**Queue System:**
```
TTS → [Queue] → Playback Thread → Speakers
               (plays sequentially)
```

**Why a separate thread?**
- Audio capture continues while speaking
- Multiple responses can queue up
- No blocking of main processing

---

### **7. RealTimeAgent Class**
*The orchestrator that connects everything*

#### Main Processing Loop:

```python
async def audio_processing_loop(self):
    while self.is_running:
        # Get audio chunk from microphone
        audio_chunk, is_speech = get_from_queue()
        
        if is_speech:
            # Add to buffer
            self.speech_buffer.append(audio_chunk)
            self.silence_frames = 0
        else:
            if self.speech_buffer:  # Had speech, now silence
                self.silence_frames += 1
                
                # Waited 800ms of silence? Process the speech!
                if self.silence_frames >= 27:  # 27 frames × 30ms = 810ms
                    self.process_speech()
```

**The Intelligence:**
1. Continuously monitors for speech
2. Buffers speech chunks
3. Detects when you stop talking (silence)
4. Processes complete sentences

#### Processing Pipeline:

```python
def process_speech(self):
    # 1. Combine all audio chunks
    audio_data = np.concatenate(self.speech_buffer)
    
    # 2. Speech → Text
    text = self.stt.transcribe(audio_data)
    # Result: "What is the capital of France?"
    
    # 3. Text → AI Response
    response = self.llm.generate_response(text)
    # Result: "The capital of France is Paris."
    
    # 4. Response → Speech
    audio_file = self.tts.synthesize(response)
    # Result: "paris_response.wav"
    
    # 5. Queue for playback
    self.audio_player.play(audio_file)
```

---

## 🌊 How Data Flows (Complete Journey)

### Timeline of a Single Interaction:

```
T=0ms:    You start speaking: "What's the weather?"
T=30ms:   First audio chunk captured
T=60ms:   Second chunk captured (VAD detects speech)
T=90ms:   Third chunk captured and buffered
...
T=2000ms: You finish speaking
T=2030ms: First silence frame detected
T=2060ms: Second silence frame
...
T=2800ms: 27 silence frames → Processing triggered!

T=2801ms: STT starts processing
T=3500ms: STT completes: "What's the weather?"
T=3501ms: LLM request sent to Cerebras
T=3700ms: LLM response received (200ms latency!)
          "I don't have real-time weather data, but I can help..."
T=3701ms: TTS synthesis starts
T=5200ms: TTS completes → audio file created
T=5201ms: Audio queued for playback
T=5202ms: Audio starts playing through speakers
T=7500ms: Response finishes playing

Total latency: ~5.2 seconds from when you stop speaking!
```

---

## 🚀 Setup & Installation Guide

### **Step 1: System Requirements**

**Minimum:**
- Python 3.8+
- 4GB RAM
- Microphone and speakers
- Internet connection (for Cerebras API)

**Recommended:**
- Python 3.10+
- 8GB RAM
- Good quality microphone

---

### **Step 2: Install Python Dependencies**

Open your terminal and run:

```bash
# Core audio processing
pip install sounddevice numpy

# Voice Activity Detection
pip install webrtcvad

# Speech-to-Text (Whisper)
pip install faster-whisper

# Text-to-Speech (Coqui)
pip install TTS

# LLM API (Cerebras)
pip install cerebras_cloud_sdk

# Deep learning framework
pip install torch
```

**Or install all at once:**
```bash
pip install sounddevice numpy webrtcvad faster-whisper TTS cerebras_cloud_sdk torch
```

**Verify installation:**
```bash
python -c "import sounddevice; print('Audio OK')"
python -c "import faster_whisper; print('Whisper OK')"
python -c "import TTS; print('TTS OK')"
python -c "from cerebras.cloud.sdk import Cerebras; print('Cerebras OK')"
```

---

### **Step 3: Get Cerebras API Key**

1. **Go to:** https://cloud.cerebras.ai/
2. **Sign up** with email (free account)
3. **Navigate to:** API Keys section
4. **Create** a new API key
5. **Copy** the key (looks like: `csk-xxxxx-xxxxxx`)

**Important:** Keep this key secret! Don't share or commit to GitHub.

---

### **Step 4: Set Environment Variable**

#### **On Mac/Linux:**
```bash
# Temporary (this session only)
export CEREBRAS_API_KEY="csk-your-key-here"

# Permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export CEREBRAS_API_KEY="csk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### **On Windows (Command Prompt):**
```cmd
# Temporary
set CEREBRAS_API_KEY=csk-your-key-here

# Permanent
setx CEREBRAS_API_KEY "csk-your-key-here"
```

#### **On Windows (PowerShell):**
```powershell
# Temporary
$env:CEREBRAS_API_KEY="csk-your-key-here"

# Permanent
[System.Environment]::SetEnvironmentVariable('CEREBRAS_API_KEY','csk-your-key-here','User')
```

**Verify it's set:**
```bash
# Mac/Linux
echo $CEREBRAS_API_KEY

# Windows (cmd)
echo %CEREBRAS_API_KEY%

# Windows (PowerShell)
echo $env:CEREBRAS_API_KEY
```

---

### **Step 5: Test Your Microphone**

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

**Output should look like:**
```
  0 MacBook Pro Microphone, Core Audio (2 in, 0 out)
> 1 MacBook Pro Speakers, Core Audio (0 in, 2 out)
```

**Set default device (if needed):**
```python
sd.default.device = 0  # Use device ID from list
```

---

## 🎬 Running the Agent

### **Step 1: Save the Code**

Copy the artifact code to a file named `agent.py`

### **Step 2: Run It**

```bash
python agent.py
```

### **Step 3: What You'll See**

```
🚀 Initializing Real-Time Audio Agent...
Loading Whisper model 'base'...
✓ Whisper loaded
Initializing Cerebras LLM 'llama3.1-8b'...
✓ Cerebras connected (ultra-fast inference enabled)
Loading TTS model 'tts_models/en/ljspeech/tacotron2-DDC'...
✓ TTS loaded
✓ Agent ready!

======================================================================
🎙️  REAL-TIME AUDIO AI AGENT
======================================================================

Instructions:
  • Speak naturally into your microphone
  • Wait for the AI to respond
  • Press Ctrl+C to stop

======================================================================

🎤 Microphone started. Speak now...
```

### **Step 4: Interact**

1. **Speak naturally:** "Hello, can you hear me?"
2. **Wait for processing indicator:**
   ```
   🎯 Processing speech...
     → Transcribing...
     👤 You: Hello, can you hear me?
     → Generating response...
     🤖 AI: Yes, I can hear you loud and clear! How can I help you today?
     → Synthesizing speech...
     → Playing response...
   ```
3. **Listen to AI response**
4. **Continue conversation!**

### **Step 5: Stop the Agent**

Press `Ctrl+C` to exit gracefully:
```
^C
🛑 Stopping agent...
✓ Agent stopped
```

---

## 🔧 Troubleshooting

### **Problem: "CEREBRAS_API_KEY not found"**

**Solution:**
```bash
export CEREBRAS_API_KEY="your-key-here"
# Then run again
python agent.py
```

---

### **Problem: "No module named 'sounddevice'"**

**Solution:**
```bash
pip install sounddevice
```

**If still fails (Mac):**
```bash
brew install portaudio
pip install sounddevice
```

---

### **Problem: Microphone not working**

**Test microphone:**
```python
python -c "import sounddevice as sd; print(sd.rec(16000, samplerate=16000, channels=1))"
```

**Check permissions:**
- Mac: System Preferences → Security & Privacy → Microphone
- Windows: Settings → Privacy → Microphone

---

### **Problem: "No speech detected"**

**Reasons:**
1. Speaking too quietly
2. Microphone sensitivity too low
3. VAD too aggressive

**Solutions:**
```python
# In Config class, try:
VAD_AGGRESSIVENESS = 2  # Less aggressive (0-3)
SILENCE_DURATION_MS = 1000  # Wait longer before processing
```

---

### **Problem: TTS model download slow**

**First run downloads ~100MB:**
```
Downloading TTS model... (this may take a few minutes)
```

**Solution:** Be patient, only happens once. Model is cached.

**Check cache location:**
```bash
ls ~/.local/share/tts/
```

---

### **Problem: Response too slow**

**Solutions:**

1. **Use smaller Whisper model:**
```python
WHISPER_MODEL = "tiny"  # Faster, less accurate
```

2. **Reduce TTS quality:**
```python
# Use faster TTS model
TTS_MODEL = "tts_models/en/ljspeech/fast_pitch"
```

3. **Check Cerebras status:**
```bash
curl https://api.cerebras.ai/v1/models
```

---

### **Problem: Audio playback issues**

**Test playback:**
```python
import sounddevice as sd
import numpy as np

# Play test tone
sd.play(np.sin(2*np.pi*440*np.linspace(0,1,16000)), 16000)
sd.wait()
```

**Check output device:**
```python
sd.default.device = [None, 1]  # [input, output] device IDs
```

---

## 🎨 Customization Options

### **Change Voice (TTS Models):**

```python
# Female voices
TTS_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"  # Default
TTS_MODEL = "tts_models/en/ljspeech/glow-tts"       # Alternative

# Male voice
TTS_MODEL = "tts_models/en/vctk/vits"  # Multiple speakers

# List all available:
from TTS.api import TTS
print(TTS.list_models())
```

---

### **Adjust Response Style:**

```python
# In LanguageModel.__init__, modify system prompt:
"content": "You are a funny comedian assistant. Be witty and entertaining!"
# or
"content": "You are a professional business assistant. Be formal and concise."
```

---

### **Multi-language Support:**

```python
# In SpeechToText.transcribe:
language="es"  # Spanish
language="fr"  # French
language="de"  # German
language=None  # Auto-detect
```

---

## 📊 Performance Metrics

**Typical Latency Breakdown:**
```
Voice Activity Detection: ~30ms (real-time)
Speech-to-Text (Whisper base): ~1.5s per 5s audio
LLM (Cerebras): ~200ms
Text-to-Speech: ~1.5s per sentence
─────────────────────────────────────
Total: ~3.2 seconds (from silence to response start)
```

**Compare to alternatives:**
- **Local Ollama:** ~8-12 seconds total
- **OpenAI API:** ~5-7 seconds total
- **This setup:** ~3-4 seconds total ✨

---

## 🎓 Advanced Understanding

### **Why Async/Threading?**

**Without async (blocking):**
```
Record → [WAIT] → Process → [WAIT] → Speak → [WAIT] → Record again
```
**Total time:** 10+ seconds per interaction

**With async (non-blocking):**
```
Record ──────────────────────────────────> (continuous)
         ↓
      Process ──> Speak
                    ↓
                 (can still record!)
```
**Total time:** 3-4 seconds, recording never stops

---

### **Why Queue Pattern?**

**Problem:** Recording happens 33x/second, processing takes seconds

**Solution:** Buffer with queues
```
Fast Producer → [Queue] → Slow Consumer
(microphone)              (processing)
```

**Prevents:**
- Data loss
- Buffer overruns
- Blocking

---

This agent is now fully explained and ready to run! Any questions about specific components or want to add features?