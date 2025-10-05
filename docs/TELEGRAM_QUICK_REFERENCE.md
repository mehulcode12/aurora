# Telegram Bot - Quick Reference

## 🚀 Quick Start

### 1. Setup Telegram Bot
```bash
# 1. Create bot with @BotFather on Telegram
# 2. Get bot token
# 3. Add to .env file
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> .env
```

### 2. Install Dependencies
```bash
pip install python-telegram-bot==20.7 APScheduler==3.10.4 gTTS==2.4.0 pydub==0.25.1 SpeechRecognition==3.10.0
```

### 3. Run Application
```bash
uvicorn main:app --reload
```

## 📱 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start conversation with Aurora |
| `/help` | Show help message |
| `/end` | End current conversation |

## 💬 Message Types Supported

| Type | User Action | Aurora Response |
|------|-------------|-----------------|
| **Text** | Send text message | Text + Audio reply |
| **Voice** | Send voice note | Transcription + Text + Audio reply |
| **Audio** | Send audio file | Same as voice |

## ⏱️ Conversation Timeouts

| Event | Time | Action |
|-------|------|--------|
| Warning | 3 min inactivity | Aurora sends warning |
| Auto-end | 5 min inactivity | Conversation archived |
| Daily cleanup | 24 hours old | Automatic archival |
| Manual end | Anytime | User types `/end` |

## 🗂️ Database Structure

### Phone Number Format
```
telegram_{user_id}
Example: telegram_123456789
```

### Worker ID Format
```
worker_telegram_{user_id}
Example: worker_telegram_123456789
```

### Call ID Format
```
call_telegram_{user_id}_{timestamp}
Example: call_telegram_123456789_1696587600
```

### Medium Type
```
"Text" - for all Telegram conversations
"Voice" - for Twilio phone calls
```

## 🔧 Configuration

### Environment Variables
```env
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_INACTIVITY_WARNING=120  # 2 minutes
TELEGRAM_INACTIVITY_TIMEOUT=300  # 5 minutes
TELEGRAM_MAX_CONVERSATION_AGE=86400  # 24 hours
```

### Audio Settings
```python
TTS_SPEED = 1.4  # Speech rate for audio responses
```

## 📊 Key Classes

### TelegramBotManager
- Handles bot commands
- Processes text/voice messages
- Generates TTS audio
- Transcribes voice messages

### TelegramInactivityManager
- Background scheduler (60s interval)
- Checks conversation activity
- Sends warnings
- Auto-archives inactive conversations

## 🔍 Monitoring

### Check Bot Status
```python
# Look for these logs on startup:
✅ Telegram Bot initialized successfully
✅ Telegram bot is running
✅ Telegram Inactivity Manager started
```

### Conversation Logs
```
💬 TELEGRAM TEXT MESSAGE
   User: JohnDoe (@123456789)
   Message: ...
   🤖 Aurora: ...
   📊 Urgency Level: ...
   📚 Sources: ...

🔍 Checking for inactive Telegram conversations...
   ✅ Inactivity check complete: X warnings, Y conversations ended
```

## 🐛 Common Issues

### Bot Not Responding
```bash
# Check token
echo $TELEGRAM_BOT_TOKEN

# Check logs
# Look for "Telegram bot is running" message
```

### Audio Not Working
```bash
# Install ffmpeg
sudo apt-get install ffmpeg libsndfile1

# Or on Windows
# Download ffmpeg from ffmpeg.org
```

### Transcription Failing
```bash
# Check internet connection
ping google.com

# Install dependencies
pip install SpeechRecognition
```

## 📝 Example Conversation Flow

```
1. User: /start
   → Aurora sends welcome message

2. User: "How do I use fire extinguisher?"
   → Aurora sends text response with sources
   → Aurora sends voice message (same content)

3. [User inactive for 3 minutes]
   → Aurora sends inactivity warning

4. User: "Thanks!"
   → Conversation continues (reset timer)

5. [User inactive for 5 minutes]
   → Aurora auto-ends conversation
   → Data archived to Firestore

OR

5. User: /end
   → Conversation ends immediately
   → Data archived to Firestore
```

## 🔐 Admin Dashboard Integration

### View Telegram Conversations
```
GET /get-active-calls
→ Returns all active calls including Telegram (medium: "Text")
```

### Stream Telegram Messages
```
GET /api/conversation/{conversation_id}/stream
→ Real-time updates for Telegram conversations
```

### End Telegram Conversation
```
POST /api/call/{call_id}/end
→ Admin can manually end any Telegram conversation
```

## 🚀 Deployment Checklist

- [ ] Set `TELEGRAM_BOT_TOKEN` in environment
- [ ] Install Python dependencies
- [ ] Install system dependencies (ffmpeg, etc.)
- [ ] Verify bot starts on application startup
- [ ] Test text messages
- [ ] Test voice messages
- [ ] Verify inactivity manager is running
- [ ] Check Firebase integration
- [ ] Test admin dashboard integration

## 📚 Related Documentation

- [Full Integration Guide](TELEGRAM_INTEGRATION.md)
- [Firebase Database Structure](Firebase%20Database%20Structure.md)
- [API Documentation](http://localhost:5000/docs)

---

**Need Help?** Check logs for error messages or refer to the full integration documentation.
