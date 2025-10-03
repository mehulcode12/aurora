# Quick Start Guide - Live Conversation Streaming

## 🚀 5-Minute Setup

### Step 1: Update Environment Variables (2 minutes)

Copy your Firebase credentials from `serviceAccountKey.json` to `.env`:

```env
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=aurora-5c9e2
FIREBASE_PRIVATE_KEY_ID=bd6c64523fe95e9f4bce8f05af64b409ca74e403
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC/DyLS/+/DEcw9\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@aurora-5c9e2.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=105362295851052593735
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40aurora-5c9e2.iam.gserviceaccount.com
FIREBASE_UNIVERSE_DOMAIN=googleapis.com
FIREBASE_DATABASE_URL=your_database_url
FIREBASE_WEB_API_KEY=your_web_api_key
```

### Step 2: Install Dependencies (1 minute)

```powershell
pip install sse-starlette==2.1.0
```

### Step 3: Start Server (30 seconds)

```powershell
uvicorn main:app --reload --port 5000
```

### Step 4: Get Auth Token (1 minute)

Login to get JWT token:

```powershell
curl -X POST "http://localhost:5000/login" `
  -H "Content-Type: application/json" `
  -d '{"email": "your_admin@example.com", "password": "your_password"}'
```

Copy the `access_token` from the response.

### Step 5: Test Streaming (30 seconds)

**Option A: Web Interface**
1. Open `conversation_monitor.html` in browser
2. Paste your token
3. Enter conversation ID: `conv_919325590143_20251003_115804`
4. Click "Start Streaming"

**Option B: Python Client**
```powershell
python test_conversation_stream.py YOUR_TOKEN conv_919325590143_20251003_115804
```

**Option C: cURL**
```powershell
curl -N "http://localhost:5000/api/conversation/conv_919325590143_20251003_115804/stream" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Accept: text/event-stream"
```

## 🎉 Done!

You should now see live conversation updates streaming to your client!

## 📖 What's Happening?

1. **Authentication:** Your JWT token is verified
2. **Authorization:** System checks you have access to the conversation
3. **Initial Data:** Complete conversation history is sent
4. **Real-time Updates:** New messages appear as they arrive
5. **Heartbeat:** Connection status monitored every 30 seconds

## 🔍 Verify It's Working

You should see:
- ✅ Initial conversation data with all messages
- ✅ Connection status: "Connected"
- ✅ Heartbeat messages every 30 seconds
- ✅ New messages appear instantly when added

## 🐛 Quick Troubleshooting

### "401 Unauthorized"
- Your token expired - login again

### "403 Forbidden"
- You don't have access to this conversation
- Check if the worker belongs to your company

### "404 Not Found"
- Conversation ID doesn't exist
- Use an active conversation ID

### Connection drops immediately
- Check your internet connection
- Verify server is running on port 5000

## 📚 Next Steps

- Read full documentation: [CONVERSATION_API_DOCS.md](./CONVERSATION_API_DOCS.md)
- Review implementation: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- Setup guide: [LIVE_STREAMING_README.md](./LIVE_STREAMING_README.md)

## 💡 Pro Tips

1. **Save your token:** The web interface auto-saves to localStorage
2. **Multiple conversations:** Open multiple browser tabs for different conversations
3. **Snapshot first:** Use the snapshot endpoint to see current state quickly
4. **Monitor network:** Open browser DevTools → Network to see SSE events

## 🎯 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/conversation/{id}` | GET | Get snapshot |
| `/api/conversation/{id}/stream` | GET | Live stream |
| `/login` | POST | Get auth token |
| `/get-active-calls` | GET | List active calls |

## 🔐 Security Reminders

- ✅ Never share your JWT token
- ✅ Don't commit `.env` file
- ✅ Tokens expire after configured time
- ✅ Logout invalidates token
- ✅ Each admin sees only their company's data

---

**Need Help?** Check the troubleshooting section in [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
