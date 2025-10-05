# 🚨 Aurora Emergency Assistant - Complete System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> AI-powered emergency assistance system for industrial workers with voice calls (Twilio) and text chat (Telegram) support.

---

## 🌟 Features

### 📞 Voice Call System (Twilio)
- Real-time phone call support
- Natural language processing
- Emergency situation detection
- Step-by-step guidance
- Conversation logging

### 💬 Text Chat System (Telegram)
- **NEW!** Text message support
- Voice message transcription
- Dual response (text + audio)
- TTS with 1.4x speed
- Automatic conversation management
- Inactivity detection & warnings

### 🔐 Admin Dashboard
- User authentication (JWT)
- Worker management
- Active call monitoring
- Real-time conversation streaming
- Call history & analytics
- Manual intervention capabilities

### 🤖 AI-Powered Assistance
- Powered by Cerebras AI (Llama 3.3 70B)
- Context-aware responses
- Urgency level detection
- Source attribution
- Multi-turn conversations

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/mehulcode12/Aurora.git
cd Aurora/API
```

### 2. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.template .env
# Edit .env with your credentials
```

### 4. Run Application
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 5. Access Application
- **API**: http://localhost:5000
- **Docs**: http://localhost:5000/docs
- **Health**: http://localhost:5000/status

---

## 📋 System Requirements

### Minimum Requirements
- Python 3.10 or 3.11
- 2 GB RAM
- 1 GB disk space
- Internet connection

### Optional Services
- Redis (for JWT blacklist)
- ngrok (for Twilio webhooks)
- FFmpeg (for audio processing)

---

## 🔧 Configuration

### Required Environment Variables

```env
# Twilio (Voice Calls)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_phone_number

# Telegram (Text Chat)
TELEGRAM_BOT_TOKEN=your_bot_token

# AI Engine
CEREBRAS_API_KEY=your_cerebras_key

# Firebase (Database & Auth)
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_WEB_API_KEY=your_web_api_key
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
# ... (see .env.template for all Firebase vars)

# Redis (Session Management)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# Email (OTP)
RESEND_API_KEY=your_resend_key
RESEND_FROM_EMAIL=your_email@domain.com

# Security
SECRET_KEY=your_secret_key_change_in_production
```

---

## 📱 Telegram Bot Setup

### Step 1: Create Bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` command
3. Choose name and username
4. Copy the bot token

### Step 2: Configure Bot
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Step 3: Test Bot
1. Start application
2. Search for your bot in Telegram
3. Send `/start` command
4. Send test message: "How do I use fire extinguisher?"

### Bot Commands
- `/start` - Start conversation
- `/help` - Show help message
- `/end` - End conversation

---

## 📞 Twilio Call Setup

### Step 1: Get Credentials
1. Create account at https://twilio.com
2. Get phone number with voice capabilities
3. Copy Account SID and Auth Token

### Step 2: Configure Webhooks (Local Testing)
```bash
# Install ngrok
ngrok http 5000

# Copy HTTPS URL and configure in Twilio Console:
# Voice Webhook: https://YOUR-URL.ngrok.io/incoming-call
# Status Callback: https://YOUR-URL.ngrok.io/call-status
```

---

## 🗄️ Database Structure

### Firebase Realtime Database (Active Data)
```
active_calls/
  {call_id}/
    worker_id: string
    mobile_no: string
    urgency: "CRITICAL" | "URGENT" | "NORMAL"
    medium: "Voice" | "Text"
    status: "ACTIVE"
    last_message_at: timestamp

active_conversations/
  {conversation_id}/
    messages/
      {message_id}/
        role: "user" | "assistant"
        content: string
        sources: string
```

### Firestore (Historical Data)
- `admins/` - Admin profiles
- `workers/` - Worker profiles
- `calls/` - Archived calls
- `conversations/` - Archived conversations
- `sops_manuals/` - Company SOPs

---

## 🔄 Conversation Management

### Telegram Conversations End When:
1. **Explicit**: User types `/end`
2. **Inactivity**: 5 minutes of no activity
3. **Daily Cleanup**: 24+ hours old
4. **Admin Action**: Manual end from dashboard

### Inactivity Timeline
- **0 min**: Conversation starts
- **3 min**: Warning logged (system)
- **5 min**: Auto-end & archive
- **24 hours**: Daily cleanup

---

## 🎯 API Endpoints

### Health & Status
```
GET  /                    - Home page
GET  /status              - System status
GET  /health/redis        - Redis health
GET  /docs                - API documentation
```

### Twilio Integration
```
POST /incoming-call       - Handle incoming calls
POST /process-speech      - Process voice input
POST /call-status         - Call status updates
POST /hangup              - Handle call end
```

### Admin Authentication
```
POST /get-otp             - Request OTP
POST /verify-otp          - Verify OTP
POST /sign-up             - Admin registration
POST /login               - Admin login
POST /logout              - Admin logout
```

### Admin Dashboard
```
GET  /get-active-calls              - Active calls
GET  /api/conversation/{id}         - Get conversation
GET  /api/conversation/{id}/stream  - Stream updates
POST /api/call/{id}/end             - End call
```

### Worker Management
```
POST   /api/workers           - Create worker
GET    /api/workers           - List workers
GET    /api/workers/{id}      - Get worker
PUT    /api/workers/{id}      - Update worker
DELETE /api/workers/{id}      - Delete worker
```

### Call History
```
GET /api/calls/history                   - Get call history
GET /api/calls/{id}/conversation         - Get conversation history
```

---

## 📊 Features Comparison

| Feature | Voice (Twilio) | Text (Telegram) |
|---------|----------------|-----------------|
| Real-time assistance | ✅ | ✅ |
| Voice input | ✅ | ✅ (with transcription) |
| Text input | ❌ | ✅ |
| Audio response | ✅ | ✅ (TTS) |
| Text response | ❌ | ✅ |
| Source attribution | ❌ | ✅ (quoted) |
| Inactivity detection | ❌ | ✅ |
| Auto-archival | ✅ | ✅ |
| Admin monitoring | ✅ | ✅ |

---

## 🧪 Testing

### Run Tests
```bash
# Test Redis connection
curl http://localhost:5000/health/redis

# Test Telegram bot
# Send message to your bot on Telegram

# Test API endpoints
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "How do I use fire extinguisher?", "ph_no": "test_user"}'
```

### Manual Testing Checklist
- [ ] Telegram bot responds to /start
- [ ] Text messages work
- [ ] Voice messages transcribed
- [ ] Audio responses generated
- [ ] Sources appear in text
- [ ] Inactivity warnings logged
- [ ] Conversations auto-archive
- [ ] Admin can view active calls
- [ ] Phone calls work (if Twilio configured)

---

## 🚀 Deployment

### Deploy to Render

1. **Push to GitHub**
```bash
git add .
git commit -m "Deploy Aurora"
git push origin main
```

2. **Create Web Service**
- Go to https://render.com
- Connect GitHub repository
- Select Docker environment
- Choose Free plan

3. **Add Environment Variables**
- Add all variables from `.env`
- Click "Create Web Service"

4. **Update Twilio Webhooks**
- Use Render URL for webhooks
- Format: `https://aurora-xyz.onrender.com/incoming-call`

### Docker Deployment

```bash
# Build image
docker build -t aurora-emergency .

# Run container
docker run -p 8000:8000 --env-file .env aurora-emergency
```

---

## 📚 Documentation

- **[Setup Guide](docs/SETUP_GUIDE.md)** - Complete setup instructions
- **[Telegram Integration](docs/TELEGRAM_INTEGRATION.md)** - Telegram bot details
- **[Quick Reference](docs/TELEGRAM_QUICK_REFERENCE.md)** - Quick commands & config
- **[Firebase Structure](docs/Firebase%20Database%20Structure.md)** - Database schema
- **[Implementation Summary](docs/TELEGRAM_IMPLEMENTATION_SUMMARY.md)** - Technical details

---

## 🐛 Troubleshooting

### Bot Not Responding
```bash
# Check token
echo $TELEGRAM_BOT_TOKEN

# Check logs for startup message
# Look for: "✅ Telegram bot is running"
```

### Audio Not Working
```bash
# Install FFmpeg
# Windows: Download from ffmpeg.org
# Linux: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
```

### Redis Connection Failed
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Start Redis
redis-server
```

### Firebase Errors
- Verify all Firebase credentials in `.env`
- Check Firebase Console for service status
- Ensure Realtime Database and Firestore are enabled

---

## 📈 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Aurora System                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │   Telegram   │      │    Twilio    │                 │
│  │     Bot      │      │  Voice Call  │                 │
│  └──────┬───────┘      └──────┬───────┘                 │
│         │                     │                          │
│         └──────────┬──────────┘                          │
│                    │                                     │
│         ┌──────────▼──────────┐                          │
│         │   FastAPI Server    │                          │
│         │   (main.py)         │                          │
│         └──────────┬──────────┘                          │
│                    │                                     │
│         ┌──────────▼──────────┐                          │
│         │   Aurora LLM        │                          │
│         │   (Cerebras AI)     │                          │
│         └──────────┬──────────┘                          │
│                    │                                     │
│    ┌───────────────┼───────────────┐                     │
│    │               │               │                     │
│    ▼               ▼               ▼                     │
│ ┌──────┐    ┌──────────┐    ┌─────────┐                 │
│ │Redis │    │ Firebase  │    │Firebase │                 │
│ │      │    │ Realtime  │    │Firestore│                 │
│ │(JWT) │    │    DB     │    │  (DB)   │                 │
│ └──────┘    └──────────┘    └─────────┘                 │
│                                                           │
│         ┌──────────────────┐                             │
│         │ APScheduler      │                             │
│         │ (Inactivity Mgr) │                             │
│         └──────────────────┘                             │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Security

### Best Practices
- Never commit `.env` file
- Use strong `SECRET_KEY`
- Rotate API keys regularly
- Enable Firebase security rules
- Use HTTPS for webhooks
- Monitor logs for suspicious activity
- Backup Firebase data regularly

### Authentication Flow
1. User requests OTP via email
2. OTP stored in Redis (10 min TTL)
3. User verifies OTP → temporary token
4. User signs up → Firebase Auth user created
5. User logs in → JWT access token (24 hours)
6. Token blacklisted on logout

---

## 📊 Monitoring & Logs

### Key Metrics
- Active conversations count
- Average response time
- Inactivity timeout rate
- Voice transcription accuracy
- LLM response quality

### Log Patterns
```
💬 TELEGRAM TEXT MESSAGE - User sent text
🎤 TELEGRAM VOICE MESSAGE - User sent voice
📞 INCOMING CALL - Phone call received
🤖 Aurora: [response] - AI response
📊 Urgency Level: [level] - Detected urgency
🔍 Checking for inactive... - Background check
⏰ Ending inactive conversation - Auto-archive
```

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 👥 Team

- **Developer**: Mehul
- **Organization**: We Make Devs Hackathon
- **AI Assistant**: GitHub Copilot

---

## 🙏 Acknowledgments

- Cerebras AI for the LLM API
- Twilio for voice call infrastructure
- Telegram for bot API
- Firebase for database & authentication
- FastAPI for the web framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/mehulcode12/Aurora/issues)
- **Docs**: [Documentation](docs/)
- **API**: http://localhost:5000/docs

---

## 🎉 Version History

### v3.0.0 - Telegram Integration (October 2025)
- ✅ Added Telegram bot support
- ✅ Text message handling
- ✅ Voice message transcription
- ✅ Dual response (text + audio)
- ✅ Inactivity detection system
- ✅ Background job scheduler
- ✅ TTS with 1.4x speed
- ✅ Source attribution in text

### v2.0.0 - Admin Dashboard (Previous)
- Admin authentication system
- Worker management
- Call history & analytics
- Real-time conversation streaming

### v1.0.0 - Initial Release
- Twilio voice call integration
- Aurora LLM responses
- Emergency detection
- Basic conversation management

---

**🚨 Aurora Emergency Assistant - Saving lives through AI-powered assistance 🚨**

*For detailed setup and usage instructions, see [Setup Guide](docs/SETUP_GUIDE.md)*
