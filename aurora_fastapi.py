"""
Aurora Emergency Assistant - Phone Call Integration (FastAPI Version)
Integrates Aurora with Twilio for real phone calls using FastAPI

Requirements:
pip install fastapi uvicorn twilio cerebras_cloud_sdk python-dotenv python-multipart

Setup Instructions:
1. Sign up for Twilio: https://www.twilio.com/try-twilio
2. Get a free phone number with voice capabilities
3. Create .env file with:
   CEREBRAS_API_KEY=your_cerebras_key
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_number

4. Run this server: uvicorn aurora_phone_fastapi:app --reload --host 0.0.0.0 --port 5000
5. In another terminal, expose with ngrok: ngrok http 5000
6. Copy ngrok URL to Twilio console → Phone Number → Voice Webhook
7. Call your Twilio number!
"""

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import Response, JSONResponse, HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from cerebras.cloud.sdk import Cerebras
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import uuid
from typing import Optional, Dict, Any

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
    TTS_VOICE = "Polly.Matthew"
    SPEECH_RATE = "slow"
    
    # Conversation settings
    SPEECH_TIMEOUT = "auto"
    GATHER_TIMEOUT = 10
    MAX_CONVERSATION_LENGTH = 20

# ============================================================================
# ACTIVE CALLS MANAGER
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
            
            existing_call_id = None
            for call_id, call_data in data["active_calls"].items():
                if call_data["mobile_no"] == phone_number and call_data["status"] == "ACTIVE":
                    existing_call_id = call_id
                    break
            
            if existing_call_id:
                call_id = existing_call_id
                conv_id = data["active_calls"][call_id]["conversation_id"]
            else:
                call_id = self._generate_call_id(phone_number)
                conv_id = self._generate_conv_id(call_id)
                
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
                
                data["active_conversations"][conv_id] = {
                    "call_id": call_id,
                    "messages": {}
                }
            
            conv_data = data["active_conversations"][conv_id]
            message_count = len(conv_data["messages"])
            
            user_msg_id = self._generate_msg_id(conv_id, message_count + 1)
            conv_data["messages"][user_msg_id] = {
                "role": "user",
                "content": user_query,
                "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                "sources": ""
            }
            
            assistant_msg_id = self._generate_msg_id(conv_id, message_count + 2)
            conv_data["messages"][assistant_msg_id] = {
                "role": "assistant",
                "content": aurora_response,
                "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                "sources": sources or ""
            }
            
            data["active_calls"][call_id]["urgency"] = urgency_level.upper()
            data["active_calls"][call_id]["last_message_at"] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
            
            if self._save_data(data):
                print(f"📁 Conversation updated for {phone_number}: {call_id}")
                return call_id, conv_id
            else:
                return None, None
            
        except Exception as e:
            print(f"❌ Error updating conversation: {e}")
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

# ============================================================================
# CONVERSATION MANAGER
# ============================================================================
class ConversationManager:
    """Manages conversation state for each phone call"""
    
    def __init__(self):
        self.conversations = {}
    
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
            
            self._save_log(summary)
            del self.conversations[call_sid]
            
            return summary
        return None
    
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
            
            enhanced_messages = [{"role": "system", "content": enhanced_system_prompt}]
            enhanced_messages.extend(conversation_history)
            enhanced_messages.append({"role": "user", "content": user_input})
            
            response = self.client.chat.completions.create(
                model=self.config.CEREBRAS_MODEL,
                messages=enhanced_messages,
                max_tokens=250,
                temperature=0.2,
            )
            
            full_response = response.choices[0].message.content
            
            urgency_level = "normal"
            sources = []
            
            if "[URGENCY:" in full_response:
                try:
                    urgency_start = full_response.find("[URGENCY:") + 9
                    urgency_end = full_response.find("]", urgency_start)
                    urgency_level = full_response[urgency_start:urgency_end].strip().lower()
                    
                    valid_levels = ["critical", "urgent", "normal", "assistive"]
                    if urgency_level not in valid_levels:
                        urgency_level = "normal"
                except Exception as e:
                    print(f"❌ Urgency parsing error: {e}")
                    urgency_level = "normal"
            
            if "[SOURCES:" in full_response:
                try:
                    sources_start = full_response.find("[SOURCES:") + 9
                    sources_end = full_response.find("]", sources_start)
                    sources = full_response[sources_start:sources_end].strip()
                except Exception as e:
                    print(f"❌ Sources parsing error: {e}")
                    sources = ""
            
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
# FASTAPI APP
# ============================================================================
app = FastAPI(
    title="Aurora Emergency Assistant - Phone System",
    description="AI-powered emergency assistance for industrial workers via phone calls",
    version="2.0.0"
)

# Initialize components
config = Config()
aurora_llm = AuroraLLM(config)
conversation_manager = ConversationManager()
active_calls_manager = ActiveCallsManager()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/status")
async def status():
    """Health check and status endpoint"""
    return {
        "status": "online",
        "message": "Aurora Emergency Assistant is running",
        "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
        "version": "2.0.0",
        "services": {
            "aurora_llm": "active" if config.CEREBRAS_API_KEY else "inactive",
            "twilio": "active" if config.TWILIO_ACCOUNT_SID else "inactive",
            "web_call": "active"
        }
    }

@app.get("/hello")
async def hello():
    """Simple hello endpoint"""
    return {"message": "Hello! Aurora Emergency Assistant is ready to help."}

@app.get("/", response_class=HTMLResponse)
async def home():
    """Health check endpoint and status page"""
    return """
    <h1>🚨 Aurora Emergency Assistant - Phone System (FastAPI)</h1>
    <p>Status: <strong>Online</strong></p>
    <p>Endpoints:</p>
    <ul>
        <li>GET /status - Health check and system status</li>
        <li>GET /hello - Simple hello message</li>
        <li>POST /incoming-call - Handle incoming calls (returns TwiML)</li>
        <li>POST /process-speech - Process worker speech (returns TwiML)</li>
        <li>POST /call-status - Call status updates</li>
        <li>POST /api/process-speech - Process speech (returns JSON)</li>
        <li>GET /api/active-calls - Get all active calls and conversations</li>
        <li>GET /api/call/{call_id} - Get specific call data</li>
        <li>POST /api/call/{call_id}/end - End a specific call</li>
        <li>GET /docs - Interactive API documentation (Swagger UI)</li>
        <li>GET /redoc - Alternative API documentation (ReDoc)</li>
        <li>GET /web-call - Web-based phone simulation</li>
    </ul>
    <p>Powered by Cerebras AI + Twilio + FastAPI</p>
    <p><strong>JSON API Response Format:</strong></p>
    <ul>
        <li><code>message</code> - Aurora's response text</li>
        <li><code>ph_no</code> - Caller's phone number</li>
        <li><code>urgency</code> - Urgency level (critical, urgent, normal, assistive)</li>
    </ul>
    <p><strong>Active Calls Structure:</strong> Data saved in <code>active_calls/total.json</code></p>
    <p><strong>🌐 Web Call Interface:</strong> <a href="/web-call" style="color: #007bff;">Try Aurora without a phone!</a></p>
    """

@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root path (Twilio webhook redirection)"""
    try:
        # Get form data
        form_data = await request.form()
        
        # Check if this is a Twilio webhook by looking for CallSid
        if 'CallSid' in form_data:
            print(f"🔄 Twilio webhook detected, redirecting to /incoming-call")
            # Redirect to the proper incoming call handler
            return await incoming_call(
                CallSid=form_data['CallSid'],
                From=form_data.get('From', 'Unknown')
            )
        else:
            # Not a Twilio webhook, return error
            return JSONResponse(
                {"error": "Invalid request. Expected Twilio webhook."}, 
                status_code=400
            )
            
    except Exception as e:
        print(f"❌ Error in root POST handler: {e}")
        return JSONResponse(
            {"error": "Internal server error"}, 
            status_code=500
        )

@app.post("/incoming-call")
async def incoming_call(
    CallSid: str = Form(...),
    From: str = Form(...)
):
    """Handle incoming phone call"""
    print(f"\n📞 INCOMING CALL")
    print(f"   Call SID: {CallSid}")
    print(f"   From: {From}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conversation_manager.get_conversation(CallSid)
    
    response = VoiceResponse()
    
    greeting = (
        "Aurora industrial assistant. "
        "How can I help you today? "
        "Describe your situation or question. "
        "You may speak now."
    )
    
    response.say(greeting, voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
    
    gather = Gather(
        input='speech',
        action='/process-speech',
        timeout=config.GATHER_TIMEOUT,
        speech_timeout=config.SPEECH_TIMEOUT,
        language='en-US'
    )
    
    response.append(gather)
    
    response.say("I didn't hear anything. Please describe your situation or question.", 
                 voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
    response.redirect('/incoming-call')
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/process-speech")
async def process_speech(
    CallSid: str = Form(...),
    SpeechResult: str = Form(""),
    Confidence: str = Form("0.0"),
    From: str = Form("Unknown")
):
    """Process worker's speech and generate Aurora's response"""
    print(f"\n🎤 SPEECH RECEIVED")
    print(f"   Call: {CallSid}")
    print(f"   Worker: {SpeechResult}")
    print(f"   Confidence: {Confidence}")
    
    conv = conversation_manager.get_conversation(CallSid)
    
    if conv["exchange_count"] >= config.MAX_CONVERSATION_LENGTH:
        response = VoiceResponse()
        response.say(
            "Maximum conversation length reached. "
            "Please call back if you need further assistance. "
            "Goodbye.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        conversation_manager.end_conversation(CallSid)
        return Response(content=str(response), media_type="application/xml")
    
    if not SpeechResult or len(SpeechResult.strip()) < 3:
        response = VoiceResponse()
        response.say(
            "I couldn't understand that. Please speak clearly and describe your situation or question.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.redirect('/incoming-call')
        return Response(content=str(response), media_type="application/xml")
    
    try:
        conversation_manager.add_message(CallSid, "user", SpeechResult)
        
        conversation_history = conversation_manager.get_history(CallSid)
        aurora_response, urgency_level, sources = aurora_llm.generate_response(conversation_history, SpeechResult)
        
        conversation_manager.add_message(CallSid, "assistant", aurora_response)
        
        if urgency_level in ["critical", "urgent"]:
            conversation_manager.add_critical_alert(CallSid, {
                "worker_message": SpeechResult,
                "aurora_response": aurora_response,
                "urgency_level": urgency_level,
                "sources": sources
            })
            print(f"   ⚠️ {urgency_level.upper()} SITUATION DETECTED")
        
        print(f"   🤖 Aurora: {aurora_response}")
        print(f"   📊 Urgency Level: {urgency_level}")
        print(f"   📚 Sources: {sources}")
        
        call_id, conv_id = active_calls_manager.add_conversation_entry(
            phone_number=From,
            user_query=SpeechResult,
            aurora_response=aurora_response,
            urgency_level=urgency_level,
            sources=sources,
            call_sid=CallSid
        )
        
        response = VoiceResponse()
        response.say(aurora_response, voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
        
        gather = Gather(
            input='speech',
            action='/process-speech',
            timeout=config.GATHER_TIMEOUT,
            speech_timeout=config.SPEECH_TIMEOUT,
            language='en-US'
        )
        
        response.append(gather)
        
        response.say(
            "If you need more help, please call back. Stay safe. Goodbye.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        response = VoiceResponse()
        response.say(
            "I'm experiencing technical difficulties. Please call back in a moment or contact your supervisor.",
            voice=config.TTS_VOICE, rate=config.SPEECH_RATE
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

@app.post("/api/process-speech")
async def api_process_speech(request: Request):
    """API endpoint for processing speech and returning JSON response"""
    try:
        if request.headers.get("content-type") == "application/json":
            data = await request.json()
            speech_result = data.get('speech', '')
            phone_number = data.get('ph_no', 'Unknown')
            history = data.get('history', [])  # Get conversation history
        else:
            form_data = await request.form()
            speech_result = form_data.get('SpeechResult', '')
            phone_number = form_data.get('From', 'Unknown')
            history = []
        
        if not speech_result or len(speech_result.strip()) < 3:
            return JSONResponse({
                "message": "I couldn't understand that. Please provide clear speech input.",
                "ph_no": phone_number,
                "urgency": "normal"
            })
        
        # IMPORTANT: Pass history to generate_response (not empty list)
        aurora_response, urgency_level, sources = aurora_llm.generate_response(history, speech_result)
        
        print(f"   📜 History length: {len(history)} messages")
        print(f"   🤖 Aurora: {aurora_response}")
        
        call_id, conv_id = active_calls_manager.add_conversation_entry(
            phone_number=phone_number,
            user_query=speech_result,
            aurora_response=aurora_response,
            urgency_level=urgency_level,
            sources=sources
        )
        
        return JSONResponse({
            "message": aurora_response,
            "ph_no": phone_number,
            "urgency": urgency_level
        })
        
    except Exception as e:
        print(f"❌ API Processing error: {e}")
        return JSONResponse({
            "message": "I'm experiencing technical difficulties. Please try again later.",
            "ph_no": "Unknown",
            "urgency": "normal"
        })
           
@app.get("/api/active-calls")
async def get_active_calls():
    """Get all active calls and conversations data"""
    try:
        data = active_calls_manager.get_all_data()
        return JSONResponse(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving active calls: {e}")

@app.get("/api/call/{call_id}")
async def get_call_data(call_id: str):
    """Get specific call data"""
    try:
        call_data = active_calls_manager.get_call_data(call_id)
        if call_data:
            return JSONResponse(call_data)
        else:
            raise HTTPException(status_code=404, detail="Call not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving call data: {e}")

@app.post("/api/call/{call_id}/end")
async def end_call(call_id: str):
    """End a specific call"""
    try:
        success = active_calls_manager.end_call(call_id)
        if success:
            return JSONResponse({"message": "Call ended successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to end call")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ending call: {e}")

@app.post("/call-status")
async def call_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...)
):
    """Handle call status updates (completed, failed, etc.)"""
    print(f"\n📊 CALL STATUS UPDATE")
    print(f"   Call: {CallSid}")
    print(f"   Status: {CallStatus}")
    
    if CallStatus in ['completed', 'failed', 'busy', 'no-answer']:
        summary = conversation_manager.end_conversation(CallSid)
        if summary:
            print(f"   Duration: {summary['duration_seconds']}s")
            print(f"   Exchanges: {summary['exchanges']}")
            print(f"   Critical Alerts: {summary['critical_alerts']}")
    
    return Response(content='', status_code=200)

@app.post("/hangup")
async def hangup(CallSid: str = Form(...)):
    """Handle explicit hangup"""
    conversation_manager.end_conversation(CallSid)
    
    response = VoiceResponse()
    response.say("Goodbye. Stay safe.", voice=config.TTS_VOICE, rate=config.SPEECH_RATE)
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")

@app.get("/web-call", response_class=HTMLResponse)
async def web_call():
    """Web-based phone simulation interface"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aurora Emergency Assistant - Web Call</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .phone-container { 
            background: rgba(255, 255, 255, 0.95);
            border-radius: 24px;
            padding: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 400px;
            max-width: 90vw;
        }
        .header { 
            text-align: center;
            margin-bottom: 24px;
        }
        .header h1 { 
            font-size: 24px;
            color: #2d3748;
            margin-bottom: 8px;
        }
        .header p { 
            font-size: 14px;
            color: #718096;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            background: #48bb78;
            color: white;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }
        .conversation {
            background: #f7fafc;
            border-radius: 16px;
            padding: 16px;
            min-height: 300px;
            max-height: 400px;
            overflow-y: auto;
            margin: 20px 0;
        }
        .message {
            margin: 12px 0;
            padding: 12px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.5;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.user {
            background: #667eea;
            color: white;
            margin-left: 20%;
        }
        .message.aurora {
            background: #e6fffa;
            color: #234e52;
            border-left: 3px solid #48bb78;
            margin-right: 20%;
        }
        .message.system {
            background: #edf2f7;
            color: #4a5568;
            font-size: 12px;
            text-align: center;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin: 20px 0;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .btn-primary {
            background: #48bb78;
            color: white;
        }
        .btn-danger {
            background: #f56565;
            color: white;
        }
        .btn-secondary {
            background: #4299e1;
            color: white;
        }
        .volume-section {
            margin: 20px 0;
        }
        .volume-label {
            font-size: 13px;
            color: #4a5568;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }
        .volume-slider {
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #e2e8f0;
            outline: none;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="phone-container">
        <div class="header">
            <h1>🚨 Aurora Assistant</h1>
            <p>AI Emergency Support</p>
            <span class="status-badge" id="status">Always Listening</span>
        </div>
        
        <div class="conversation" id="conversation">
            <div class="message system">Ready to assist. Speak naturally or click Start Call.</div>
        </div>
        
        <div class="controls">
            <button id="startBtn" class="btn btn-primary">Start Call</button>
            <button id="endBtn" class="btn btn-danger hidden">End Call</button>
            <button id="testBtn" class="btn btn-secondary">Test</button>
        </div>
        
        <div class="volume-section">
            <div class="volume-label">
                <span>Volume</span>
                <span id="volumeVal">50%</span>
            </div>
            <input type="range" id="volume" class="volume-slider" min="0" max="100" value="50">
        </div>
    </div>

    <script>
        class AuroraCall {
            constructor() {
                this.conv = document.getElementById('conversation');
                this.status = document.getElementById('status');
                this.startBtn = document.getElementById('startBtn');
                this.endBtn = document.getElementById('endBtn');
                this.testBtn = document.getElementById('testBtn');
                this.volume = document.getElementById('volume');
                this.volumeVal = document.getElementById('volumeVal');
                this.synthesis = window.speechSynthesis;
                this.recognition = null;
                this.currentVolume = 0.5;
                this.history = []; // Store conversation history
                
                this.startBtn.onclick = () => this.startCall();
                this.endBtn.onclick = () => this.endCall();
                this.testBtn.onclick = () => this.test();
                this.volume.oninput = (e) => {
                    this.currentVolume = e.target.value / 100;
                    this.volumeVal.textContent = e.target.value + '%';
                };
                
                this.initSpeech();
            }
            
            initSpeech() {
                if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
                    this.addMsg('Speech not supported', 'system');
                    return;
                }
                
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.recognition = new SR();
                this.recognition.continuous = true;
                this.recognition.lang = 'en-US';
                
                this.recognition.onresult = (e) => {
                    const text = e.results[e.results.length - 1][0].transcript;
                    if (text.trim().length > 2) {
                        this.addMsg(text, 'user');
                        this.process(text);
                    }
                };
                
                this.recognition.onerror = (e) => {
                    if (e.error === 'not-allowed') {
                        this.addMsg('Microphone blocked', 'system');
                    }
                };
                
                this.recognition.onend = () => {
                    setTimeout(() => {
                        try { this.recognition.start(); } catch(e) {}
                    }, 1000);
                };
                
                try { this.recognition.start(); } catch(e) {}
            }
            
            addMsg(text, type) {
                const div = document.createElement('div');
                div.className = `message ${type}`;
                div.textContent = text;
                this.conv.appendChild(div);
                this.conv.scrollTop = this.conv.scrollHeight;
            }
            
            startCall() {
                this.startBtn.classList.add('hidden');
                this.endBtn.classList.remove('hidden');
                this.status.textContent = 'Call Active';
                this.addMsg('Calling Aurora...', 'system');
                setTimeout(() => {
                    const msg = 'Aurora here. How can I help you today?';
                    this.addMsg(msg, 'aurora');
                    this.speak(msg);
                }, 1500);
            }
            
            endCall() {
                this.endBtn.classList.add('hidden');
                this.startBtn.classList.remove('hidden');
                this.status.textContent = 'Always Listening';
                this.synthesis.cancel();
                this.addMsg('Call ended', 'system');
            }
            
            test() {
                this.addMsg('Testing...', 'system');
                this.process('Hello Aurora, test message');
            }
            
            async process(text) {
                try {
                    // Add user message to history
                    this.history.push({role: 'user', content: text});
                    
                    // Keep only last 10 exchanges (20 messages)
                    if (this.history.length > 20) {
                        this.history = this.history.slice(-20);
                    }
                    
                    const res = await fetch('/api/process-speech', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            speech: text, 
                            ph_no: 'web_user',
                            history: this.history.slice(-20) // Send last 10 exchanges
                        })
                    });
                    const data = await res.json();
                    
                    // Add assistant response to history
                    this.history.push({role: 'assistant', content: data.message});
                    
                    this.addMsg(data.message, 'aurora');
                    this.speak(data.message);
                } catch(e) {
                    this.addMsg('Error: ' + e.message, 'system');
                }
            }
            
            speak(text) {
                this.synthesis.cancel();
                const u = new SpeechSynthesisUtterance(text);
                u.rate = 0.9;
                u.volume = this.currentVolume;
                this.synthesis.speak(u);
            }
        }
        
        new AuroraCall();
    </script>
</body>
</html>
    """

# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Validate configuration and create necessary directories"""
    print("\n" + "="*70)
    print("🚨 AURORA EMERGENCY ASSISTANT - PHONE SYSTEM (FastAPI)")
    print("="*70)
    
    # Validate configuration
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
        print("\n⚠️ Server will start but API calls will fail!")
    else:
        print("\n✓ Configuration validated")
        print(f"✓ Twilio Account: {config.TWILIO_ACCOUNT_SID[:10]}...")
        print(f"✓ Phone Number: {config.TWILIO_PHONE_NUMBER}")
        print(f"✓ Cerebras API: Connected")
    
    # Create necessary directories
    os.makedirs("call_logs", exist_ok=True)
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Run this server: uvicorn aurora_fastapi:app --reload --host 0.0.0.0 --port 5000")
    print("2. In another terminal: ngrok http 5000")
    print("3. Copy ngrok HTTPS URL")
    print("4. Twilio Console → Phone Number → Voice Webhook:")
    print("   - Webhook URL: https://your-ngrok-url.ngrok.io/incoming-call")
    print("   - HTTP POST")
    print("5. Status Callback URL: https://your-ngrok-url.ngrok.io/call-status")
    print("6. Save and call your Twilio number!")
    print("7. Web Call Interface: http://localhost:5000/web-call")
    print("="*70)
    print("\n🚀 Aurora Phone System Ready!")
    print(f"📞 Server running on http://localhost:5000")
    print(f"📚 API Documentation: http://localhost:5000/docs")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")
    print("="*70)
    print("\n🚀 Aurora Phone System Ready!")
    print(f"📞 Server running on http://localhost:5000")
    print(f"📚 API Documentation: http://localhost:5000/docs")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")