"""
Aurora Emergency Assistant - Complete Integrated System
Combines phone call integration (Twilio) with admin authentication and management

Requirements:
pip install fastapi uvicorn twilio cerebras_cloud_sdk python-dotenv python-multipart
pip install redis firebase-admin jose PyPDF2 pdfplumber python-docx requests

Setup Instructions:
1. Create .env file with all required credentials
2. Place serviceAccountKey.json for Firebase
3. Run: uvicorn merged_main:app --reload --host 0.0.0.0 --port 5000
4. For Twilio: expose with ngrok http 5000
"""

from fastapi import FastAPI, Form, Request, HTTPException, status, Depends, File, UploadFile, Header
from fastapi.responses import Response, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from cerebras.cloud.sdk import Cerebras
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import os
import json
import uuid
import random
import asyncio
import time
import redis
import resend
import firebase_admin
from firebase_admin import credentials, firestore, db, initialize_app, auth
import PyPDF2
import pdfplumber
import docx
import io
import requests
import tempfile
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr

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
# CORS: Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- all allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    
    # Voice settings
    TTS_VOICE = "Polly.Amy"
    SPEECH_RATE = "fast"
    TTS_SPEED = 1.4  # For Telegram voice messages
    
    # Conversation settings
    SPEECH_TIMEOUT = "auto"
    GATHER_TIMEOUT = 10
    MAX_CONVERSATION_LENGTH = 20
    TELEGRAM_INACTIVITY_TIMEOUT = 300  # 5 minutes in seconds
    TELEGRAM_INACTIVITY_WARNING = 120  # 2 minutes before timeout
    TELEGRAM_MAX_CONVERSATION_AGE = 86400  # 24 hours in seconds
    
    # JWT settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
    ALGORITHM = "HS256"
    TEMP_TOKEN_EXPIRE_MINUTES = 15
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    
    # Resend Email settings
    RESEND_API_KEY = os.getenv('RESEND_API_KEY')
    RESEND_FROM_EMAIL = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
    
    # Redis settings
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_USERNAME = os.getenv('REDIS_USERNAME')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    
    # Telegram settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

config = Config()

# ============================================================================
# RESEND EMAIL INITIALIZATION
# ============================================================================
resend.api_key = config.RESEND_API_KEY

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
    
    def add_conversation_entry(self, phone_number, user_query, aurora_response, urgency_level, sources=None, call_sid=None, medium="Voice"):
        """Add a new conversation entry following frontend structure"""
        try:
            data = self._load_data()
            
            # Check for existing ACTIVE call for this phone number
            existing_call_id = None
            for call_id, call_data in data["active_calls"].items():
                if call_data["mobile_no"] == phone_number and call_data["status"] == "ACTIVE":
                    existing_call_id = call_id
                    break
            
            # Also check Firebase Realtime DB to ensure call still exists there
            if existing_call_id:
                # Verify the call actually exists in Firebase RT DB
                try:
                    fb_call = db.reference(f'active_calls/{existing_call_id}').get()
                    if not fb_call:
                        # Call was archived, create new one
                        print(f"⚠️ Call {existing_call_id} was archived, creating new call")
                        existing_call_id = None
                except Exception as e:
                    print(f"⚠️ Error checking Firebase for call: {e}")
                    existing_call_id = None
            
            if existing_call_id:
                call_id = existing_call_id
                conv_id = data["active_calls"][call_id]["conversation_id"]
            else:
                call_id = self._generate_call_id(phone_number)
                conv_id = self._generate_conv_id(call_id)
                
                data["active_calls"][call_id] = {
                    "worker_id": f"worker_{phone_number.replace('+', '').replace('-', '').replace('_', '')}",
                    "mobile_no": phone_number,
                    "conversation_id": conv_id,
                    "urgency": urgency_level.upper(),
                    "status": "ACTIVE",
                    "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                    "medium": medium,
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
            
            # Save to local JSON first (fast, synchronous)
            if self._save_data(data):
                print(f"📝 Conversation updated locally for {phone_number}: {call_id}")
                
                # Update Firebase Realtime Database asynchronously (non-blocking)
                self._update_firebase_async(call_id, conv_id, data["active_calls"][call_id], conv_data)
                
                return call_id, conv_id
            else:
                return None, None
            
        except Exception as e:
            print(f"❌ Error updating conversation: {e}")
            return None, None
    
    def _update_firebase_async(self, call_id, conv_id, call_data, conv_data):
        """Update Firebase Realtime Database asynchronously without blocking"""
        try:
            # Use threading to avoid blocking the main conversation flow
            import threading
            
            def firebase_update():
                try:
                    # Update active_calls in Firebase
                    active_calls_ref = db.reference(f'active_calls/{call_id}')
                    active_calls_ref.set(call_data)
                    
                    # Update active_conversations in Firebase
                    active_conversations_ref = db.reference(f'active_conversations/{conv_id}')
                    active_conversations_ref.set(conv_data)
                    
                    print(f"🔥 Firebase updated successfully for {call_id}")
                except Exception as e:
                    print(f"⚠️ Firebase update error (non-critical): {e}")
            
            # Start Firebase update in background thread
            thread = threading.Thread(target=firebase_update, daemon=True)
            thread.start()
            
        except Exception as e:
            print(f"⚠️ Error starting Firebase update thread: {e}")
    
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
    
    def find_active_call_by_phone(self, phone_number):
        """Find active call ID by phone number"""
        try:
            data = self._load_data()
            for call_id, call_data in data["active_calls"].items():
                if call_data["mobile_no"] == phone_number and call_data["status"] == "ACTIVE":
                    return call_id
            return None
        except Exception as e:
            print(f"❌ Error finding call by phone: {e}")
            return None
    
    def end_call(self, call_id):
        """Mark a call as ended and archive to Firestore"""
        try:
            data = self._load_data()
            if call_id in data["active_calls"]:
                call_data = data["active_calls"][call_id]
                conv_id = call_data["conversation_id"]
                conv_data = data["active_conversations"].get(conv_id, {})
                
                # Mark as ended in local JSON
                data["active_calls"][call_id]["status"] = "ENDED"
                
                # Save to local JSON
                if self._save_data(data):
                    # Archive to Firestore and cleanup Firebase Realtime DB asynchronously
                    import threading
                    
                    def archive_and_cleanup():
                        try:
                            # Step 1: Archive call to Firestore calls/ collection
                            self._archive_call_to_firestore(call_id, call_data, conv_data)
                            
                            # Step 2: Archive conversation to Firestore conversations/ collection
                            self._archive_conversation_to_firestore(conv_id, call_id, conv_data)
                            
                            # Step 3: Remove from Firebase Realtime Database
                            db.reference(f'active_calls/{call_id}').delete()
                            db.reference(f'active_conversations/{conv_id}').delete()
                            
                            # Step 4: Clean up local JSON (remove from active_calls and active_conversations)
                            local_data = self._load_data()
                            if call_id in local_data["active_calls"]:
                                del local_data["active_calls"][call_id]
                            if conv_id in local_data["active_conversations"]:
                                del local_data["active_conversations"][conv_id]
                            self._save_data(local_data)
                            
                            print(f"✅ Call {call_id} archived to Firestore and removed from active calls")
                        except Exception as e:
                            print(f"⚠️ Firebase archive error: {e}")
                    
                    thread = threading.Thread(target=archive_and_cleanup, daemon=True)
                    thread.start()
                    
                    return True
            return False
        except Exception as e:
            print(f"❌ Error ending call: {e}")
            return False
    
    def _archive_call_to_firestore(self, call_id, call_data, conv_data):
        """Archive call to Firestore calls/ collection following schema"""
        try:
            # Calculate duration if possible
            start_time = datetime.fromisoformat(call_data["timestamp"].replace('+05:30', ''))
            end_time = datetime.now()
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # Prepare call document following Firestore schema
            call_doc = {
                "worker_id": call_data.get("worker_id", ""),
                "mobile_no": call_data.get("mobile_no", ""),
                "conversation_id": call_data.get("conversation_id", ""),
                "urgency": call_data.get("urgency", "NORMAL"),
                "status": "COMPLETE",  # As per schema: "COMPLETE" | "TAKEOVER"
                "timestamp": firestore.SERVER_TIMESTAMP,
                "medium": call_data.get("medium", "Voice"),
                "final_action": None,  # Can be updated if action was taken
                "admin_id": call_data.get("admin_id"),  # If taken over
                "resolved_at": firestore.SERVER_TIMESTAMP,
                "duration_seconds": duration_seconds,
                "admin_notes": ""  # Can be added by admin
            }
            
            # Save to Firestore calls/ collection
            firestore_db.collection('calls').document(call_id).set(call_doc)
            print(f"📦 Call {call_id} archived to Firestore calls/ collection")
            
        except Exception as e:
            print(f"❌ Error archiving call to Firestore: {e}")
    
    def _archive_conversation_to_firestore(self, conv_id, call_id, conv_data):
        """Archive conversation to Firestore conversations/ collection following schema"""
        try:
            # Extract messages from conversation data
            messages = []
            messages_dict = conv_data.get("messages", {})
            
            for msg_id, msg_data in sorted(messages_dict.items()):
                messages.append({
                    "role": msg_data.get("role", "user"),
                    "content": msg_data.get("content", ""),
                    "timestamp": msg_data.get("timestamp", ""),
                    "sources": msg_data.get("sources", "")
                })
            
            # Prepare conversation document following Firestore schema
            conversation_doc = {
                "call_id": call_id,
                "messages": messages,
                "archived_at": firestore.SERVER_TIMESTAMP,
                "total_messages": len(messages)
            }
            
            # Save to Firestore conversations/ collection
            firestore_db.collection('conversations').document(conv_id).set(conversation_doc)
            print(f"💬 Conversation {conv_id} archived to Firestore conversations/ collection")
            
        except Exception as e:
            print(f"❌ Error archiving conversation to Firestore: {e}")

# ============================================================================
# TELEGRAM BOT MANAGER
# ============================================================================
class TelegramBotManager:
    """Manages Telegram bot interactions and conversations"""
    
    def __init__(self, token: str, aurora_llm, active_calls_manager):
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        
        self.token = token
        self.aurora_llm = aurora_llm
        self.active_calls_manager = active_calls_manager
        self.application = Application.builder().token(token).build()
        self.recognizer = sr.Recognizer()
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("end", self.cmd_end))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
        self.application.add_handler(MessageHandler(filters.AUDIO, self.handle_audio_message))
        
        print("✅ Telegram Bot Manager initialized")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            f"🚨 I'm Aurora, your Emergency Assistant.\n\n"
            f"I can help you with:\n"
            f"• Emergency situations\n"
            f"• Safety procedures\n"
            f"• Equipment troubleshooting\n"
            f"• General work guidance\n\n"
            f"💬 Send me a text message or voice note\n"
            f"🎤 I'll respond with both text and voice\n\n"
            f"Commands:\n"
            f"/help - Show this help message\n"
            f"/end - End current conversation\n\n"
            f"⚠️ Conversations auto-end after 5 minutes of inactivity\n\n"
            f"How can I assist you today?"
        )
        await update.message.reply_text(welcome_message)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "📋 *Aurora Emergency Assistant Help*\n\n"
            "*How to use:*\n"
            "• Send text messages for quick responses\n"
            "• Send voice messages for voice-to-voice assistance\n"
            "• I'll respond with both text and audio\n\n"
            "*Commands:*\n"
            "/start - Start a new conversation\n"
            "/help - Show this help message\n"
            "/end - End current conversation\n\n"
            "*Features:*\n"
            "• Real-time emergency assistance\n"
            "• Step-by-step safety guidance\n"
            "• Source references for information\n"
            "• Voice and text support\n\n"
            "⚠️ *Inactivity Rules:*\n"
            "• Warning after 3 minutes of inactivity\n"
            "• Auto-end conversation after 5 minutes of inactivity\n"
            "• Daily cleanup for 24+ hour old conversations\n\n"
            "Stay safe! 🚨"
        )
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def cmd_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /end command - explicitly end conversation"""
        user_id = str(update.effective_user.id)
        phone_number = f"telegram_{user_id}"
        
        # Find active conversation for this user
        call_id = self.active_calls_manager.find_active_call_by_phone(phone_number)
        
        if call_id:
            success = self.active_calls_manager.end_call(call_id)
            if success:
                await update.message.reply_text(
                    "✅ *Conversation ended.*\n\n"
                    "Your conversation has been saved.\n"
                    "Send a new message to start a new conversation.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Error ending conversation. Please try again.")
        else:
            await update.message.reply_text("ℹ️ No active conversation found.")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages from users"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        user_text = update.message.text
        phone_number = f"telegram_{user_id}"
        
        print(f"\n💬 TELEGRAM TEXT MESSAGE")
        print(f"   User: {username} (@{user_id})")
        print(f"   Message: {user_text}")
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        try:
            # Generate Aurora's response
            aurora_response, urgency_level, sources = self.aurora_llm.generate_response([], user_text)
            
            print(f"   🤖 Aurora: {aurora_response}")
            print(f"   📊 Urgency Level: {urgency_level}")
            print(f"   📚 Sources: {sources}")
            
            # Update conversation in active calls manager
            call_id, conv_id = self.active_calls_manager.add_conversation_entry(
                phone_number=phone_number,
                user_query=user_text,
                aurora_response=aurora_response,
                urgency_level=urgency_level,
                sources=sources,
                call_sid=f"telegram_{user_id}_{int(datetime.now().timestamp())}",
                medium="Text"
            )
            
            # Format response with sources in quote
            formatted_response = aurora_response
            if sources and sources.strip():
                formatted_response += f"\n\n📚 *Sources:*\n_{sources}_"
            
            # Send text response
            await update.message.reply_text(formatted_response, parse_mode='Markdown')
            
            # Generate and send voice response
            await update.message.chat.send_action(action="record_voice")
            voice_file = await self.text_to_speech(aurora_response)
            
            if voice_file:
                with open(voice_file, 'rb') as audio:
                    await update.message.reply_voice(voice=audio)
                # Clean up temp file
                os.remove(voice_file)
            
        except Exception as e:
            print(f"❌ Error processing text message: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                "❌ I'm experiencing technical difficulties. Please try again in a moment."
            )
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages from users"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        phone_number = f"telegram_{user_id}"
        
        print(f"\n🎤 TELEGRAM VOICE MESSAGE")
        print(f"   User: {username} (@{user_id})")
        
        await update.message.reply_text("🎧 Processing your voice message...")
        
        try:
            # Download voice message
            voice_file = await update.message.voice.get_file()
            voice_path = f"temp_voice_{user_id}_{int(datetime.now().timestamp())}.ogg"
            await voice_file.download_to_drive(voice_path)
            
            # Convert OGG to WAV for speech recognition
            audio = AudioSegment.from_ogg(voice_path)
            wav_path = voice_path.replace('.ogg', '.wav')
            audio.export(wav_path, format="wav")
            
            # Transcribe audio
            user_text = await self.transcribe_audio(wav_path)
            
            # Clean up temp files
            os.remove(voice_path)
            os.remove(wav_path)
            
            if not user_text:
                await update.message.reply_text("❌ Sorry, I couldn't understand the audio. Please try again.")
                return
            
            print(f"   📝 Transcribed: {user_text}")
            await update.message.reply_text(f"📝 You said: _{user_text}_", parse_mode='Markdown')
            
            # Generate Aurora's response
            await update.message.chat.send_action(action="typing")
            aurora_response, urgency_level, sources = self.aurora_llm.generate_response([], user_text)
            
            print(f"   🤖 Aurora: {aurora_response}")
            print(f"   📊 Urgency Level: {urgency_level}")
            print(f"   📚 Sources: {sources}")
            
            # Update conversation
            call_id, conv_id = self.active_calls_manager.add_conversation_entry(
                phone_number=phone_number,
                user_query=user_text,
                aurora_response=aurora_response,
                urgency_level=urgency_level,
                sources=sources,
                call_sid=f"telegram_{user_id}_{int(datetime.now().timestamp())}",
                medium="Text"
            )
            
            # Format response with sources in quote
            formatted_response = aurora_response
            if sources and sources.strip():
                formatted_response += f"\n\n📚 *Sources:*\n_{sources}_"
            
            # Send text response
            await update.message.reply_text(formatted_response, parse_mode='Markdown')
            
            # Generate and send voice response
            await update.message.chat.send_action(action="record_voice")
            voice_file = await self.text_to_speech(aurora_response)
            
            if voice_file:
                with open(voice_file, 'rb') as audio:
                    await update.message.reply_voice(voice=audio)
                os.remove(voice_file)
            
        except Exception as e:
            print(f"❌ Error processing voice message: {e}")
            import traceback
            traceback.print_exc()
            await update.message.reply_text(
                "❌ I'm experiencing technical difficulties processing your voice message."
            )
    
    async def handle_audio_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle audio files sent by users"""
        # Redirect to voice message handler
        await self.handle_voice_message(update, context)
    
    async def text_to_speech(self, text: str) -> Optional[str]:
        """Convert text to speech using gTTS with speed 1.4"""
        try:
            # Create a temporary file
            temp_file = f"temp_tts_{int(datetime.now().timestamp())}.mp3"
            
            # Generate speech with gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(temp_file)
            
            # Speed up audio to 1.4x using pydub
            audio = AudioSegment.from_mp3(temp_file)
            # Speed up audio (1.4x means divide duration by 1.4)
            speeded_audio = audio.speedup(playback_speed=config.TTS_SPEED)
            
            # Convert to OGG format (Telegram voice format)
            output_file = temp_file.replace('.mp3', '.ogg')
            speeded_audio.export(output_file, format="ogg", codec="libopus")
            
            # Clean up temp mp3
            os.remove(temp_file)
            
            return output_file
            
        except Exception as e:
            print(f"❌ Error generating TTS: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file to text using speech_recognition"""
        try:
            with sr.AudioFile(audio_path) as source:
                audio_data = self.recognizer.record(source)
                
            # Use Google Speech Recognition (free)
            text = self.recognizer.recognize_google(audio_data)
            return text
            
        except sr.UnknownValueError:
            print("❌ Speech recognition could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Could not request results from speech recognition service: {e}")
            return None
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def start_bot(self):
        """Start the Telegram bot"""
        try:
            print("🚀 Starting Telegram bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            print("✅ Telegram bot started successfully!")
        except Exception as e:
            print(f"❌ Error starting Telegram bot: {e}")
            import traceback
            traceback.print_exc()
    
    async def stop_bot(self):
        """Stop the Telegram bot"""
        try:
            print("🛑 Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            print("✅ Telegram bot stopped")
        except Exception as e:
            print(f"❌ Error stopping Telegram bot: {e}")

# ============================================================================
# TELEGRAM INACTIVITY MANAGER
# ============================================================================
class TelegramInactivityManager:
    """Manages conversation inactivity detection and auto-archival"""
    
    def __init__(self, active_calls_manager):
        self.active_calls_manager = active_calls_manager
        self.scheduler = AsyncIOScheduler()
        self.warned_conversations = set()  # Track conversations that received warnings
        print("✅ Telegram Inactivity Manager initialized")
    
    async def check_inactivity(self):
        """Check for inactive Telegram conversations and handle them"""
        try:
            print("\n🔍 Checking for inactive Telegram conversations...")
            current_time = datetime.now()
            
            # Get all active calls
            data = self.active_calls_manager.get_all_data()
            active_calls = data.get('active_calls', {})
            
            warnings_sent = 0
            conversations_ended = 0
            
            for call_id, call_data in list(active_calls.items()):
                # Only check Telegram conversations (Text medium)
                if call_data.get('medium') != 'Text':
                    continue
                
                # Skip if not a Telegram user
                mobile_no = call_data.get('mobile_no', '')
                if not mobile_no.startswith('telegram_'):
                    continue
                
                # Parse last message timestamp
                last_message_at_str = call_data.get('last_message_at', '')
                try:
                    # Handle different timestamp formats
                    if '+' in last_message_at_str:
                        last_message_at_str = last_message_at_str.split('+')[0]
                    last_message_at = datetime.fromisoformat(last_message_at_str)
                except:
                    print(f"   ⚠️ Could not parse timestamp for call {call_id}")
                    continue
                
                # Calculate time since last message
                time_since_last_message = (current_time - last_message_at).total_seconds()
                
                # Check for 24+ hour old conversations (daily cleanup)
                conversation_age = (current_time - datetime.fromisoformat(
                    call_data.get('timestamp', '').split('+')[0] if '+' in call_data.get('timestamp', '') 
                    else call_data.get('timestamp', '')
                )).total_seconds()
                
                if conversation_age >= config.TELEGRAM_MAX_CONVERSATION_AGE:
                    print(f"   📦 Archiving 24+ hour old conversation: {call_id}")
                    self.active_calls_manager.end_call(call_id)
                    conversations_ended += 1
                    if call_id in self.warned_conversations:
                        self.warned_conversations.remove(call_id)
                    continue
                
                # Check if conversation should be ended (5 minutes of inactivity)
                if time_since_last_message >= config.TELEGRAM_INACTIVITY_TIMEOUT:
                    print(f"   ⏰ Ending inactive conversation: {call_id} (inactive for {time_since_last_message:.0f}s)")
                    
                    # Send notification to user (if we have bot access)
                    # Note: This requires storing chat_id, which we'll add to the call data
                    
                    # End the conversation
                    self.active_calls_manager.end_call(call_id)
                    conversations_ended += 1
                    
                    # Remove from warned set
                    if call_id in self.warned_conversations:
                        self.warned_conversations.remove(call_id)
                
                # Check if warning should be sent (3 minutes of inactivity)
                elif time_since_last_message >= config.TELEGRAM_INACTIVITY_WARNING:
                    if call_id not in self.warned_conversations:
                        print(f"   ⚠️ Sending inactivity warning for: {call_id}")
                        # Mark as warned
                        self.warned_conversations.add(call_id)
                        warnings_sent += 1
                        
                        # Note: To actually send the warning, we need telegram bot instance
                        # This will be handled in the next iteration
            
            print(f"   ✅ Inactivity check complete: {warnings_sent} warnings, {conversations_ended} conversations ended")
            
        except Exception as e:
            print(f"❌ Error in inactivity check: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start the inactivity checker"""
        try:
            # Run check every 1 minute (60 seconds)
            self.scheduler.add_job(
                self.check_inactivity,
                IntervalTrigger(seconds=60),
                id='telegram_inactivity_check',
                name='Check Telegram conversation inactivity',
                replace_existing=True
            )
            self.scheduler.start()
            print("✅ Telegram Inactivity Manager started (checking every 60 seconds)")
        except Exception as e:
            print(f"❌ Error starting Inactivity Manager: {e}")
    
    def stop(self):
        """Stop the inactivity checker"""
        try:
            self.scheduler.shutdown()
            print("✅ Telegram Inactivity Manager stopped")
        except Exception as e:
            print(f"❌ Error stopping Inactivity Manager: {e}")

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
            return "Emergency system error. {Tokens per day limit exceeded - too many tokens processed.} Please call your supervisor at extension 9999 immediately.", "critical", "Emergency Procedures Manual"

# Initialize components
aurora_llm = AuroraLLM(config)
conversation_manager = ConversationManager()
active_calls_manager = ActiveCallsManager()

# Initialize Telegram Bot (only if token is provided)
telegram_bot_manager = None
telegram_inactivity_manager = None
if config.TELEGRAM_BOT_TOKEN:
    try:
        telegram_bot_manager = TelegramBotManager(config.TELEGRAM_BOT_TOKEN, aurora_llm, active_calls_manager)
        telegram_inactivity_manager = TelegramInactivityManager(active_calls_manager)
        print("✅ Telegram Bot initialized successfully")
    except Exception as e:
        print(f"⚠️ Telegram Bot initialization failed: {e}")
        telegram_bot_manager = None
        telegram_inactivity_manager = None
else:
    print("⚠️ TELEGRAM_BOT_TOKEN not found - Telegram bot disabled")

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

class ConversationMessage(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: str
    sources: Optional[str] = ""

class ConversationSnapshot(BaseModel):
    conversation_id: str
    call_id: str
    worker_id: str
    mobile_no: str
    urgency: str
    status: str
    medium: str
    timestamp: str
    messages: List[ConversationMessage]
    total_messages: int
    admin_id: Optional[str] = None

class GetConversationResponse(BaseModel):
    success: bool
    conversation: ConversationSnapshot

# Worker Models
class CreateWorkerRequest(BaseModel):
    mobile_numbers: str
    name: str
    department: str

class UpdateWorkerRequest(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

class Worker(BaseModel):
    worker_id: str
    mobile_numbers: str
    name: str
    department: str
    admin_id: str
    created_at: str
    is_active: bool

class CreateWorkerResponse(BaseModel):
    success: bool
    worker_id: str
    message: str

class GetWorkerResponse(BaseModel):
    success: bool
    worker: Worker

class GetWorkersResponse(BaseModel):
    success: bool
    workers: List[Worker]

class UpdateWorkerResponse(BaseModel):
    success: bool
    message: str

class DeleteWorkerResponse(BaseModel):
    success: bool
    message: str

# Call History Models
class CallHistory(BaseModel):
    call_id: str
    worker_id: str
    mobile_no: str
    conversation_id: str
    urgency: str
    status: str
    timestamp: str
    medium: str
    final_action: Optional[str] = None
    admin_id: Optional[str] = None
    resolved_at: str
    duration_seconds: Optional[int] = None
    admin_notes: Optional[str] = None

class GetCallsHistoryResponse(BaseModel):
    success: bool
    calls: List[CallHistory]
    total_calls: int

class ConversationHistoryMessage(BaseModel):
    role: str
    content: str
    sources: Optional[str] = None
    timestamp: str

class ConversationHistory(BaseModel):
    conversation_id: str
    call_id: str
    messages: List[ConversationHistoryMessage]
    archived_at: str
    total_messages: int

class GetConversationHistoryResponse(BaseModel):
    success: bool
    conversation: ConversationHistory

# Admin Update Models
class UpdateAdminRequest(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None

class UpdateAdminResponse(BaseModel):
    success: bool
    message: str
    admin: AdminProfile

# ============================================================================
# UTILITY FUNCTIONS - OTP & EMAIL
# ============================================================================

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """Send OTP via Resend email service"""
    try:
        print(f"📧 Attempting to send OTP email to {recipient_email}")
        
        params: resend.Emails.SendParams = {
            "from": config.RESEND_FROM_EMAIL,
            "to": [recipient_email],
            "subject": "Your OTP for Aurora Admin Registration",
            "html": f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                  <h2 style="color: #4CAF50; text-align: center;">Aurora Admin Registration</h2>
                  <p>Hello,</p>
                  <p>Your OTP for Aurora Admin registration is:</p>
                  <div style="text-align: center; margin: 30px 0;">
                    <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 8px; background-color: #f5f5f5; padding: 20px; border-radius: 5px;">{otp}</h1>
                  </div>
                  <p>This OTP will expire in <strong>10 minutes</strong>.</p>
                  <p>If you did not request this OTP, please ignore this email.</p>
                  <br>
                  <p style="color: #666;">Best regards,<br><strong>Aurora Emergency Assistant Team</strong></p>
                </div>
              </body>
            </html>
            """,
        }
        
        email: resend.Email = resend.Emails.send(params)
        print(f"✅ Email sent successfully via Resend. Email ID: {email.get('id', 'N/A')}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email via Resend: {str(e)}")
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

async def process_files(files: List[UploadFile]) -> str:
    """Extract and process content from multiple files"""
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
    
    <h2>Worker Management Endpoints:</h2>
    <ul>
        <li>POST /api/workers - Create a new worker (requires auth)</li>
        <li>GET /api/workers - Get all workers for admin (requires auth)</li>
        <li>GET /api/workers/{worker_id} - Get specific worker (requires auth)</li>
        <li>PUT /api/workers/{worker_id} - Update worker information (requires auth)</li>
        <li>DELETE /api/workers/{worker_id} - Delete a worker (requires auth)</li>
    </ul>
    
    <h2>Call History Endpoints:</h2>
    <ul>
        <li>GET /api/calls/history - Get all completed calls for admin (requires auth)</li>
        <li>GET /api/calls/{call_id}/conversation - Get conversation for specific call (requires auth)</li>
    </ul>
    
    <h2>Admin Profile Endpoints:</h2>
    <ul>
        <li>GET /api/admin/profile - Get admin profile information (requires auth)</li>
        <li>PUT /api/admin/profile - Update admin profile (requires auth)</li>
    </ul>
    
    <h2>Documentation:</h2>
    <ul>
        <li>GET /docs - Interactive API documentation (Swagger UI)</li>
        <li>GET /redoc - Alternative API documentation (ReDoc)</li>
    </ul>
    
    <p>Powered by Cerebras AI + Llama + Twilio + Firebase + FastAPI</p>
    <p><strong>🌐 Web Call Interface:</strong> <a href="/web-call" style="color: #007bff;">Try Aurora without a phone!</a></p>
    """

@app.get("/status")
async def get_status():
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
        
        # Note: Archival happens via /call-status webhook when call actually ends
        # Do NOT archive here - this runs on every message exchange!
        
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
    CallStatus: str = Form(...),
    From: str = Form(None)
):
    """Handle call status updates (completed, failed, etc.)"""
    print(f"\n📊 CALL STATUS UPDATE")
    print(f"   Call SID: {CallSid}")
    print(f"   Status: {CallStatus}")
    print(f"   From: {From}")
    
    if CallStatus in ['completed', 'failed', 'busy', 'no-answer']:
        # End conversation in memory
        summary = conversation_manager.end_conversation(CallSid)
        if summary:
            print(f"   Duration: {summary['duration_seconds']}s")
            print(f"   Exchanges: {summary['exchanges']}")
            print(f"   Critical Alerts: {summary['critical_alerts']}")
        
        # Find and archive the call from active_calls_manager
        if From:
            call_id = active_calls_manager.find_active_call_by_phone(From)
            if call_id:
                print(f"   📦 Archiving call {call_id} to Firestore...")
                active_calls_manager.end_call(call_id)
            else:
                print(f"   ⚠️ No active call found for {From}")
    
    return Response(content='', status_code=200)

@app.post("/hangup")
async def hangup(CallSid: str = Form(...), From: str = Form(None)):
    """Handle explicit hangup"""
    # End conversation in memory
    conversation_manager.end_conversation(CallSid)
    
    # Find and archive the call
    if From:
        call_id = active_calls_manager.find_active_call_by_phone(From)
        if call_id:
            print(f"📦 Archiving call {call_id} after explicit hangup")
            active_calls_manager.end_call(call_id)
    
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
            body { font-family: 'Arial', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
            .phone-container { background: #1a1a1a; border-radius: 30px; padding: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); text-align: center; width: 350px; max-width: 90vw; }
            .phone-header { color: #fff; margin-bottom: 20px; }
            .phone-header h1 { font-size: 18px; margin-bottom: 5px; }
            .phone-header p { font-size: 12px; opacity: 0.7; }
            .status-display { background: #000; border-radius: 10px; padding: 15px; margin: 20px 0; min-height: 100px; color: #00ff00; font-family: 'Courier New', monospace; font-size: 14px; text-align: left; overflow-y: auto; max-height: 200px; }
            .call-controls { margin: 20px 0; }
            .call-button { background: #00ff00; color: #000; border: none; border-radius: 50%; width: 80px; height: 80px; font-size: 16px; font-weight: bold; cursor: pointer; margin: 10px; transition: all 0.3s; }
            .call-button:hover { transform: scale(1.1); }
            .call-button.call { background: #00ff00; }
            .call-button.hangup { background: #ff4444; color: #fff; }
            .call-button.speaking { background: #ffaa00; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.1); } 100% { transform: scale(1); } }
            .microphone-button { background: #444; color: #fff; border: none; border-radius: 50%; width: 60px; height: 60px; margin: 10px; cursor: pointer; transition: all 0.3s; }
            .microphone-button:hover { background: #666; }
            .microphone-button.listening { background: #ff4444; animation: pulse 1s infinite; }
            .audio-controls { margin: 20px 0; }
            .volume-control { width: 100%; margin: 10px 0; }
            .instructions { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin-top: 20px; color: #fff; font-size: 12px; }
            .instructions h3 { margin-bottom: 10px; }
            .instructions ul { list-style: none; padding-left: 0; }
            .instructions li { margin: 5px 0; padding-left: 15px; position: relative; }
            .instructions li:before { content: "📞"; position: absolute; left: 0; }
            .hidden { display: none; }
            .thinking { animation: blink 1s infinite; }
            @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.3; } }
        </style>
    </head>
    <body>
        <div class="phone-container">
            <div class="phone-header">
                <h1>🚨 Aurora Emergency Assistant</h1>
                <p>Web Phone Simulation</p>
            </div>
            <div class="status-display" id="statusDisplay">
                <div id="statusMessages">Ready to start call...</div>
            </div>
            <div class="call-controls">
                <button id="startCall" class="call-button call">Start Call</button>
                <button id="endCall" class="call-button hangup hidden">End Call</button>
            </div>
            <div class="audio-controls">
                <button id="micButton" class="microphone-button listening">🎤</button>
                <button id="testButton" class="microphone-button" style="background: #0066cc;">Test</button>
                <div><label for="volumeRange" style="color: #fff; font-size: 12px;">Volume:</label><input type="range" id="volumeRange" class="volume-control" min="0" max="100" value="50"></div>
            </div>
            <div class="instructions">
                <h3>📋 Instructions:</h3>
                <ul><li>Aurora is always listening - just speak naturally</li><li>Click "Test" to test API connection</li><li>Allow microphone access when prompted</li><li>Speak clearly to Aurora</li><li>Wait for Aurora's response</li><li>Optional: Click "Start Call" for formal call mode</li></ul>
            </div>
        </div>
        <script>
            class AuroraWebCall {
                constructor() {
                    this.isCallActive = false; this.isListening = false; this.conversationHistory = []; this.callId = this.generateCallId(); this.synthesis = window.speechSynthesis; this.apiBase = window.location.origin; this.recognition = null;
                    this.initializeElements(); this.setupEventListeners(); this.checkMicrophonePermissions(); this.startContinuousListening();
                }
                initializeElements() {
                    this.statusDisplay = document.getElementById('statusDisplay'); this.statusMessages = document.getElementById('statusMessages'); this.startCallBtn = document.getElementById('startCall'); this.endCallBtn = document.getElementById('endCall'); this.micButton = document.getElementById('micButton'); this.testButton = document.getElementById('testButton'); this.audioControls = document.getElementById('audioControls'); this.volumeRange = document.getElementById('volumeRange');
                }
                setupEventListeners() {
                    this.startCallBtn.addEventListener('click', () => this.startCall());
                    this.endCallBtn.addEventListener('click', () => this.endCall());
                    this.testButton.addEventListener('click', () => this.testAPI());
                    this.volumeRange.addEventListener('input', (e) => { const volume = e.target.value / 100; localStorage.setItem('auroraVolume', volume); });
                    const savedVolume = localStorage.getItem('auroraVolume') || 0.5; this.volumeRange.value = savedVolume * 100;
                }
                generateCallId() { return 'web_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9); }
                
                startContinuousListening() {
                    if (!('SpeechRecognition' in window) && !('webkitSpeechRecognition' in window)) {
                        this.addStatusMessage('❌ Speech recognition not supported in this browser', 'error');
                        return;
                    }

                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    this.recognition = new SpeechRecognition();
                    
                    this.recognition.continuous = true;
                    this.recognition.interimResults = false;
                    this.recognition.lang = 'en-US';
                    this.recognition.maxAlternatives = 1;

                    this.recognition.onstart = () => {
                        this.addStatusMessage('🎤 Continuous listening started - Aurora is always listening', 'success');
                        this.micButton.classList.add('listening');
                    };

                    this.recognition.onresult = (event) => {
                        if (event.results.length > 0) {
                            const transcript = event.results[event.results.length - 1][0].transcript;
                            if (transcript.trim().length > 2) {
                                this.addStatusMessage(`👤 You: ${transcript}`, 'user');
                                this.processSpeech(transcript);
                            }
                        }
                    };

                    this.recognition.onerror = (event) => {
                        this.addStatusMessage(`❌ Speech recognition error: ${event.error}`, 'error');
                        if (event.error === 'not-allowed') {
                            this.addStatusMessage('❌ Microphone access denied. Please allow microphone access.', 'error');
                        }
                    };

                    this.recognition.onend = () => {
                        this.addStatusMessage('🔄 Restarting continuous listening...', 'info');
                        setTimeout(() => {
                            try {
                                this.recognition.start();
                            } catch (error) {
                                this.addStatusMessage(`❌ Error restarting speech recognition: ${error.message}`, 'error');
                            }
                        }, 1000);
                    };

                    try {
                        this.recognition.start();
                    } catch (error) {
                        this.addStatusMessage(`❌ Error starting continuous speech recognition: ${error.message}`, 'error');
                    }
                }
                checkMicrophonePermissions() {
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                        this.addStatusMessage('❌ Browser does not support microphone access', 'error');
                        return;
                    }
                    navigator.mediaDevices.getUserMedia({ audio: true })
                        .then(() => { 
                            this.addStatusMessage('✓ Microphone access ready', 'success'); 
                        })
                        .catch((error) => { 
                            this.addStatusMessage(`❌ Microphone access denied: ${error.message}`, 'error'); 
                        });
                }
                addStatusMessage(message, type = 'info') {
                    const timestamp = new Date().toLocaleTimeString();
                    const color = type === 'error' ? '#ff4444' : type === 'success' ? '#00ff00' : '#00ff00';
                    this.statusMessages.innerHTML += `<div style="color: ${color}; margin: 5px 0;">[${timestamp}] ${message}</div>`;
                    this.statusDisplay.scrollTop = this.statusDisplay.scrollHeight;
                }
                async startCall() {
                    try {
                        this.isCallActive = true; this.startCallBtn.classList.add('hidden'); this.endCallBtn.classList.remove('hidden');
                        this.addStatusMessage('🔄 Calling Aurora...', 'info');
                        setTimeout(() => {
                            this.addStatusMessage('📞 Aurora: Aurora industrial assistant. How can I help you today? Describe your situation or question. You may speak now.', 'info');
                            this.speakText('Aurora industrial assistant. How can I help you today? Describe your situation or question. You may speak now.');
                        }, 1500);
                    } catch (error) { this.addStatusMessage(`❌ Error starting call: ${error.message}`, 'error'); }
                }
                async endCall() {
                    this.isCallActive = false; this.startCallBtn.classList.remove('hidden'); this.endCallBtn.classList.add('hidden'); this.micButton.classList.remove('speaking'); this.synthesis.cancel(); this.addStatusMessage('📞 Call ended. Aurora continues listening.', 'info');
                }
                
                async testAPI() {
                    this.addStatusMessage('🧪 Testing API connection...', 'info');
                    try {
                        const testSpeech = "Hello Aurora, this is a test message";
                        await this.processSpeech(testSpeech);
                    } catch (error) {
                        this.addStatusMessage(`❌ Test failed: ${error.message}`, 'error');
                    }
                }
                async processSpeech(userSpeech) {
                    this.micButton.classList.add('speaking', 'thinking'); 
                    this.addStatusMessage('🤖 Aurora is thinking...', 'thinking');
                    
                    try {
                        this.addStatusMessage(`📤 Sending to Aurora: "${userSpeech}"`, 'info');
                        
                        const response = await fetch(`${this.apiBase}/api/process-speech`, { 
                            method: 'POST', 
                            headers: { 'Content-Type': 'application/json' }, 
                            body: JSON.stringify({ 
                                speech: userSpeech, 
                                ph_no: `web_user_${this.callId}` 
                            }) 
                        });
                        
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        
                        const data = await response.json();
                        this.addStatusMessage(`📥 Received from Aurora: ${JSON.stringify(data)}`, 'info');
                        
                        if (data.message) { 
                            this.addStatusMessage(`🤖 Aurora: ${data.message}`, 'aurora'); 
                            this.speakText(data.message); 
                        } else { 
                            throw new Error('No message in Aurora response'); 
                        }
                    } catch (error) { 
                        this.addStatusMessage(`❌ Error processing speech: ${error.message}`, 'error'); 
                        this.speakText("I'm experiencing technical difficulties. Please try again."); 
                    } finally {
                        setTimeout(() => { 
                            this.micButton.classList.remove('speaking', 'thinking'); 
                        }, 2000);
                    }
                }
                speakText(text) {
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.rate = 0.8; utterance.pitch = 1.0; utterance.volume = this.volumeRange.value / 100;
                    const voices = this.synthesis.getVoices();
                    const preferredVoice = voices.find(voice => voice.name.includes('Microsoft') || voice.name.includes('Google') || voice.name.includes('male'));
                    if (preferredVoice) { utterance.voice = preferredVoice; }
                    utterance.onend = () => { this.micButton.classList.remove('speaking'); };
                    this.synthesis.speak(utterance);
                }
            }
            document.addEventListener('DOMContentLoaded', () => { new AuroraWebCall(); });
        </script>
    </body>
    </html>
    """



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
        
        processed_content = await process_files(files)
        
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
# CONVERSATION ENDPOINTS
# ============================================================================

@app.get("/api/conversation/{conversation_id}", response_model=GetConversationResponse, status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Get a snapshot of a conversation with all messages
    
    This endpoint:
    1. Verifies admin authentication
    2. Checks if the admin has access to this conversation
    3. Returns the complete conversation with all messages
    
    Args:
        conversation_id: The ID of the conversation to retrieve
        token_data: Authentication token data (injected by dependency)
    
    Returns:
        GetConversationResponse: Complete conversation data
    """
    try:
        admin_id = token_data["admin_id"]
        
        # Get admin's company and workers
        company_name = get_admin_company(admin_id)
        workers_ref = firestore_db.collection('workers')
        workers_query = workers_ref.where('admin_id', '==', admin_id).get()
        worker_ids = [worker.id for worker in workers_query]
        
        # Get conversation from Firebase Realtime Database
        active_conversations_ref = db.reference(f'active_conversations/{conversation_id}')
        conversation_data = active_conversations_ref.get()
        
        if not conversation_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found"
            )
        
        call_id = conversation_data.get('call_id')
        
        # Get call data to verify access
        active_calls_ref = db.reference(f'active_calls/{call_id}')
        call_data = active_calls_ref.get()
        
        if not call_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call '{call_id}' not found or no longer active"
            )
        
        # Check if admin has access
        worker_id = call_data.get('worker_id')
        call_admin_id = call_data.get('admin_id')
        
        has_access = (
            call_admin_id == admin_id or 
            (not call_admin_id and worker_id in worker_ids)
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You don't have permission to view this conversation."
            )
        
        # Build messages list
        messages = conversation_data.get('messages', {})
        message_list = []
        
        for msg_id, msg_data in sorted(messages.items()):
            message_list.append(ConversationMessage(
                message_id=msg_id,
                role=msg_data.get('role', 'unknown'),
                content=msg_data.get('content', ''),
                timestamp=msg_data.get('timestamp', ''),
                sources=msg_data.get('sources', '')
            ))
        
        # Build conversation snapshot
        conversation = ConversationSnapshot(
            conversation_id=conversation_id,
            call_id=call_id,
            worker_id=worker_id,
            mobile_no=call_data.get('mobile_no', ''),
            urgency=call_data.get('urgency', 'NORMAL'),
            status=call_data.get('status', 'ACTIVE'),
            medium=call_data.get('medium', 'Text'),
            timestamp=call_data.get('timestamp', ''),
            messages=message_list,
            total_messages=len(message_list),
            admin_id=call_admin_id
        )
        
        return GetConversationResponse(
            success=True,
            conversation=conversation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )

@app.get("/api/conversation/{conversation_id}/stream")
async def stream_conversation(
    conversation_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Stream live conversation updates using Server-Sent Events (SSE)
    
    This endpoint:
    1. Verifies admin authentication
    2. Checks if the admin has access to this conversation
    3. Returns initial conversation messages
    4. Continuously monitors for new messages and streams them in real-time
    
    Args:
        conversation_id: The ID of the conversation to stream
        token_data: Authentication token data (injected by dependency)
    
    Returns:
        EventSourceResponse: SSE stream of conversation messages
    """
    
    async def event_generator():
        """Generator function that yields conversation updates"""
        try:
            admin_id = token_data["admin_id"]
            
            # Get admin's company and workers
            company_name = get_admin_company(admin_id)
            workers_ref = firestore_db.collection('workers')
            workers_query = workers_ref.where('admin_id', '==', admin_id).get()
            worker_ids = [worker.id for worker in workers_query]
            
            # Verify the conversation exists and get call info
            active_conversations_ref = db.reference(f'active_conversations/{conversation_id}')
            conversation_data = active_conversations_ref.get()
            
            if not conversation_data:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "Conversation not found",
                        "conversation_id": conversation_id
                    })
                }
                return
            
            call_id = conversation_data.get('call_id')
            
            # Verify admin has access to this conversation
            active_calls_ref = db.reference(f'active_calls/{call_id}')
            call_data = active_calls_ref.get()
            
            if not call_data:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "Call not found or no longer active",
                        "call_id": call_id
                    })
                }
                return
            
            # Check if admin has access (either assigned to them or unassigned worker from their company)
            worker_id = call_data.get('worker_id')
            call_admin_id = call_data.get('admin_id')
            
            has_access = (
                call_admin_id == admin_id or 
                (not call_admin_id and worker_id in worker_ids)
            )
            
            if not has_access:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": "Access denied. You don't have permission to view this conversation.",
                        "conversation_id": conversation_id
                    })
                }
                return
            
            # Send initial conversation data
            messages = conversation_data.get('messages', {})
            initial_messages = []
            
            for msg_id, msg_data in sorted(messages.items()):
                initial_messages.append({
                    "message_id": msg_id,
                    "role": msg_data.get('role'),
                    "content": msg_data.get('content'),
                    "timestamp": msg_data.get('timestamp'),
                    "sources": msg_data.get('sources', '')
                })
            
            # Send initial data event
            yield {
                "event": "initial",
                "data": json.dumps({
                    "conversation_id": conversation_id,
                    "call_id": call_id,
                    "worker_id": worker_id,
                    "mobile_no": call_data.get('mobile_no'),
                    "urgency": call_data.get('urgency'),
                    "status": call_data.get('status'),
                    "medium": call_data.get('medium'),
                    "timestamp": call_data.get('timestamp'),
                    "messages": initial_messages,
                    "total_messages": len(initial_messages)
                })
            }
            
            # Track the last message count to detect new messages
            last_message_count = len(messages)
            
            # Continuously monitor for new messages
            while True:
                await asyncio.sleep(1)  # Poll every second
                
                # Check if conversation still exists
                conversation_data = active_conversations_ref.get()
                if not conversation_data:
                    yield {
                        "event": "ended",
                        "data": json.dumps({
                            "message": "Conversation has ended",
                            "conversation_id": conversation_id
                        })
                    }
                    break
                
                # Check for new messages
                current_messages = conversation_data.get('messages', {})
                current_count = len(current_messages)
                
                if current_count > last_message_count:
                    # New messages detected
                    new_messages = []
                    sorted_messages = sorted(current_messages.items())
                    
                    # Get only the new messages
                    for msg_id, msg_data in sorted_messages[last_message_count:]:
                        new_messages.append({
                            "message_id": msg_id,
                            "role": msg_data.get('role'),
                            "content": msg_data.get('content'),
                            "timestamp": msg_data.get('timestamp'),
                            "sources": msg_data.get('sources', '')
                        })
                    
                    # Send new messages event
                    yield {
                        "event": "new_messages",
                        "data": json.dumps({
                            "conversation_id": conversation_id,
                            "messages": new_messages,
                            "total_messages": current_count
                        })
                    }
                    
                    last_message_count = current_count
                
                # Check if call status has changed
                call_data = active_calls_ref.get()
                if not call_data:
                    yield {
                        "event": "ended",
                        "data": json.dumps({
                            "message": "Call has ended",
                            "conversation_id": conversation_id
                        })
                    }
                    break
                
                # Send heartbeat every 30 seconds to keep connection alive
                if int(time.time()) % 30 == 0:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({
                            "timestamp": datetime.now().isoformat(),
                            "status": "connected"
                        })
                    }
        
        except Exception as e:
            print(f"Error in conversation stream: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": f"Stream error: {str(e)}",
                    "conversation_id": conversation_id
                })
            }
    
    return EventSourceResponse(event_generator())

# ============================================================================
# WORKER ENDPOINTS
# ============================================================================

@app.post("/api/workers", response_model=CreateWorkerResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(
    request: CreateWorkerRequest,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """Create a new worker in the system"""
    try:
        admin_id = token_data['admin_id']
        
        # Clean mobile number: remove spaces, +, and any special characters
        clean_mobile = request.mobile_numbers.replace('+', '').replace('-', '').replace(' ', '')
        
        # Validate mobile number (should be digits only)
        if not clean_mobile.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number must contain only digits"
            )
        
        # Generate worker_id in format: worker_mobileno
        worker_id = f"worker_{clean_mobile}"
        
        # Check if worker already exists
        worker_ref = firestore_db.collection('workers').document(worker_id)
        if worker_ref.get().exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Worker with mobile number {request.mobile_numbers} already exists"
            )
        
        # Create worker document
        worker_data = {
            "mobile_numbers": request.mobile_numbers,
            "name": request.name,
            "department": request.department,
            "admin_id": admin_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "is_active": True
        }
        
        worker_ref.set(worker_data)
        
        print(f"✅ Worker created: {worker_id}")
        
        return CreateWorkerResponse(
            success=True,
            worker_id=worker_id,
            message="Worker created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating worker: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating worker: {str(e)}"
        )

@app.get("/api/workers", response_model=GetWorkersResponse, status_code=status.HTTP_200_OK)
async def get_workers(
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """Get all workers for the authenticated admin"""
    try:
        admin_id = token_data['admin_id']
        
        # Query workers by admin_id
        workers_ref = firestore_db.collection('workers')
        query = workers_ref.where('admin_id', '==', admin_id).stream()
        
        workers = []
        for doc in query:
            worker_data = doc.to_dict()
            workers.append(Worker(
                worker_id=doc.id,
                mobile_numbers=worker_data.get('mobile_numbers', ''),
                name=worker_data.get('name', ''),
                department=worker_data.get('department', ''),
                admin_id=worker_data.get('admin_id', ''),
                created_at=convert_timestamp(worker_data.get('created_at')),
                is_active=worker_data.get('is_active', True)
            ))
        
        return GetWorkersResponse(
            success=True,
            workers=workers
        )
        
    except Exception as e:
        print(f"❌ Error fetching workers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching workers: {str(e)}"
        )

@app.get("/api/workers/{worker_id}", response_model=GetWorkerResponse, status_code=status.HTTP_200_OK)
async def get_worker(
    worker_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """Get a specific worker by ID"""
    try:
        admin_id = token_data['admin_id']
        
        # Get worker document
        worker_ref = firestore_db.collection('workers').document(worker_id)
        worker_doc = worker_ref.get()
        
        if not worker_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {worker_id} not found"
            )
        
        worker_data = worker_doc.to_dict()
        
        # Verify worker belongs to this admin
        if worker_data.get('admin_id') != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this worker"
            )
        
        worker = Worker(
            worker_id=worker_doc.id,
            mobile_numbers=worker_data.get('mobile_numbers', ''),
            name=worker_data.get('name', ''),
            department=worker_data.get('department', ''),
            admin_id=worker_data.get('admin_id', ''),
            created_at=convert_timestamp(worker_data.get('created_at')),
            is_active=worker_data.get('is_active', True)
        )
        
        return GetWorkerResponse(
            success=True,
            worker=worker
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching worker: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching worker: {str(e)}"
        )

@app.put("/api/workers/{worker_id}", response_model=UpdateWorkerResponse, status_code=status.HTTP_200_OK)
async def update_worker(
    worker_id: str,
    request: UpdateWorkerRequest,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """Update a worker's information"""
    try:
        admin_id = token_data['admin_id']
        
        # Get worker document
        worker_ref = firestore_db.collection('workers').document(worker_id)
        worker_doc = worker_ref.get()
        
        if not worker_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {worker_id} not found"
            )
        
        worker_data = worker_doc.to_dict()
        
        # Verify worker belongs to this admin
        if worker_data.get('admin_id') != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this worker"
            )
        
        # Build update data (only include fields that are provided)
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.department is not None:
            update_data['department'] = request.department
        if request.is_active is not None:
            update_data['is_active'] = request.is_active
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update worker document
        worker_ref.update(update_data)
        
        print(f"✅ Worker updated: {worker_id}")
        
        return UpdateWorkerResponse(
            success=True,
            message="Worker updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating worker: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating worker: {str(e)}"
        )

@app.delete("/api/workers/{worker_id}", response_model=DeleteWorkerResponse, status_code=status.HTTP_200_OK)
async def delete_worker(
    worker_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """Delete a worker from the system"""
    try:
        admin_id = token_data['admin_id']
        
        # Get worker document
        worker_ref = firestore_db.collection('workers').document(worker_id)
        worker_doc = worker_ref.get()
        
        if not worker_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Worker with ID {worker_id} not found"
            )
        
        worker_data = worker_doc.to_dict()
        
        # Verify worker belongs to this admin
        if worker_data.get('admin_id') != admin_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this worker"
            )
        
        # Delete worker document
        worker_ref.delete()
        
        print(f"✅ Worker deleted: {worker_id}")
        
        return DeleteWorkerResponse(
            success=True,
            message="Worker deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting worker: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting worker: {str(e)}"
        )

# ============================================================================
# CALL HISTORY ENDPOINTS
# ============================================================================

@app.get("/api/calls/history", response_model=GetCallsHistoryResponse, status_code=status.HTTP_200_OK)
async def get_calls_history(
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Get all completed/archived calls for the authenticated admin from Firestore
    
    Returns calls that belong to workers under this admin's management
    """
    try:
        admin_id = token_data['admin_id']
        
        # Get all workers for this admin to find their worker_ids
        workers_ref = firestore_db.collection('workers')
        workers_query = workers_ref.where('admin_id', '==', admin_id).stream()
        worker_ids = [worker.id for worker in workers_query]
        
        if not worker_ids:
            # No workers, return empty list
            return GetCallsHistoryResponse(
                success=True,
                calls=[],
                total_calls=0
            )
        
        # Query calls collection for calls from these workers
        calls_ref = firestore_db.collection('calls')
        all_calls = []
        
        # Firestore 'in' query supports max 10 items, so we batch if needed
        batch_size = 10
        for i in range(0, len(worker_ids), batch_size):
            batch_worker_ids = worker_ids[i:i+batch_size]
            calls_query = calls_ref.where('worker_id', 'in', batch_worker_ids).stream()
            
            for doc in calls_query:
                call_data = doc.to_dict()
                all_calls.append(CallHistory(
                    call_id=doc.id,
                    worker_id=call_data.get('worker_id', ''),
                    mobile_no=call_data.get('mobile_no', ''),
                    conversation_id=call_data.get('conversation_id', ''),
                    urgency=call_data.get('urgency', 'NORMAL'),
                    status=call_data.get('status', 'COMPLETE'),
                    timestamp=convert_timestamp(call_data.get('timestamp')),
                    medium=call_data.get('medium', 'Voice'),
                    final_action=call_data.get('final_action'),
                    admin_id=call_data.get('admin_id'),
                    resolved_at=convert_timestamp(call_data.get('resolved_at')),
                    duration_seconds=call_data.get('duration_seconds'),
                    admin_notes=call_data.get('admin_notes', '')
                ))
        
        # Sort by timestamp (most recent first)
        all_calls.sort(key=lambda x: x.timestamp, reverse=True)
        
        print(f"✅ Retrieved {len(all_calls)} call history records for admin {admin_id}")
        
        return GetCallsHistoryResponse(
            success=True,
            calls=all_calls,
            total_calls=len(all_calls)
        )
        
    except Exception as e:
        print(f"❌ Error fetching call history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {str(e)}"
        )

@app.get("/api/calls/{call_id}/conversation", response_model=GetConversationHistoryResponse, status_code=status.HTTP_200_OK)
async def get_call_conversation_history(
    call_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Get conversation history for a specific call from Firestore
    
    Retrieves the archived conversation from Firestore conversations/ collection
    """
    try:
        admin_id = token_data['admin_id']
        
        # First, verify the call belongs to this admin
        call_ref = firestore_db.collection('calls').document(call_id)
        call_doc = call_ref.get()
        
        if not call_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call with ID {call_id} not found"
            )
        
        call_data = call_doc.to_dict()
        worker_id = call_data.get('worker_id', '')
        
        # Verify worker belongs to this admin
        if worker_id:
            worker_ref = firestore_db.collection('workers').document(worker_id)
            worker_doc = worker_ref.get()
            
            if worker_doc.exists:
                worker_data = worker_doc.to_dict()
                if worker_data.get('admin_id') != admin_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You don't have permission to access this call"
                    )
        
        # Get conversation from Firestore
        conversation_id = call_data.get('conversation_id', '')
        
        if not conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation ID not found for this call"
            )
        
        conversation_ref = firestore_db.collection('conversations').document(conversation_id)
        conversation_doc = conversation_ref.get()
        
        if not conversation_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with ID {conversation_id} not found"
            )
        
        conversation_data = conversation_doc.to_dict()
        
        # Parse messages
        messages = []
        for msg in conversation_data.get('messages', []):
            messages.append(ConversationHistoryMessage(
                role=msg.get('role', 'user'),
                content=msg.get('content', ''),
                sources=msg.get('sources', ''),
                timestamp=convert_timestamp(msg.get('timestamp'))
            ))
        
        conversation = ConversationHistory(
            conversation_id=conversation_doc.id,
            call_id=conversation_data.get('call_id', call_id),
            messages=messages,
            archived_at=convert_timestamp(conversation_data.get('archived_at')),
            total_messages=conversation_data.get('total_messages', len(messages))
        )
        
        print(f"✅ Retrieved conversation {conversation_id} for call {call_id}")
        
        return GetConversationHistoryResponse(
            success=True,
            conversation=conversation
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching conversation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching conversation history: {str(e)}"
        )

# ============================================================================
# ADMIN PROFILE ENDPOINTS
# ============================================================================

@app.put("/api/admin/profile", response_model=UpdateAdminResponse, status_code=status.HTTP_200_OK)
async def update_admin_profile(
    request: UpdateAdminRequest,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Update admin profile information
    
    Allows admin to update their name and designation
    Email and company_name cannot be changed
    """
    try:
        admin_id = token_data['admin_id']
        
        # Get admin document
        admin_ref = firestore_db.collection('admins').document(admin_id)
        admin_doc = admin_ref.get()
        
        if not admin_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin profile not found"
            )
        
        admin_data = admin_doc.to_dict()
        
        # Build update data (only include fields that are provided)
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.designation is not None:
            update_data['designation'] = request.designation
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update admin document
        admin_ref.update(update_data)
        
        # Get updated admin data
        updated_admin_doc = admin_ref.get()
        updated_admin_data = updated_admin_doc.to_dict()
        
        print(f"✅ Admin profile updated: {admin_id}")
        
        admin_profile = AdminProfile(
            admin_id=admin_id,
            email=updated_admin_data.get('email', ''),
            name=updated_admin_data.get('name', ''),
            company_name=updated_admin_data.get('company_name', ''),
            designation=updated_admin_data.get('designation', '')
        )
        
        return UpdateAdminResponse(
            success=True,
            message="Admin profile updated successfully",
            admin=admin_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating admin profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating admin profile: {str(e)}"
        )

@app.get("/api/admin/profile", response_model=AdminProfile, status_code=status.HTTP_200_OK)
async def get_admin_profile(
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    """
    Get current admin profile information
    """
    try:
        admin_id = token_data['admin_id']
        
        # Get admin document
        admin_ref = firestore_db.collection('admins').document(admin_id)
        admin_doc = admin_ref.get()
        
        if not admin_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin profile not found"
            )
        
        admin_data = admin_doc.to_dict()
        
        return AdminProfile(
            admin_id=admin_id,
            email=admin_data.get('email', ''),
            name=admin_data.get('name', ''),
            company_name=admin_data.get('company_name', ''),
            designation=admin_data.get('designation', '')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching admin profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching admin profile: {str(e)}"
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
        print(f"✅ Firebase: Connected")
        # print(f"✅ SMTP Email: {config.SMTP_EMAIL}")
    
    os.makedirs("call_logs", exist_ok=True)
    
    # Start Telegram Bot
    if telegram_bot_manager:
        print("\n" + "="*70)
        print("TELEGRAM BOT SETUP:")
        print("="*70)
        try:
            await telegram_bot_manager.start_bot()
            print("✅ Telegram bot is running")
            print(f"📱 Bot Token: {config.TELEGRAM_BOT_TOKEN[:15]}...")
        except Exception as e:
            print(f"❌ Failed to start Telegram bot: {e}")
    
    # Start Inactivity Manager
    if telegram_inactivity_manager:
        try:
            telegram_inactivity_manager.start()
            print("✅ Telegram Inactivity Manager started")
            print(f"⏰ Checking every 60 seconds for inactive conversations")
            print(f"⚠️ Warning threshold: {config.TELEGRAM_INACTIVITY_WARNING}s (2 min)")
            print(f"⏱️ Timeout threshold: {config.TELEGRAM_INACTIVITY_TIMEOUT}s (5 min)")
            print(f"🗓️ Daily cleanup: {config.TELEGRAM_MAX_CONVERSATION_AGE}s (24 hours)")
        except Exception as e:
            print(f"❌ Failed to start Inactivity Manager: {e}")
    
    print("\n" + "="*70)
    print("TWILIO SETUP:")
    print("="*70)
    print("1. Run: uvicorn main:app --reload --host 0.0.0.0 --port 5000")
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
    print(f"� Telegram Bot: {'Enabled' if telegram_bot_manager else 'Disabled'}")
    print(f"�🔐 Admin Auth: Enabled")
    print(f"📱 Server running on http://localhost:5000")
    print(f"📚 API Documentation: http://localhost:5000/docs")
    print(f"🔗 Use ngrok to expose: ngrok http 5000\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\n🛑 Shutting down Aurora system...")
    
    # Stop Telegram Bot
    if telegram_bot_manager:
        try:
            await telegram_bot_manager.stop_bot()
        except Exception as e:
            print(f"⚠️ Error stopping Telegram bot: {e}")
    
    # Stop Inactivity Manager
    if telegram_inactivity_manager:
        try:
            telegram_inactivity_manager.stop()
        except Exception as e:
            print(f"⚠️ Error stopping Inactivity Manager: {e}")
    
    print("✅ Aurora system shutdown complete")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
