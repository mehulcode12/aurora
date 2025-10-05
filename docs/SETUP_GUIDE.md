# Aurora Emergency Assistant - Setup Guide

## 🚀 Complete Setup Instructions

### Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Telegram Bot Setup](#telegram-bot-setup)
4. [Twilio Setup](#twilio-setup)
5. [Firebase Setup](#firebase-setup)
6. [Redis Setup](#redis-setup)
7. [Testing](#testing)
8. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required
- Python 3.10 or 3.11
- pip (Python package manager)
- Git
- Internet connection

### Recommended
- Redis server (local or cloud)
- ngrok (for Twilio webhook testing)
- FFmpeg (for audio processing)

---

## Local Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/mehulcode12/Aurora.git
cd Aurora/API
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install System Dependencies

#### Windows
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract and add to PATH
3. Install PortAudio: `pip install pyaudio`

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg libsndfile1 portaudio19-dev flac
```

#### macOS
```bash
brew install ffmpeg portaudio
```

### 5. Create Environment File
```bash
# Copy template
cp .env.template .env

# Edit .env with your credentials
nano .env  # or use any text editor
```

---

## Telegram Bot Setup

### Step 1: Create Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name (e.g., "Aurora Emergency Assistant")
   - Choose a username (must end with 'bot', e.g., "aurora_emergency_bot")
4. Copy the bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Configure Bot Settings

1. Send `/setdescription` to BotFather
   ```
   Aurora AI Emergency Assistant - Get instant help for emergencies, safety procedures, and work guidance. Available 24/7.
   ```

2. Send `/setabouttext` to BotFather
   ```
   🚨 Aurora Emergency Assistant
   AI-powered emergency response system for industrial workers.
   Send text or voice messages for instant assistance.
   ```

3. Send `/setcommands` to BotFather
   ```
   start - Start conversation with Aurora
   help - Show help and features
   end - End current conversation
   ```

### Step 3: Add Token to .env
```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### Step 4: Test Bot
1. Start your application (see below)
2. Search for your bot in Telegram
3. Send `/start` command
4. Send a test message

---

## Twilio Setup

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/
2. Sign up for free trial account
3. Verify your phone number

### Step 2: Get Phone Number
1. Go to Twilio Console
2. Navigate to Phone Numbers → Manage → Buy a Number
3. Choose a number with Voice capabilities
4. Purchase the number

### Step 3: Get Credentials
1. Go to Twilio Console Dashboard
2. Copy your Account SID
3. Copy your Auth Token
4. Note your Twilio phone number

### Step 4: Add to .env
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### Step 5: Configure Webhooks (Local Testing)

#### Install ngrok
```bash
# Windows
choco install ngrok

# Linux
snap install ngrok

# Or download from https://ngrok.com/
```

#### Start ngrok
```bash
ngrok http 5000
```

#### Configure Twilio
1. Copy ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)
2. Go to Twilio Console → Phone Numbers → Active Numbers
3. Click your number
4. Under Voice Configuration:
   - **Webhook URL**: `https://abc123.ngrok.io/incoming-call`
   - **HTTP Method**: POST
   - **Status Callback URL**: `https://abc123.ngrok.io/call-status`
5. Save

---

## Firebase Setup

### Step 1: Create Firebase Project
1. Go to https://console.firebase.google.com/
2. Click "Add Project"
3. Enter project name (e.g., "aurora-emergency")
4. Disable Google Analytics (optional)
5. Create project

### Step 2: Enable Authentication
1. Go to Authentication → Sign-in method
2. Enable Email/Password
3. Save

### Step 3: Create Firestore Database
1. Go to Firestore Database
2. Click "Create database"
3. Start in production mode
4. Choose location
5. Enable

### Step 4: Create Realtime Database
1. Go to Realtime Database
2. Click "Create database"
3. Start in locked mode
4. Set rules to:
```json
{
  "rules": {
    ".read": "auth != null",
    ".write": "auth != null"
  }
}
```

### Step 5: Generate Service Account Key
1. Go to Project Settings → Service Accounts
2. Click "Generate New Private Key"
3. Download JSON file
4. Extract credentials and add to .env:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
```

### Step 6: Get Web API Key
1. Go to Project Settings → General
2. Scroll to "Your apps"
3. Click Web app icon (</>) or add app
4. Copy Web API Key
5. Add to .env:

```env
FIREBASE_WEB_API_KEY=your-web-api-key
```

---

## Redis Setup

### Option 1: Local Redis (Development)

#### Windows
1. Download Redis from https://github.com/microsoftarchive/redis/releases
2. Extract to `C:\Redis`
3. Run: `redis-server.exe redis.windows.conf`

#### Linux
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

#### macOS
```bash
brew install redis
brew services start redis
```

### Option 2: Cloud Redis (Production)

#### Upstash (Free Tier)
1. Go to https://upstash.com/
2. Create account
3. Create Redis database
4. Copy credentials

#### Redis Cloud
1. Go to https://redis.com/try-free/
2. Create account
3. Create database
4. Copy connection details

### Add to .env
```env
REDIS_HOST=localhost  # or cloud host
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=your_password  # if required
```

---

## Testing

### 1. Start Application
```bash
# Make sure virtual environment is activated
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### 2. Verify Startup Logs
Look for these success messages:
```
✅ Connected to Redis successfully
✅ Aurora LLM initialized
✅ Telegram Bot initialized successfully
✅ Telegram bot is running
✅ Telegram Inactivity Manager started
🚀 Aurora Complete System Ready!
```

### 3. Test Telegram Bot
1. Open Telegram
2. Search for your bot
3. Send `/start`
4. Send test message: "How do I use a fire extinguisher?"
5. Wait for text and voice response

### 4. Test Voice Message
1. In Telegram, record a voice message
2. Send to bot
3. Verify transcription and response

### 5. Test Inactivity
1. Start conversation with bot
2. Wait 3 minutes
3. Check if warning is logged (check console)
4. Wait 2 more minutes
5. Verify conversation is archived

### 6. Test API Endpoints
```bash
# Health check
curl http://localhost:5000/

# Check Redis
curl http://localhost:5000/health/redis

# Get API docs
open http://localhost:5000/docs
```

---

## Production Deployment

### Deploy to Render

#### 1. Push to GitHub
```bash
git add .
git commit -m "Add Telegram integration"
git push origin main
```

#### 2. Create Render Account
1. Go to https://render.com/
2. Sign up with GitHub

#### 3. Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: aurora-emergency-assistant
   - **Environment**: Docker
   - **Plan**: Free
   - **Branch**: main

#### 4. Add Environment Variables
In Render dashboard, add all variables from `.env`:
- `TELEGRAM_BOT_TOKEN`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `CEREBRAS_API_KEY`
- `FIREBASE_*` (all Firebase variables)
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`
- `RESEND_API_KEY`
- `SECRET_KEY`

#### 5. Deploy
1. Click "Create Web Service"
2. Wait for deployment (5-10 minutes)
3. Copy your Render URL (e.g., `https://aurora-emergency.onrender.com`)

#### 6. Update Twilio Webhooks
1. Go to Twilio Console
2. Update webhooks with Render URL:
   - **Voice Webhook**: `https://aurora-emergency.onrender.com/incoming-call`
   - **Status Callback**: `https://aurora-emergency.onrender.com/call-status`

#### 7. Verify Deployment
1. Check Render logs for successful startup
2. Test Telegram bot
3. Make test phone call

---

## Troubleshooting

### Telegram Bot Not Starting
```bash
# Check token format
echo $TELEGRAM_BOT_TOKEN  # Should be: 1234567890:ABC...

# Check logs
# Look for: "✅ Telegram bot is running"

# Verify internet connection
ping api.telegram.org
```

### Audio Issues
```bash
# Check FFmpeg installation
ffmpeg -version

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
# Windows: redis-server.exe
# Linux: sudo systemctl start redis
# macOS: brew services start redis
```

### Firebase Errors
```bash
# Verify credentials in .env
# Check FIREBASE_PRIVATE_KEY has proper \n escaping
# Verify FIREBASE_DATABASE_URL is correct
# Check Firebase Console for service status
```

### Inactivity Manager Not Working
```bash
# Check logs for:
# "✅ Telegram Inactivity Manager started"
# "🔍 Checking for inactive Telegram conversations..."

# Verify APScheduler is installed
pip install APScheduler==3.10.4
```

---

## Configuration Options

### Inactivity Timeouts
```env
# Warning after 2 minutes (120 seconds)
TELEGRAM_INACTIVITY_WARNING=120

# Auto-end after 5 minutes (300 seconds)
TELEGRAM_INACTIVITY_TIMEOUT=300

# Daily cleanup for 24+ hour conversations
TELEGRAM_MAX_CONVERSATION_AGE=86400
```

### Audio Settings
Edit `main.py`:
```python
class Config:
    TTS_SPEED = 1.4  # Change speech rate (1.0 = normal, 1.4 = faster)
```

---

## Next Steps

1. **Customize System Prompt**: Edit `AuroraLLM.__init__()` to customize Aurora's behavior
2. **Add Company Data**: Upload SOPs via admin sign-up endpoint
3. **Configure Workers**: Use admin dashboard to add workers
4. **Monitor Conversations**: Use admin endpoints to view active calls
5. **Review Analytics**: Check Firebase for conversation history

---

## Support

- **Documentation**: See `/docs` folder for detailed guides
- **API Docs**: http://localhost:5000/docs
- **Issues**: https://github.com/mehulcode12/Aurora/issues

---

## Security Best Practices

1. **Never commit .env file** to version control
2. **Use strong SECRET_KEY** for JWT tokens
3. **Rotate API keys** regularly
4. **Enable Firebase security rules** in production
5. **Use HTTPS** for all webhooks
6. **Monitor logs** for suspicious activity
7. **Backup Firebase data** regularly

---

## License

This project is part of the Aurora Emergency Assistant system.

---

**🎉 Congratulations! Your Aurora system with Telegram integration is ready!**
