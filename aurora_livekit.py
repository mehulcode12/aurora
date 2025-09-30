"""
Aurora Emergency Assistant - Phone Call Integration
Integrates Aurora with Twilio for real phone calls

Requirements:
pip install twilio flask cerebras_cloud_sdk python-dotenv

Setup Instructions:
1. Sign up for Twilio: https://www.twilio.com/try-twilio
2. Get a free phone number with voice capabilities
3. Create .env file with:
   CEREBRAS_API_KEY=your_cerebras_key
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_number

4. Run this server: python aurora_phone.py
5. In another terminal, expose with ngrok: ngrok http 5000
6. Copy ngrok URL to Twilio console → Phone Number → Voice Webhook
7. Call your Twilio number!
"""

from flask import Flask, request, session
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from cerebras.cloud.sdk import Cerebras
import os
from datetime import datetime
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    # Twilio settings
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    
    # Cerebras settings
    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
    CEREBRAS_MODEL = "llama3.1-8b"
    
    # Voice settings
    TTS_VOICE = "Polly.Joanna"  # Amazon Polly voice (clear, professional)
    # Alternative voices: Polly.Matthew (male), Polly.Amy, Polly.Brian
    
    # Conversation settings
    SPEECH_TIMEOUT = "auto"  # Auto-detect when user stops speaking
    GATHER_TIMEOUT = 5  # Seconds to wait for speech
    MAX_CONVERSATION_LENGTH = 20  # Maximum exchanges per call

# ============================================================================
# CONVERSATION MANAGER
# ============================================================================
class ConversationManager:
    """Manages conversation state for each phone call"""
    
    def __init__(self):
        self.conversations = {}  # call_sid -> conversation_history
    
    def get_conversation(self, call_sid):
        """Get or create conversation history for a call"""
        if call_sid not in self.conversations:
            self.conversations[call_sid] = {
                "history": [],
                "start_time": datetime.now(),
                "exchange_count": 0,
                "critical_alerts": []
            }
        return self.conversations[call_sid]
    
    def add_message(self, call_sid, role, content):
        """Add message to conversation history"""
        conv = self.get_conversation(call_sid)
        conv["history"].append({"role": role, "content": content})
        if role == "user":
            conv["exchange_count"] += 1
    
    def get_history(self, call_sid):
        """Get conversation history"""
        conv = self.get_conversation(call_sid)
        return conv["history"]
    
    def add_critical_alert(self, call_sid, alert):
        """Log critical situation"""
        conv = self.get_conversation(call_sid)
        conv["critical_alerts"].append({
            "timestamp": datetime.now(),
            "alert": alert
        })
    
    def end_conversation(self, call_sid):
        """End conversation and generate summary"""
        if call_sid in self.conversations:
            conv = self.conversations[call_sid]
            duration = (datetime.now() - conv["start_time"]).seconds
            
            summary = {
                "call_sid": call_sid,
                "duration_seconds": duration,
                "exchanges": conv["exchange_count"],
                "critical_alerts": len(conv["critical_alerts"]),
                "conversation": conv["history"]
            }
            
            # Save to log file
            self._save_log(summary)
            
            # Clean up
            del self.conversations[call_sid]
            
            return summary
    
    def _save_log(self, summary):
        """Save conversation log to file"""
        log_dir = "call_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        filename = f"{log_dir}/call_{summary['call_sid']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"📝 Call log saved: {filename}")

# ============================================================================
# AURORA LLM INTEGRATION
# ============================================================================
class AuroraLLM:
    """Aurora Emergency Assistant LLM"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize Cerebras client
        if not config.CEREBRAS_API_KEY:
            raise ValueError("CEREBRAS_API_KEY not found in environment")
        
        self.client = Cerebras(api_key=config.CEREBRAS_API_KEY)
        print("✓ Aurora LLM initialized")
        
        # System prompt for phone-based emergency assistance
        self.system_prompt = """You are Aurora, an AI emergency assistant for industrial workers calling via phone.

CRITICAL PHONE CONVERSATION GUIDELINES:
1. Be EXTREMELY CONCISE - phone conversations require brevity
2. Use SHORT sentences - easier to understand over phone
3. Speak CLEARLY - avoid complex words or jargon
4. ONE instruction at a time - don't overwhelm the caller
5. REPEAT critical information - ensure understanding
6. Ask for CONFIRMATION - "Do you understand? Say yes or no."

Your core mission:
- Provide IMMEDIATE, ACTIONABLE safety guidance
- Identify hazards: gas leaks, fires, injuries, equipment failures
- Give clear step-by-step emergency instructions
- Prioritize worker safety above all else

Response structure for emergencies:
1. IMMEDIATE ACTION (1 sentence): "Evacuate now."
2. SAFETY STEP (1 sentence): "Shut Valve 3 if safe."
3. ALERT (1 sentence): "Call fire brigade immediately."
4. CONFIRMATION: "Did you understand? Say yes or no."

Zone layout:
- Zone A: Manufacturing floor, press machines
- Zone B: Gas line corridor, Valves 1-5
- Zone C: Chemical storage, flammable materials
- Zone D: Assembly line, low-risk area
- Zone E: Maintenance workshop
- Zone F: Loading dock

Emergency protocols:
- Gas leak → Evacuate, shut valves, eliminate ignition, call gas team + fire brigade
- Fire → Evacuate, activate alarms, use extinguisher if safe, call fire brigade
- Chemical spill → Evacuate, contain if safe, call hazmat team
- Injury → First aid, call ambulance, don't move victim unless danger
- Equipment failure → Shut down, isolate area, call maintenance

PHONE-SPECIFIC RULES:
- Maximum 3 sentences per response
- Use simple words only
- Pause between instructions (use periods)
- Always end critical instructions with confirmation request
- If caller seems confused, repeat in simpler terms

Remember: This is a PHONE CALL. Keep it SHORT and CLEAR."""
    
    def generate_response(self, conversation_history, user_input):
        """Generate Aurora's response"""
        
        # Build messages with system prompt
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        
        # Detect urgency
        urgent_keywords = ['gas', 'leak', 'fire', 'injured', 'emergency', 
                          'help', 'danger', 'smoke', 'bleeding', 'explosion']
        is_urgent = any(keyword in user_input.lower() for keyword in urgent_keywords)
        
        try:
            # Call Cerebras API
            response = self.client.chat.completions.create(
                model=self.config.CEREBRAS_MODEL,
                messages=messages,
                max_tokens=150,  # Keep responses very short for phone
                temperature=0.2,  # Very low for consistent safety instructions
            )
            
            assistant_message = response.choices[0].message.content
            
            return assistant_message, is_urgent
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return "Emergency system error. Please call your supervisor at extension 9999 immediately.", True

# ============================================================================
# FLASK APP
# ============================================================================
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Initialize components
config = Config()
aurora_llm = AuroraLLM(config)
conversation_manager = ConversationManager()

# ============================================================================
# TWILIO WEBHOOKS
# ============================================================================

@app.route("/", methods=['GET', 'POST'])
def home():
    """Health check endpoint and Twilio webhook handler"""
    if request.method == 'POST':
        # Check if this is a Twilio webhook (has CallSid)
        call_sid = request.form.get('CallSid')
        if call_sid:
            print(f"\n📞 TWILIO WEBHOOK DETECTED - Redirecting to /incoming-call")
            print(f"   Call SID: {call_sid}")
            print(f"   From: {request.form.get('From')}")
            print(f"   To: {request.form.get('To')}")
            print(f"   Call Status: {request.form.get('CallStatus')}")
            
            # Redirect to the proper incoming call handler
            return incoming_call()
        else:
            # Log other POST requests for debugging
            print(f"\n📨 POST request to root path:")
            print(f"   Headers: {dict(request.headers)}")
            print(f"   Form data: {dict(request.form)}")
            print(f"   JSON data: {request.get_json()}")
            
            # Return a simple response for non-Twilio POST requests
            return "Aurora Emergency Assistant - Phone System Online", 200
    
    # GET request - show the status page
    return """
    <h1>🚨 Aurora Emergency Assistant - Phone System</h1>
    <p>Status: <strong>Online</strong></p>
    <p>Endpoints:</p>
    <ul>
        <li>POST /incoming-call - Handle incoming calls</li>
        <li>POST /process-speech - Process worker speech</li>
        <li>POST /call-status - Call status updates</li>
    </ul>
    <p>Powered by Cerebras AI + Twilio</p>
    <p><strong>Note:</strong> Twilio webhooks sent to root path will be automatically redirected to /incoming-call</p>
    """

@app.route("/incoming-call", methods=['POST'])
def incoming_call():
    """Handle incoming phone call"""
    call_sid = request.form.get('CallSid')
    from_number = request.form.get('From')
    
    print(f"\n📞 INCOMING CALL")
    print(f"   Call SID: {call_sid}")
    print(f"   From: {from_number}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize conversation
    conversation_manager.get_conversation(call_sid)
    
    # Create response
    response = VoiceResponse()
    
    # Greeting
    greeting = (
        "Aurora emergency assistant. "
        "Describe your situation clearly. "
        "Speak now."
    )
    
    response.say(greeting, voice=config.TTS_VOICE)
    
    # Gather speech input
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=config.GATHER_TIMEOUT,
        speech_timeout=config.SPEECH_TIMEOUT,
        language='en-US'
    )
    
    response.append(gather)
    
    # If no input, prompt again
    response.say("I didn't hear anything. Please describe your situation.", 
                 voice=config.TTS_VOICE)
    response.redirect('/incoming-call')
    
    return str(response)

@app.route("/process-speech", methods=['POST'])
def process_speech():
    """Process worker's speech and generate Aurora's response"""
    call_sid = request.form.get('CallSid')
    speech_result = request.form.get('SpeechResult', '')
    confidence = request.form.get('Confidence', '0.0')
    
    print(f"\n🎤 SPEECH RECEIVED")
    print(f"   Call: {call_sid}")
    print(f"   Worker: {speech_result}")
    print(f"   Confidence: {confidence}")
    
    # Check if conversation exists
    conv = conversation_manager.get_conversation(call_sid)
    
    # Check conversation length limit
    if conv["exchange_count"] >= config.MAX_CONVERSATION_LENGTH:
        response = VoiceResponse()
        response.say(
            "Maximum conversation length reached. "
            "Please call back if you need further assistance. "
            "Goodbye.",
            voice=config.TTS_VOICE
        )
        response.hangup()
        conversation_manager.end_conversation(call_sid)
        return str(response)
    
    # Handle empty or unclear speech
    if not speech_result or len(speech_result.strip()) < 3:
        response = VoiceResponse()
        response.say(
            "I couldn't understand that. Please speak clearly and describe your situation.",
            voice=config.TTS_VOICE
        )
        response.redirect('/incoming-call')
        return str(response)
    
    # Add to conversation history
    conversation_manager.add_message(call_sid, "user", speech_result)
    
    # Generate Aurora's response
    conversation_history = conversation_manager.get_history(call_sid)
    aurora_response, is_urgent = aurora_llm.generate_response(conversation_history, speech_result)
    
    # Add Aurora's response to history
    conversation_manager.add_message(call_sid, "assistant", aurora_response)
    
    # Log critical situations
    if is_urgent:
        conversation_manager.add_critical_alert(call_sid, {
            "worker_message": speech_result,
            "aurora_response": aurora_response
        })
        print(f"   ⚠️ CRITICAL SITUATION DETECTED")
    
    print(f"   🤖 Aurora: {aurora_response}")
    
    # Create response
    response = VoiceResponse()
    response.say(aurora_response, voice=config.TTS_VOICE)
    
    # Continue conversation
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=config.GATHER_TIMEOUT,
        speech_timeout=config.SPEECH_TIMEOUT,
        language='en-US'
    )
    
    response.append(gather)
    
    # If no further input, end call
    response.say(
        "If you need more help, please call back. Stay safe. Goodbye.",
        voice=config.TTS_VOICE
    )
    response.hangup()
    
    return str(response)

@app.route("/call-status", methods=['POST'])
def call_status():
    """Handle call status updates (completed, failed, etc.)"""
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    
    print(f"\n📊 CALL STATUS UPDATE")
    print(f"   Call: {call_sid}")
    print(f"   Status: {call_status}")
    
    # If call ended, save conversation log
    if call_status in ['completed', 'failed', 'busy', 'no-answer']:
        summary = conversation_manager.end_conversation(call_sid)
        if summary:
            print(f"   Duration: {summary['duration_seconds']}s")
            print(f"   Exchanges: {summary['exchanges']}")
            print(f"   Critical Alerts: {summary['critical_alerts']}")
    
    return '', 200

@app.route("/hangup", methods=['POST'])
def hangup():
    """Handle explicit hangup"""
    call_sid = request.form.get('CallSid')
    conversation_manager.end_conversation(call_sid)
    
    response = VoiceResponse()
    response.say("Goodbye. Stay safe.", voice=config.TTS_VOICE)
    response.hangup()
    
    return str(response)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_config():
    """Validate required configuration"""
    missing = []
    
    if not config.CEREBRAS_API_KEY:
        missing.append("CEREBRAS_API_KEY")
    if not config.TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not config.TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not config.TWILIO_PHONE_NUMBER:
        missing.append("TWILIO_PHONE_NUMBER")
    
    if missing:
        print("\n❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nCreate a .env file with:")
        print("CEREBRAS_API_KEY=your_key")
        print("TWILIO_ACCOUNT_SID=your_sid")
        print("TWILIO_AUTH_TOKEN=your_token")
        print("TWILIO_PHONE_NUMBER=your_number")
        return False
    
    return True

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚨 AURORA EMERGENCY ASSISTANT - PHONE SYSTEM")
    print("="*70)
    
    # Validate configuration
    if not validate_config():
        print("\n❌ Configuration validation failed!")
        print("\nSetup instructions:")
        print("1. Sign up: https://www.twilio.com/try-twilio")
        print("2. Get Cerebras key: https://cloud.cerebras.ai/")
        print("3. Create .env file with credentials")
        exit(1)
    
    print("\n✓ Configuration validated")
    print(f"✓ Twilio Account: {config.TWILIO_ACCOUNT_SID[:10]}...")
    print(f"✓ Phone Number: {config.TWILIO_PHONE_NUMBER}")
    print(f"✓ Cerebras API: Connected")
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Run this server: python aurora_phone.py")
    print("2. In another terminal: ngrok http 5000")
    print("3. Copy ngrok HTTPS URL")
    print("4. Twilio Console → Phone Number → Voice Webhook:")
    print("   - Webhook URL: https://your-ngrok-url.ngrok.io/incoming-call")
    print("   - HTTP POST")
    print("5. Status Callback URL: https://your-ngrok-url.ngrok.io/call-status")
    print("6. Save and call your Twilio number!")
    print("="*70 + "\n")
    
    # Create logs directory
    os.makedirs("call_logs", exist_ok=True)
    
    # Run Flask app
    print("🚀 Starting Aurora Phone System...")
    print(f"📞 Server running on http://localhost:5000")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)