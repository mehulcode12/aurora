"""
Aurora Emergency Assistant - Complete Integrated System
Combines phone call integration (Twilio) with admin authentication and management

Requirements:
pip install fastapi uvicorn twilio cerebras_cloud_sdk python-dotenv python-multipart
pip install redis firebase-admin jose groq PyPDF2 pdfplumber python-docx requests

Setup Instructions:
1. Create .env file with all required credentials
2. Place serviceAccountKey.json for Firebase
3. Run: uvicorn merged_main:app --reload --host 0.0.0.0 --port 5000
4. For Twilio: expose with ngrok http 5000
"""

from fastapi import FastAPI, Form, Request, HTTPException, status, Depends, File, UploadFile, Header
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from cerebras.cloud.sdk import Cerebras
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from groq import Groq
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import os
import json
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import redis
import firebase_admin
from firebase_admin import credentials, firestore, db, initialize_app, auth
import PyPDF2
import pdfplumber
import docx
import io
import requests

# Load environment variables
load_dotenv()

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================
app = FastAPI(
    title="Aurora Emergency Assistant - Complete System",
    description="AI-powered emergency assistance with phone calls and admin management",
    version="3.0.0"
)

security = HTTPBearer()

# ============================================================================
# FIREBASE INITIALIZATION
# ============================================================================
# Initialize Firebase with environment variables instead of JSON file
firebase_credentials = {
    "type": os.getenv('FIREBASE_TYPE', 'service_account'),
    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
    "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
    "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
    "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_CERT_URL', 'https://www.googleapis.com/oauth2/v1/certs'),
    "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL'),
    "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com')
}

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})
firestore_db = firestore.client()
FIREBASE_WEB_API_KEY = os.getenv('FIREBASE_WEB_API_KEY')

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
    
    # Groq settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Voice settings
    TTS_VOICE = "Polly.Amy"
    SPEECH_RATE = "fast"
    
    # Conversation settings
    SPEECH_TIMEOUT = "auto"
    GATHER_TIMEOUT = 10
    MAX_CONVERSATION_LENGTH = 20
    
    # JWT settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
    ALGORITHM = "HS256"
    TEMP_TOKEN_EXPIRE_MINUTES = 15
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    
    # SMTP settings
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_EMAIL = os.getenv('SMTP_EMAIL')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # Redis settings
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_USERNAME = os.getenv('REDIS_USERNAME')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

config = Config()

# ============================================================================
# REDIS INITIALIZATION
# ============================================================================
redis_client = redis.Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True,
    username=config.REDIS_USERNAME,
    password=config.REDIS_PASSWORD,
    db=0,
)

# Test Redis connection
try:
    redis_client.ping()
    print("✅ Connected to Redis successfully")
except redis.ConnectionError:
    print("❌ Failed to connect to Redis")
    print("\n---------------------------------------------------------------------------------")
    print("Run Redis Server > cd C:\\Redis-x64-3.0.504 && redis-server.exe redis.windows.conf")
    print("---------------------------------------------------------------------------------\n")

# ============================================================================
# GROQ CLIENT INITIALIZATION
# ============================================================================
groq_client = Groq(api_key=config.GROQ_API_KEY)

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
            with open(self.total_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Data saved successfully")
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
                print(f"📝 Conversation updated for {phone_number}: {call_id}")
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
        
        print(f"📋 Call log saved: {filename}")

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
        print("✅ Aurora LLM initialized")
        
        # Load company data from output.txt
        try:
            with open('output.txt', 'r', encoding='utf-8') as f:
                company_data = f.read()
        except Exception as e:
            print(f"⚠️ Error loading company data: {e}")
            company_data = "Company data not available"
        
        # System prompt for phone-based industrial assistance
        self.system_prompt = f"""You are Aurora, an Friendly AI assistant for industrial workers calling via phone.

COMPANY INFORMATION:
######### start ################
{company_data}
######### end ################

Instructions:

PHONE CONVERSATION GUIDELINES:
1. Be CONCISE - phone conversations require brevity
2. Use SHORT sentences - easier to understand over phone
3. Speak CLEARLY - avoid complex words or jargon
4. ONE instruction at a time - don't overwhelm the caller
5. REPEAT important information - ensure understanding
6. Ask for CONFIRMATION when needed - eg: "Do you understand? Say yes or no."

Your core mission:
- Provide IMMEDIATE, ACTIONABLE guidance for ALL work situations
- Help with routine tasks, procedures, troubleshooting, AND emergency situations
- Give clear step-by-step instructions for any work-related question
- Prioritize worker safety and efficiency in all scenarios
- Reference company policies, procedures, and safety protocols
- Assist with daily operations, equipment questions, and general work guidance
- If asking for any things, please tell the exact location. (eg for First aid kit or any other relevant things.)

Response structure:
For EMERGENCIES (fires, injuries, equipment failures, safety hazards):
1. IMMEDIATE ACTION (1 sentence): "Evacuate now."
2. SAFETY STEP (1 sentence): "Follow emergency exit routes."
3. ALERT (1 sentence): "Contact emergency response team immediately."
4. CONFIRMATION: "Did you understand? Say yes or no."
5. ALways share the respective correct contact number


For REGULAR ASSISTANCE (procedures, troubleshooting, guidance):
1. UNDERSTAND the situation: Ask clarifying questions if needed
2. PROVIDE clear steps: Break down complex tasks
3. OFFER alternatives: Suggest backup options when possible
4. CONFIRM understanding: "Does this help? Any questions?"

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

# Initialize components
aurora_llm = AuroraLLM(config)
conversation_manager = ConversationManager()
active_calls_manager = ActiveCallsManager()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

# Admin Auth Models
class EmailRequest(BaseModel):
    email: EmailStr

class OTPResponse(BaseModel):
    success: bool
    message: str

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class VerifyOTPResponse(BaseModel):
    success: bool
    temp_token: str
    expires_in: int

class SignUpResponse(BaseModel):
    success: bool
    admin_id: str
    message: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AdminProfile(BaseModel):
    admin_id: str
    email: str
    name: str
    company_name: str
    designation: str

class LoginResponse(BaseModel):
    success: bool
    access_token: str
    admin: AdminProfile

class ActiveCall(BaseModel):
    call_id: str
    worker_id: str
    mobile_no: str
    conversation_id: str
    urgency: str
    status: str
    timestamp: str
    medium: str
    last_message_at: str
    admin_id: Optional[str] = None

class GetActiveCallsResponse(BaseModel):
    success: bool
    active_calls: List[ActiveCall]

class LogoutResponse(BaseModel):
    success: bool
    message: str

# ============================================================================
# UTILITY FUNCTIONS - OTP & EMAIL
# ============================================================================

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """Send OTP via SMTP email"""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your OTP for Aurora Admin Registration"
        message["From"] = config.SMTP_EMAIL
        message["To"] = recipient_email
        
        text = f"""
        Hello,
        
        Your OTP for Aurora Admin registration is: {otp}
        
        This OTP will expire in 10 minutes.
        
        If you did not request this OTP, please ignore this email.
        
        Best regards,
        Aurora Team
        """
        
        html = f"""
        <html>
          <body>
            <h2>Aurora Admin Registration</h2>
            <p>Hello,</p>
            <p>Your OTP for Aurora Admin registration is:</p>
            <h1 style="color: #4CAF50; font-size: 32px; letter-spacing: 5px;">{otp}</h1>
            <p>This OTP will expire in <strong>10 minutes</strong>.</p>
            <p>If you did not request this OTP, please ignore this email.</p>
            <br>
            <p>Best regards,<br>Aurora Team</p>
          </body>
        </html>
        """
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)
        
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_EMAIL, recipient_email, message.as_string())
        
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def check_email_exists(email: str) -> bool:
    """Check if email exists in Firestore admins collection"""
    try:
        admins_ref = firestore_db.collection('admins')
        query = admins_ref.where('email', '==', email).limit(1).get()
        return len(query) > 0
    except Exception as e:
        print(f"Error checking email in Firestore: {str(e)}")
        raise

def store_otp_in_redis(email: str, otp: str, ttl: int = 600) -> bool:
    """Store OTP in Redis with TTL (default 10 minutes = 600 seconds)"""
    try:
        redis_client.setex(f"otp:{email}", ttl, otp)
        return True
    except Exception as e:
        print(f"Error storing OTP in Redis: {str(e)}")
        return False

# ============================================================================
# UTILITY FUNCTIONS - JWT & AUTH
# ============================================================================

def create_temp_token(email: str) -> str:
    """Generate temporary JWT token valid for 15 minutes"""
    expire = datetime.utcnow() + timedelta(minutes=config.TEMP_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": email,
        "type": "temp",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return token

def verify_temp_token(token: str) -> str:
    """Verify temporary token and extract email"""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        
        if payload.get("type") != "temp":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return email
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or invalid"
        )

def create_access_token(admin_id: str, email: str) -> str:
    """Generate JWT access token valid for 24 hours"""
    expire = datetime.utcnow() + timedelta(hours=config.ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": admin_id,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return token

def verify_access_token_with_blacklist(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT access token and check blacklist"""
    try:
        token = credentials.credentials
        
        # Check if token is blacklisted
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please login again.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        return {
            "admin_id": admin_id,
            "email": payload.get("email"),
            "token": token,
            "exp": payload.get("exp")
        }
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def is_token_blacklisted(token: str) -> bool:
    """Check if token is in Redis blacklist"""
    return redis_client.exists(f"blacklist:{token}") > 0

def blacklist_token(token: str, exp: int):
    """Add token to Redis blacklist with TTL"""
    current_time = int(datetime.utcnow().timestamp())
    ttl = exp - current_time
    
    if ttl > 0:
        redis_client.setex(f"blacklist:{token}", ttl, "revoked")

def authenticate_with_firebase(email: str, password: str) -> dict:
    """Authenticate user with Firebase Auth REST API"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        error_data = response.json()
        error_message = error_data.get('error', {}).get('message', 'Authentication failed')
        
        if error_message == "EMAIL_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not found"
            )
        elif error_message == "INVALID_PASSWORD":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        elif error_message == "USER_DISABLED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been disabled"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    return response.json()

def get_admin_company(admin_id: str) -> str:
    """Get company name for admin from Firestore"""
    try:
        admin_doc = firestore_db.collection('admins').document(admin_id).get()
        if not admin_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        return admin_doc.to_dict().get('company_name')
    except Exception as e:
        print(f"Error fetching admin company: {str(e)}")
        raise

def convert_timestamp(timestamp_value) -> str:
    """Convert Firebase timestamp to ISO format string"""
    try:
        if isinstance(timestamp_value, (int, float)):
            return datetime.fromtimestamp(timestamp_value / 1000).isoformat() + "Z"
        elif isinstance(timestamp_value, str):
            return timestamp_value
        else:
            return datetime.utcnow().isoformat() + "Z"
    except:
        return datetime.utcnow().isoformat() + "Z"

# ============================================================================
# UTILITY FUNCTIONS - FILE PROCESSING
# ============================================================================

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file using pdfplumber"""
    try:
        pdf_file = io.BytesIO(file_content)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n--- Page Break ---\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF: {str(e)}")
        return ""

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        doc_file = io.BytesIO(file_content)
        doc = docx.Document(doc_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting DOCX: {str(e)}")
        return ""

def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT file"""
    try:
        return file_content.decode('utf-8')
    except Exception as e:
        print(f"Error extracting TXT: {str(e)}")
        return ""

async def process_files_with_groq(files: List[UploadFile]) -> str:
    """Extract and process content from multiple files using Groq API"""
    all_text = ""
    
    for file in files:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(content)
        elif filename.endswith('.docx'):
            extracted_text = extract_text_from_docx(content)
        elif filename.endswith('.txt'):
            extracted_text = extract_text_from_txt(content)
        else:
            continue
        
        all_text += f"\n--- {file.filename} ---\n{extracted_text}\n"
    
    return all_text

# ============================================================================
# ENDPOINTS - HOME & HEALTH
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Health check endpoint and status page"""
    return """
    <h1>🚨 Aurora Emergency Assistant - Complete System</h1>
    <p>Status: <strong>Online</strong></p>
    
    <h2>Twilio Phone Integration Endpoints:</h2>
    <ul>
        <li>POST /incoming-call - Handle incoming calls (returns TwiML)</li>
        <li>POST /process-speech - Process worker speech (returns TwiML)</li>
        <li>POST /call-status - Call status updates</li>
        <li>POST /hangup - Handle explicit hangup</li>
        <li>POST /api/process-speech - Process speech (returns JSON)</li>
        <li>GET /api/active-calls-json - Get all active calls from JSON</li>
        <li>GET /api/call/{call_id} - Get specific call data</li>
        <li>POST /api/call/{call_id}/end - End a specific call</li>
    </ul>
    
    <h2>Admin Authentication Endpoints:</h2>
    <ul>
        <li>POST /get-otp - Request OTP for registration</li>
        <li>POST /verify-otp - Verify OTP and get temp token</li>
        <li>POST /sign-up - Complete admin registration</li>
        <li>POST /login - Admin login</li>
        <li>POST /logout - Admin logout (requires auth)</li>
        <li>GET /get-active-calls - Get active calls from Firebase (requires auth)</li>
        <li>GET /health/redis - Check Redis connection</li>
    </ul>
    
    <h2>Documentation:</h2>
    <ul>
        <li>GET /docs - Interactive API documentation (Swagger UI)</li>
        <li>GET /redoc - Alternative API documentation (ReDoc)</li>
    </ul>
    
    <p>Powered by Cerebras AI + Twilio + Firebase + Groq + FastAPI</p>
    """

@app.get("/health/redis")
async def check_redis():
    """Health check endpoint for Redis connection"""
    try:
        redis_client.ping()
        return {"status": "Redis is connected"}
    except redis.ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not connected"
        )

# ============================================================================
# ENDPOINTS - TWILIO PHONE INTEGRATION
# ============================================================================

@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root path (Twilio webhook redirection)"""
    try:
        form_data = await request.form()
        
        if 'CallSid' in form_data:
            print(f"📞 Twilio webhook detected, redirecting to /incoming-call")
            return await incoming_call(
                CallSid=form_data['CallSid'],
                From=form_data.get('From', 'Unknown')
            )
        else:
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
        else:
            form_data = await request.form()
            speech_result = form_data.get('SpeechResult', '')
            phone_number = form_data.get('From', 'Unknown')
        
        if not speech_result or len(speech_result.strip()) < 3:
            return JSONResponse({
                "message": "I couldn't understand that. Please provide clear speech input.",
                "ph_no": phone_number,
                "urgency": "normal"
            })
        
        aurora_response, urgency_level, sources = aurora_llm.generate_response([], speech_result)
        
        print(f"   🤖 Aurora: {aurora_response}")
        print(f"   📊 Urgency Level: {urgency_level}")
        print(f"   📚 Sources: {sources}")
        
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

@app.get("/api/active-calls-json")
async def get_active_calls_json():
    """Get all active calls and conversations data from JSON"""
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
async def end_call_endpoint(call_id: str):
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

# ============================================================================
# ENDPOINTS - ADMIN AUTHENTICATION
# ============================================================================

@app.post("/get-otp", response_model=OTPResponse, status_code=status.HTTP_200_OK)
async def get_otp(request: EmailRequest):
    """
    Generate and send OTP to user's email
    
    - **email**: User's email address
    
    Returns success message if OTP sent successfully
    """
    try:
        email = request.email.lower().strip()
        
        if check_email_exists(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        otp = generate_otp()
        print(f"Generated OTP for {email}: {otp}")
        
        if not store_otp_in_redis(email, otp, ttl=600):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store OTP. Please try again."
            )
        
        if not send_otp_email(email, otp):
            redis_client.delete(f"otp:{email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please check your email address."
            )
        
        return OTPResponse(
            success=True,
            message="OTP sent to email"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@app.post("/verify-otp", response_model=VerifyOTPResponse, status_code=status.HTTP_200_OK)
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP and generate temporary token
    
    - **email**: User's email address
    - **otp**: 6-digit OTP received via email
    """
    try:
        email = request.email.lower().strip()
        otp = request.otp.strip()
        
        stored_otp = redis_client.get(f"otp:{email}")
        
        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or invalid. Please request a new OTP."
            )
        
        if stored_otp != otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP. Please check and try again."
            )
        
        redis_client.delete(f"otp:{email}")
        
        temp_token = create_temp_token(email)
        
        return VerifyOTPResponse(
            success=True,
            temp_token=temp_token,
            expires_in=900
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in verify_otp: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@app.post("/sign-up", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    temp_token: str = Form(...),
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    company_name: str = Form(...),
    designation: str = Form(...),
    files: List[UploadFile] = File(...)
    ):
    """
    Admin sign-up with SOP manual upload
    
    - **temp_token**: Temporary token from verify-otp
    - **name**: Admin full name
    - **email**: Admin email address
    - **password**: Admin password
    - **company_name**: Company name
    - **designation**: Job designation
    - **files**: SOP manual files (PDF, DOCX, TXT)
    """
    try:
        email = email.lower().strip()
        
        token_email = verify_temp_token(temp_token)
        
        if token_email != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match token"
            )
        
        admins_ref = firestore_db.collection('admins')
        existing_admin = admins_ref.where('email', '==', email).limit(1).get()
        if len(existing_admin) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin already exists"
            )
        
        processed_content = await process_files_with_groq(files)
        
        sops_ref = firestore_db.collection('sops_manuals')
        sop_doc_ref = sops_ref.add({
            'sop_manual_guidelines': processed_content,
        })
        sop_manual_id = sop_doc_ref[1].id
        
        firebase_user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        
        admin_doc_ref = admins_ref.document(firebase_user.uid)
        admin_doc_ref.set({
            'email': email,
            'name': name,
            'company_name': company_name,
            'designation': designation,
            'sop_manuals_id': sop_manual_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': None
        })
        admin_id = firebase_user.uid
        
        return SignUpResponse(
            success=True,
            admin_id=admin_id,
            message="Admin registered successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in sign_up: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    Admin login endpoint
    
    - **email**: Admin email address
    - **password**: Admin password
    """
    try:
        email = request.email.lower().strip()
        
        firebase_response = authenticate_with_firebase(email, request.password)
        firebase_uid = firebase_response.get('localId')
        
        admins_ref = firestore_db.collection('admins')
        admin_query = admins_ref.where('email', '==', email).limit(1).get()
        
        if len(admin_query) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin profile not found"
            )
        
        admin_doc = admin_query[0]
        admin_data = admin_doc.to_dict()
        admin_id = admin_doc.id
        
        admins_ref.document(admin_id).update({
            'last_login': firestore.SERVER_TIMESTAMP
        })
        
        access_token = create_access_token(admin_id, email)
        
        admin_profile = AdminProfile(
            admin_id=admin_id,
            email=admin_data['email'],
            name=admin_data['name'],
            company_name=admin_data['company_name'],
            designation=admin_data['designation']
        )
        
        return LoginResponse(
            success=True,
            access_token=access_token,
            admin=admin_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )

@app.get("/get-active-calls", response_model=GetActiveCallsResponse, status_code=status.HTTP_200_OK)
async def get_active_calls(token_data: dict = Depends(verify_access_token_with_blacklist)):
    """
    Get active calls for logged-in admin from Firebase
    
    Returns active calls that are:
    - Taken over by the logged-in admin (admin_id matches)
    - Unassigned calls from workers in the same company
    """
    try:
        admin_id = token_data["admin_id"]
        
        company_name = get_admin_company(admin_id)
        
        workers_ref = firestore_db.collection('workers')
        workers_query = workers_ref.where('admin_id', '==', admin_id).get()
        worker_ids = [worker.id for worker in workers_query]
        
        active_calls_ref = db.reference('active_calls')
        all_calls = active_calls_ref.get()
        
        filtered_calls = []
        
        if all_calls:
            for call_id, call_data in all_calls.items():
                if (call_data.get('admin_id') == admin_id or 
                    (not call_data.get('admin_id') and call_data.get('worker_id') in worker_ids)):
                    
                    active_call = ActiveCall(
                        call_id=call_id,
                        worker_id=call_data.get('worker_id', ''),
                        mobile_no=call_data.get('mobile_no', ''),
                        conversation_id=call_data.get('conversation_id', ''),
                        urgency=call_data.get('urgency', 'NORMAL'),
                        status=call_data.get('status', 'ACTIVE'),
                        timestamp=convert_timestamp(call_data.get('timestamp')),
                        medium=call_data.get('medium', 'Text'),
                        last_message_at=convert_timestamp(call_data.get('last_message_at')),
                        admin_id=call_data.get('admin_id')
                    )
                    filtered_calls.append(active_call)
        
        urgency_priority = {'CRITICAL': 0, 'URGENT': 1, 'NORMAL': 2}
        filtered_calls.sort(key=lambda x: urgency_priority.get(x.urgency, 3))
        
        return GetActiveCallsResponse(
            success=True,
            active_calls=filtered_calls
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_active_calls: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active calls"
        )

@app.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(token_data: dict = Depends(verify_access_token_with_blacklist)):
    """
    Admin logout endpoint
    
    Invalidates the current JWT token by adding it to Redis blacklist
    """
    try:
        admin_id = token_data["admin_id"]
        token = token_data["token"]
        exp = token_data["exp"]
        
        if is_token_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token already invalidated"
            )
        
        blacklist_token(token, exp)
        
        firestore_db.collection('admins').document(admin_id).update({
            'last_logout': firestore.SERVER_TIMESTAMP
        })
        
        return LogoutResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again."
        )

# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Validate configuration and create necessary directories"""
    print("\n" + "="*70)
    print("🚨 AURORA EMERGENCY ASSISTANT - COMPLETE SYSTEM")
    print("="*70)
    
    missing = []
    if not config.CEREBRAS_API_KEY:
        missing.append("CEREBRAS_API_KEY")
    if not config.TWILIO_ACCOUNT_SID:
        missing.append("TWILIO_ACCOUNT_SID")
    if not config.TWILIO_AUTH_TOKEN:
        missing.append("TWILIO_AUTH_TOKEN")
    if not config.TWILIO_PHONE_NUMBER:
        missing.append("TWILIO_PHONE_NUMBER")
    if not config.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not config.SMTP_EMAIL:
        missing.append("SMTP_EMAIL")
    if not config.SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not FIREBASE_WEB_API_KEY:
        missing.append("FIREBASE_WEB_API_KEY")
    
    if missing:
        print("\n❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\n⚠️ Server will start but some features will fail!")
    else:
        print("\n✅ Configuration validated")
        print(f"✅ Twilio Account: {config.TWILIO_ACCOUNT_SID[:10]}...")
        print(f"✅ Phone Number: {config.TWILIO_PHONE_NUMBER}")
        print(f"✅ Cerebras API: Connected")
        print(f"✅ Groq API: Connected")
        print(f"✅ Firebase: Connected")
        print(f"✅ SMTP Email: {config.SMTP_EMAIL}")
    
    os.makedirs("call_logs", exist_ok=True)
    
    print("\n" + "="*70)
    print("TWILIO SETUP:")
    print("="*70)
    print("1. Run: uvicorn merged_main:app --reload --host 0.0.0.0 --port 5000")
    print("2. In another terminal: ngrok http 5000")
    print("3. Copy ngrok HTTPS URL")
    print("4. Twilio Console → Phone Number → Voice Webhook:")
    print("   - Webhook URL: https://your-ngrok-url.ngrok.io/incoming-call")
    print("   - HTTP POST")
    print("5. Status Callback URL: https://your-ngrok-url.ngrok.io/call-status")
    print("6. Save and call your Twilio number!")
    print("="*70)
    print("\n🚀 Aurora Complete System Ready!")
    print(f"📞 Phone System: Enabled")
    print(f"🔐 Admin Auth: Enabled")
    print(f"📱 Server running on http://localhost:5000")
    print(f"📚 API Documentation: http://localhost:5000/docs")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
