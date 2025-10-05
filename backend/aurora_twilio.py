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

from flask import Flask, request, session, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from cerebras.cloud.sdk import Cerebras
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import uuid

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
    CEREBRAS_MODEL = "llama-3.3-70b"
    
    # Voice settings
    TTS_VOICE = "Polly.Matthew"  # Amazon Polly voice (clear, professional)
    # Alternative voices: Polly.Matthew (male), Polly.Amy, Polly.Brian
    SPEECH_RATE = "slow"  # Speech speed options:
    # - "slow" (slower than normal)
    # - "medium" (normal speed) 
    # - "fast" (faster than normal)
    # - Specific rate: 0.5 (half speed) to 2.0 (double speed)
    # - Examples: 0.8, 1.2, 1.5
    
    # Conversation settings
    SPEECH_TIMEOUT = "auto"  # Auto-detect when user stops speaking
    GATHER_TIMEOUT = 10  # Seconds to wait for speech
    MAX_CONVERSATION_LENGTH = 20  # Maximum exchanges per call

# ============================================================================
# ACTIVE CALLS MANAGER (Frontend Structure)
# ============================================================================
class ActiveCallsManager:
    """Manages active calls and conversations in frontend-compatible structure"""
    
    def __init__(self):
        self.active_calls_dir = "active_calls"
        self.total_file = os.path.join(self.active_calls_dir, "total.json")
        try:
            os.makedirs(self.active_calls_dir, exist_ok=True)
            print(f"📁 Active calls directory created/verified: {os.path.abspath(self.active_calls_dir)}")
        except Exception as e:
            print(f"❌ Error creating active calls directory: {e}")
            # Fallback to current directory
            self.active_calls_dir = "."
            self.total_file = "total.json"
            print(f"📁 Using fallback directory: {os.path.abspath(self.active_calls_dir)}")
    
    def _load_data(self):
        """Load existing data or create new structure"""
        try:
            if os.path.exists(self.total_file):
                with open(self.total_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "active_calls": {},
                    "active_conversations": {}
                }
            return data
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return {"active_calls": {}, "active_conversations": {}}
    
    def _save_data(self, data):
        """Save data to total.json"""
        try:
            print(f"📁 Attempting to save to: {self.total_file}")
            with open(self.total_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📁 Data saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            print(f"❌ Filepath: {self.total_file}")
            return False
    
    def _generate_call_id(self, phone_number):
        """Generate unique call ID based on phone number"""
        clean_phone = phone_number.replace('+', '').replace('-', '').replace(' ', '')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"call_{clean_phone}_{timestamp}"
    
    def _generate_conv_id(self, call_id):
        """Generate conversation ID from call ID"""
        return f"conv_{call_id.split('_', 1)[1]}"
    
    def _generate_msg_id(self, conv_id, message_count):
        """Generate message ID"""
        return f"msg_{conv_id.split('_', 1)[1]}_{message_count:04d}"
    
    def add_conversation_entry(self, phone_number, user_query, aurora_response, urgency_level, sources=None, call_sid=None):
        """Add a new conversation entry following frontend structure"""
        try:
            data = self._load_data()
            
            # Check if this phone number already has an active call
            existing_call_id = None
            for call_id, call_data in data["active_calls"].items():
                if call_data["mobile_no"] == phone_number and call_data["status"] == "ACTIVE":
                    existing_call_id = call_id
                    break
            
            if existing_call_id:
                # Update existing call
                call_id = existing_call_id
                conv_id = data["active_calls"][call_id]["conversation_id"]
            else:
                # Create new call and conversation
                call_id = self._generate_call_id(phone_number)
                conv_id = self._generate_conv_id(call_id)
                
                # Add to active_calls
                data["active_calls"][call_id] = {
                    "worker_id": f"worker_{phone_number.replace('+', '').replace('-', '')}",
                    "mobile_no": phone_number,
                    "conversation_id": conv_id,
                    "urgency": urgency_level.upper(),
                    "status": "ACTIVE",
                    "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                    "medium": "Voice",
                    "last_message_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
                }
                
                # Initialize conversation
                data["active_conversations"][conv_id] = {
                    "call_id": call_id,
                    "messages": {}
                }
            
            # Add messages to conversation
            conv_data = data["active_conversations"][conv_id]
            message_count = len(conv_data["messages"])
            
            # Add user message
            user_msg_id = self._generate_msg_id(conv_id, message_count + 1)
            conv_data["messages"][user_msg_id] = {
                "role": "user",
                "content": user_query,
                "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                "sources": ""
            }
            
            # Add assistant message with sources
            assistant_msg_id = self._generate_msg_id(conv_id, message_count + 2)
            conv_data["messages"][assistant_msg_id] = {
                "role": "assistant",
                "content": aurora_response,
                "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                "sources": sources or ""
            }
            
            # Update call urgency and last message time
            data["active_calls"][call_id]["urgency"] = urgency_level.upper()
            data["active_calls"][call_id]["last_message_at"] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
            
            # Save updated data
            if self._save_data(data):
                print(f"📁 Conversation updated for {phone_number}: {call_id}")
                return call_id, conv_id
            else:
                return None, None
            
        except Exception as e:
            print(f"❌ Error updating conversation: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            return None, None
    
    def get_all_data(self):
        """Get all active calls and conversations data"""
        try:
            return self._load_data()
        except Exception as e:
            print(f"❌ Error getting all data: {e}")
            return {"active_calls": {}, "active_conversations": {}}
    
    def get_call_data(self, call_id):
        """Get specific call data"""
        try:
            data = self._load_data()
            if call_id in data["active_calls"]:
                return {
                    "call": data["active_calls"][call_id],
                    "conversation": data["active_conversations"].get(data["active_calls"][call_id]["conversation_id"], {})
                }
            return None
        except Exception as e:
            print(f"❌ Error getting call data: {e}")
            return None
    
    def end_call(self, call_id):
        """Mark a call as ended"""
        try:
            data = self._load_data()
            if call_id in data["active_calls"]:
                data["active_calls"][call_id]["status"] = "ENDED"
                return self._save_data(data)
            return False
        except Exception as e:
            print(f"❌ Error ending call: {e}")
            return False

# Initialize active calls manager
active_calls_manager = ActiveCallsManager()

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
        
        # Load company data from output.txt
        try:
            with open('output.txt', 'r', encoding='utf-8') as f:
                company_data = f.read()
        except Exception as e:
            print(f"❌ Error loading company data: {e}")
            company_data = "Company data not available"
        
        # System prompt for phone-based industrial assistance
        self.system_prompt = f"""You are Aurora, an AI assistant for industrial workers calling via phone.

COMPANY INFORMATION:
{company_data}

PHONE CONVERSATION GUIDELINES:
1. Be CONCISE - phone conversations require brevity
2. Use SHORT sentences - easier to understand over phone
3. Speak CLEARLY - avoid complex words or jargon
4. ONE instruction at a time - don't overwhelm the caller
5. REPEAT important information - ensure understanding
6. Ask for CONFIRMATION when needed - "Do you understand? Say yes or no."

Your core mission:
- Provide IMMEDIATE, ACTIONABLE guidance for ALL work situations
- Help with routine tasks, procedures, troubleshooting, AND emergency situations
- Give clear step-by-step instructions for any work-related question
- Prioritize worker safety and efficiency in all scenarios
- Reference company policies, procedures, and safety protocols
- Assist with daily operations, equipment questions, and general work guidance

Response structure:
For EMERGENCIES (fires, injuries, equipment failures, safety hazards):
1. IMMEDIATE ACTION (1 sentence): "Evacuate now."
2. SAFETY STEP (1 sentence): "Follow emergency exit routes."
3. ALERT (1 sentence): "Contact emergency response team immediately."
4. CONFIRMATION: "Did you understand? Say yes or no."

For REGULAR ASSISTANCE (procedures, troubleshooting, guidance):
1. UNDERSTAND the situation: Ask clarifying questions if needed
2. PROVIDE clear steps: Break down complex tasks
3. OFFER alternatives: Suggest backup options when possible
4. CONFIRM understanding: "Does this help? Any questions?"

Emergency procedures (from company data):
- Fire Drill: Follow emergency exit routes, gather at designated assembly point
- Medical Emergency: Contact on-site medical staff immediately, first aid kits available
- Evacuation: Follow instructions of emergency response team
- Hazard Reporting: Report hazards to safety officer immediately
- Safety Training: Regular sessions cover fire safety, first aid, emergency response

Safety protocols (from company data):
- Personal Protective Equipment (PPE): Wear appropriate PPE at all times
- Hazard Reporting: Report spills, equipment malfunctions, potential dangers
- Safety Training: Regular sessions ensure awareness of safety protocols

Regular assistance areas (Aurora helps with ALL of these):
- Equipment operation procedures and how-to questions
- Troubleshooting common issues and problems
- Safety protocol questions and clarifications
- Process optimization suggestions and improvements
- Training and guidance requests
- Company policies and procedures explanations
- Quality control measures and standards
- Standard operating procedures and workflows
- Daily operations and routine tasks
- Equipment maintenance and care
- Work scheduling and time management
- General work-related questions and support
- Procedure clarifications and step-by-step guidance
- Policy questions and compliance help

PHONE-SPECIFIC RULES:
- Maximum 3-4 sentences per response
- Use simple words only
- Pause between instructions (use periods)
- Always end critical instructions with confirmation request
- For emergencies, prioritize safety above all else
- For regular assistance, be helpful and thorough
- Reference company policies when relevant
- Aurora is available for ANY work-related question or situation
- No question is too simple or too complex - Aurora helps with everything

Remember: This is a PHONE CALL. Keep it SHORT and CLEAR. Aurora assists with ALL work situations - emergencies AND regular assistance."""
    
    def generate_response(self, conversation_history, user_input):
        """Generate Aurora's response with sources extraction"""
        
        try:
            # Enhanced system prompt to include urgency classification and sources
            enhanced_system_prompt = self.system_prompt + """

IMPORTANT: After providing your response, you MUST also classify the urgency level and provide sources.
Add this exact format at the end of your response:
[URGENCY: critical/urgent/normal/assistive]
[SOURCES: source1, source2, source3]

Urgency levels:
- "critical": life-threatening, immediate danger (gas leaks, fires, explosions, severe injuries)
- "urgent": serious but not immediately life-threatening (injuries, equipment failures, safety hazards)
- "normal": routine work situation (status updates, general questions)
- "assistive": asking for help, guidance, or procedures (how-to questions, troubleshooting)

Sources should be relevant references like:
- "OSHA Safety Standards", "Emergency Procedures Manual", "Zone A Layout", "Valve 3 Documentation", "Fire Safety Protocol", "Chemical Handling Guide", "Equipment Manual", "Safety Training Materials"

Example response:
"Evacuate immediately. Shut Valve 3 if safe. Call fire brigade now. [URGENCY: critical] [SOURCES: Emergency Procedures Manual, Zone A Layout, Fire Safety Protocol]"
"""
            
            # Build messages with enhanced system prompt
            enhanced_messages = [{"role": "system", "content": enhanced_system_prompt}]
            enhanced_messages.extend(conversation_history)
            enhanced_messages.append({"role": "user", "content": user_input})
            
            # Call Cerebras API
            response = self.client.chat.completions.create(
                model=self.config.CEREBRAS_MODEL,
                messages=enhanced_messages,
                max_tokens=250,  # Increased to accommodate urgency and sources
                temperature=0.2,  # Very low for consistent safety instructions
            )
            
            full_response = response.choices[0].message.content
            
            # Extract urgency level and sources from response
            urgency_level = "normal"  # Default
            sources = []  # Default empty sources
            
            # Extract urgency
            if "[URGENCY:" in full_response:
                try:
                    urgency_start = full_response.find("[URGENCY:") + 9
                    urgency_end = full_response.find("]", urgency_start)
                    urgency_level = full_response[urgency_start:urgency_end].strip().lower()
                    
                    # Validate urgency level
                    valid_levels = ["critical", "urgent", "normal", "assistive"]
                    if urgency_level not in valid_levels:
                        urgency_level = "normal"
                except Exception as e:
                    print(f"❌ Urgency parsing error: {e}")
                    urgency_level = "normal"
            
            # Extract sources
            if "[SOURCES:" in full_response:
                try:
                    sources_start = full_response.find("[SOURCES:") + 9
                    sources_end = full_response.find("]", sources_start)
                    sources = full_response[sources_start:sources_end].strip()
                except Exception as e:
                    print(f"❌ Sources parsing error: {e}")
                    sources = ""
            
            # Remove both classifications from response
            assistant_message = full_response
            if "[URGENCY:" in assistant_message:
                assistant_message = assistant_message[:assistant_message.find("[URGENCY:")].strip()
            if "[SOURCES:" in assistant_message:
                assistant_message = assistant_message[:assistant_message.find("[SOURCES:")].strip()
            
            return assistant_message, urgency_level, sources
            
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return "Emergency system error. Please call your supervisor at extension 9999 immediately.", "critical", "Emergency Procedures Manual"

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
        <li>POST /incoming-call - Handle incoming calls (returns TwiML)</li>
        <li>POST /process-speech - Process worker speech (returns TwiML)</li>
        <li>POST /call-status - Call status updates</li>
        <li>POST /api/process-speech - Process speech (returns JSON)</li>
        <li>GET /api/active-calls - Get all active calls and conversations</li>
        <li>GET /api/call/&lt;call_id&gt; - Get specific call data</li>
        <li>POST /api/call/&lt;call_id&gt;/end - End a specific call</li>
    </ul>
    <p>Powered by Cerebras AI + Twilio</p>
    <p><strong>JSON API Response Format:</strong></p>
    <ul>
        <li><code>message</code> - Aurora's response text</li>
        <li><code>ph_no</code> - Caller's phone number</li>
        <li><code>urgency</code> - Urgency level (critical, urgent, normal, assistive)</li>
    </ul>
    <p><strong>Active Calls Structure:</strong> Data saved in <code>active_calls/total.json</code> with frontend-compatible structure</p>
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
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Greeting
    greeting = (
        "Aurora industrial assistant. "
        "How can I help you today? "
        "Describe your situation or question. "
        "You may speak now."
    )
    
    response.say(greeting, voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
    
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
    response.say("I didn't hear anything. Please describe your situation or question.", 
                 voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
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
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        conversation_manager.end_conversation(call_sid)
        return str(response)
    
    # Handle empty or unclear speech
    if not speech_result or len(speech_result.strip()) < 3:
        response = VoiceResponse()
        response.say(
            "I couldn't understand that. Please speak clearly and describe your situation or question.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.redirect('/incoming-call')
        return str(response)
    
    try:
        # Add to conversation history
        conversation_manager.add_message(call_sid, "user", speech_result)
        
        # Generate Aurora's response
        conversation_history = conversation_manager.get_history(call_sid)
        aurora_response, urgency_level, sources = aurora_llm.generate_response(conversation_history, speech_result)
        
        # Add Aurora's response to history
        conversation_manager.add_message(call_sid, "assistant", aurora_response)
        
        # Log critical situations
        if urgency_level in ["critical", "urgent"]:
            conversation_manager.add_critical_alert(call_sid, {
                "worker_message": speech_result,
                "aurora_response": aurora_response,
                "urgency_level": urgency_level,
                "sources": sources
            })
            print(f"   ⚠️ {urgency_level.upper()} SITUATION DETECTED")
        
        print(f"   🤖 Aurora: {aurora_response}")
        print(f"   📊 Urgency Level: {urgency_level}")
        print(f"   📚 Sources: {sources}")
        
        # Save to active calls structure
        phone_number = request.form.get('From', 'Unknown')
        call_id, conv_id = active_calls_manager.add_conversation_entry(
            phone_number=phone_number,
            user_query=speech_result,
            aurora_response=aurora_response,
            urgency_level=urgency_level,
            sources=sources,
            call_sid=call_sid
        )
        
        # Create TwiML response
        response = VoiceResponse()
        response.say(aurora_response, voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
        
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
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        
        return str(response)
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        # Return TwiML error response
        response = VoiceResponse()
        response.say(
            "I'm experiencing technical difficulties. Please call back in a moment or contact your supervisor.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        return str(response)

@app.route("/api/process-speech", methods=['POST'])
def api_process_speech():
    """API endpoint for processing speech and returning JSON response"""
    try:
        # Get data from request (can be form data or JSON)
        if request.is_json:
            data = request.get_json()
            speech_result = data.get('speech', '')
            phone_number = data.get('ph_no', 'Unknown')
        else:
            speech_result = request.form.get('SpeechResult', '')
            phone_number = request.form.get('From', 'Unknown')
        
        if not speech_result or len(speech_result.strip()) < 3:
            return jsonify({
                "message": "I couldn't understand that. Please provide clear speech input.",
                "ph_no": phone_number,
                "urgency": "normal"
            })
        
        # Generate Aurora's response
        aurora_response, urgency_level, sources = aurora_llm.generate_response([], speech_result)
        
        print(f"   🤖 Aurora: {aurora_response}")
        print(f"   📊 Urgency Level: {urgency_level}")
        print(f"   📚 Sources: {sources}")
        
        # Save to active calls structure
        call_id, conv_id = active_calls_manager.add_conversation_entry(
            phone_number=phone_number,
            user_query=speech_result,
            aurora_response=aurora_response,
            urgency_level=urgency_level,
            sources=sources
        )
        
        # Prepare JSON response
        json_response = {
            "message": aurora_response,
            "ph_no": phone_number,
            "urgency": urgency_level
        }
        
        return jsonify(json_response)
        
    except Exception as e:
        print(f"❌ API Processing error: {e}")
        return jsonify({
            "message": "I'm experiencing technical difficulties. Please try again later.",
            "ph_no": request.form.get('From', 'Unknown'),
            "urgency": "normal"
        })

@app.route("/api/active-calls", methods=['GET'])
def get_active_calls():
    """Get all active calls and conversations data"""
    try:
        data = active_calls_manager.get_all_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Error retrieving active calls: {e}"}), 500

@app.route("/api/call/<call_id>", methods=['GET'])
def get_call_data(call_id):
    """Get specific call data"""
    try:
        call_data = active_calls_manager.get_call_data(call_id)
        if call_data:
            return jsonify(call_data)
        else:
            return jsonify({"error": "Call not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error retrieving call data: {e}"}), 500

@app.route("/api/call/<call_id>/end", methods=['POST'])
def end_call(call_id):
    """End a specific call"""
    try:
        success = active_calls_manager.end_call(call_id)
        if success:
            return jsonify({"message": "Call ended successfully"})
        else:
            return jsonify({"error": "Failed to end call"}), 500
    except Exception as e:
        return jsonify({"error": f"Error ending call: {e}"}), 500

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
    response.say("Goodbye. Stay safe.", voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
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