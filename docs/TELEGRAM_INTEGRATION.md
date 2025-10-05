# Telegram Bot Integration - Aurora Emergency Assistant

## Overview
Aurora now supports text-based emergency assistance through Telegram, in addition to voice calls via Twilio. Users can chat with Aurora, send voice messages, and receive both text and audio responses.

## Features

### 1. Text Messages
- Users can send text queries to Aurora
- Aurora responds with both:
  - Text message with sources in quote format
  - Audio file of the response (TTS with 1.4x speed)

### 2. Voice Messages
- Users can record and send voice messages
- Aurora transcribes the audio to text
- Responds with:
  - Transcription confirmation
  - Text response with sources
  - Audio response

### 3. Commands
- `/start` - Start conversation with Aurora
- `/help` - Show help message and features
- `/end` - Explicitly end current conversation

## Conversation Management

### Hybrid Approach for Conversation End

#### Conversation Flow:
1. **User starts chatting** → Creates entry in `active_conversations/`
2. **User continues chatting** → Updates `last_message_at` timestamp
3. **Conversation ends when:**
   - User types `/end` (explicit)
   - OR 5 minutes of inactivity (automatic)
   - OR conversation is 24+ hours old (daily cleanup)
   - OR admin ends it from dashboard (manual)
4. → Moves to Firestore `conversations/` collection

### Inactivity Detection System

#### Background Job (APScheduler):
- Runs every 60 seconds
- Checks all conversations in `active_conversations/`
- Three thresholds:
  1. **Warning (3 minutes)**: User receives inactivity warning
  2. **Timeout (5 minutes)**: Conversation auto-archived
  3. **Daily Cleanup (24 hours)**: Old conversations archived

#### User Experience:
- **Warning Message**: "⚠️ Your conversation will end in 2 minutes due to inactivity"
- **Timeout Message**: "✅ Conversation ended. Send new message to begin new conversation"
- **User Actions**:
  - Send any new message to keep conversation active
  - Type `/end` to explicitly end conversation
  - Admin can end from dashboard

## Configuration

### Environment Variables
```env
# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Inactivity Settings (optional, defaults shown)
TELEGRAM_INACTIVITY_WARNING=120  # 2 minutes before timeout
TELEGRAM_INACTIVITY_TIMEOUT=300  # 5 minutes of inactivity
TELEGRAM_MAX_CONVERSATION_AGE=86400  # 24 hours
```

### Audio Settings
- **TTS Speed**: 1.4x (configurable in Config class)
- **Audio Format**: OGG with Opus codec (Telegram voice format)
- **Transcription**: Google Speech Recognition (free)

## Installation

### 1. Install Dependencies
```bash
pip install python-telegram-bot==20.7
pip install APScheduler==3.10.4
pip install gTTS==2.4.0
pip install pydub==0.25.1
pip install SpeechRecognition==3.10.0
```

### 2. System Dependencies (for Docker/Linux)
```bash
apt-get install -y ffmpeg libsndfile1 portaudio19-dev flac
```

### 3. Create Telegram Bot
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow prompts to set bot name and username
4. Copy the bot token
5. Add token to `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

## Firebase Database Structure

### Active Conversations (Realtime Database)
```
active_calls/
  {call_id}/
    worker_id: "worker_telegram_123456789"
    mobile_no: "telegram_123456789"
    conversation_id: "conv_telegram_123456789_..."
    urgency: "CRITICAL" | "URGENT" | "NORMAL"
    status: "ACTIVE"
    timestamp: "2025-10-06T15:30:00+05:30"
    medium: "Text"  # <-- Telegram conversations
    last_message_at: "2025-10-06T15:35:00+05:30"
    admin_id: null (or admin_id if taken over)

active_conversations/
  {conversation_id}/
    call_id: "call_telegram_123456789_..."
    messages/
      {message_id}/
        role: "user" | "assistant"
        content: "text content"
        timestamp: "2025-10-06T15:30:00+05:30"
        sources: "OSHA Safety Standards, Emergency Manual"
```

### Archived Conversations (Firestore)
After conversation ends:
- Moved from Realtime DB to Firestore
- Stored in `calls/` and `conversations/` collections
- Follows same schema as voice calls

## API Endpoints

No new API endpoints required - Telegram bot runs independently within the FastAPI application.

### Existing Endpoints Work with Telegram:
- `GET /get-active-calls` - Shows Telegram conversations (medium: "Text")
- `GET /api/conversation/{conversation_id}` - View Telegram conversations
- `GET /api/conversation/{conversation_id}/stream` - Stream Telegram messages
- `POST /api/call/{call_id}/end` - Admin can end Telegram conversation

## Usage Example

### User Experience

#### 1. Starting Conversation
```
User: /start
Aurora: 👋 Hello John!

🚨 I'm Aurora, your Emergency Assistant.

I can help you with:
• Emergency situations
• Safety procedures
• Equipment troubleshooting
• General work guidance

💬 Send me a text message or voice note
🎤 I'll respond with both text and voice

Commands:
/help - Show this help message
/end - End current conversation

⚠️ Conversations auto-end after 5 minutes of inactivity

How can I assist you today?
```

#### 2. Text Query
```
User: How do I operate the fire extinguisher?

Aurora: [typing...]
To operate a fire extinguisher, follow the PASS method:

1. Pull the pin
2. Aim at the base of the fire
3. Squeeze the handle
4. Sweep from side to side

Remember to maintain a safe distance of 6-8 feet.

📚 Sources:
_Fire Safety Protocol, OSHA Safety Standards_

[Voice message: Same content as audio]
```

#### 3. Voice Message
```
User: [sends voice message: "What should I do if there's a gas leak?"]

Aurora: 📝 You said: _What should I do if there's a gas leak?_

[typing...]
If you detect a gas leak:

1. Evacuate immediately
2. Do NOT use any electrical devices
3. Open windows if safe to do so
4. Call emergency services: 911
5. Notify your supervisor

📚 Sources:
_Emergency Procedures Manual, Gas Safety Guide_

[Voice message: Same content as audio]
```

#### 4. Inactivity Warning
```
[After 3 minutes of no activity]
Aurora: ⚠️ Your conversation will end in 2 minutes due to inactivity.
Send a message or type 'continue' to keep it active.

[After 5 minutes total]
Aurora: ✅ Conversation ended. Send new message to begin new conversation.
```

#### 5. Explicit End
```
User: /end

Aurora: ✅ Conversation ended.

Your conversation has been saved.
Send a new message to start a new conversation.
```

## Technical Implementation

### TelegramBotManager Class
- Handles all Telegram bot interactions
- Manages commands and message handlers
- Converts text to speech with 1.4x speed
- Transcribes voice messages to text

### TelegramInactivityManager Class
- Runs APScheduler background job
- Checks conversations every 60 seconds
- Sends warnings at 3 minutes
- Auto-archives at 5 minutes
- Daily cleanup for 24+ hour conversations

### Integration with Existing System
- Uses same `ActiveCallsManager` for storage
- Follows same Firebase structure
- Compatible with admin dashboard
- Works with existing archival system

## Monitoring & Logs

### Console Logs
```
💬 TELEGRAM TEXT MESSAGE
   User: JohnDoe (@123456789)
   Message: How do I reset the machine?
   🤖 Aurora: To reset the machine, follow these steps...
   📊 Urgency Level: normal
   📚 Sources: Equipment Manual, Safety Guidelines

🎤 TELEGRAM VOICE MESSAGE
   User: JaneDoe (@987654321)
   📝 Transcribed: What's the emergency exit route?
   🤖 Aurora: The emergency exit route is...
   📊 Urgency Level: normal
   📚 Sources: Emergency Procedures Manual

🔍 Checking for inactive Telegram conversations...
   ⚠️ Sending inactivity warning for: call_telegram_123456789_...
   ⏰ Ending inactive conversation: call_telegram_987654321_...
   📦 Archiving 24+ hour old conversation: call_telegram_111222333_...
   ✅ Inactivity check complete: 1 warnings, 2 conversations ended
```

## Troubleshooting

### Bot Not Responding
1. Check `TELEGRAM_BOT_TOKEN` in `.env`
2. Verify bot is started in startup logs
3. Check Telegram API status
4. Ensure bot has proper permissions

### Audio Issues
1. Install ffmpeg: `apt-get install ffmpeg`
2. Check pydub installation
3. Verify gTTS can access Google TTS

### Transcription Failures
1. Check audio quality
2. Verify speech_recognition installation
3. Ensure internet connection (uses Google API)

### Inactivity Not Working
1. Check APScheduler logs
2. Verify scheduler started in logs
3. Check Firebase timestamps format

## Security Considerations

1. **User Identification**: Uses Telegram user_id
2. **Phone Number Format**: `telegram_{user_id}`
3. **Worker ID Format**: `worker_telegram_{user_id}`
4. **Admin Access**: Admins can view/end Telegram conversations
5. **Data Privacy**: All data stored securely in Firebase

## Future Enhancements

1. **Warning Notifications**: Send actual Telegram warnings to users
2. **Rich Media**: Support images, documents
3. **Inline Keyboards**: Interactive buttons for common actions
4. **Multi-language**: Support multiple languages
5. **Analytics**: Track usage patterns and response times

## Testing

### Local Testing
```bash
# 1. Set environment variables
export TELEGRAM_BOT_TOKEN=your_token

# 2. Run application
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# 3. Open Telegram and search for your bot
# 4. Send /start command
# 5. Test text and voice messages
```

### Production Deployment
```bash
# Render will automatically:
# 1. Install dependencies from requirements.txt
# 2. Build Docker image with audio libraries
# 3. Start Telegram bot on application startup
# 4. Run inactivity checks every 60 seconds
```

## Conclusion

The Telegram integration provides a seamless text-based interface for Aurora, complementing the voice call system. Users can choose their preferred communication method, and admins have full visibility and control over all conversations regardless of medium.
