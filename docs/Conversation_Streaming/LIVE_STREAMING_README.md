# Aurora - Live Conversation Streaming

## 🎯 Overview

This update adds real-time conversation streaming capabilities to the Aurora Emergency Assistant API. Admins can now monitor active emergency conversations in real-time using Server-Sent Events (SSE).

## ✨ New Features

### 1. **Live Conversation Streaming (SSE)**
- Real-time updates when new messages arrive
- Automatic reconnection handling
- Heartbeat monitoring to keep connections alive
- Graceful handling of conversation endings

### 2. **Conversation Snapshot Endpoint**
- Retrieve complete conversation history at any point
- Fast access to all messages without streaming overhead
- Perfect for displaying historical conversations

### 3. **Enhanced Authentication & Authorization**
- JWT token-based authentication
- Role-based access control
- Admins can only view conversations from their company's workers
- Automatic access verification for taken-over calls

## 📋 Prerequisites

- Python 3.11+
- FastAPI
- Firebase (Realtime Database & Firestore)
- Redis
- All packages from `requirements.txt`

## 🚀 Installation

### 1. Install New Dependencies

```powershell
# Using pip
pip install sse-starlette==2.1.0

# Or install all requirements
pip install -r requirements.txt
```

### 2. Environment Variables

Add these Firebase credentials to your `.env` file:

```env
# Firebase Configuration
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nyour_private_key\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_CERT_URL=your_client_cert_url
FIREBASE_UNIVERSE_DOMAIN=googleapis.com
FIREBASE_DATABASE_URL=your_database_url
FIREBASE_WEB_API_KEY=your_web_api_key
```

**Note:** You can now delete the `serviceAccountKey.json` file as all credentials are loaded from environment variables.

### 3. Start the Server

```powershell
# Development mode
uvicorn main:app --reload --host 0.0.0.0 --port 5000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4
```

## 📡 API Endpoints

### Get Conversation Snapshot

```http
GET /api/conversation/{conversation_id}
Authorization: Bearer <your_jwt_token>
```

**Response:**
```json
{
  "success": true,
  "conversation": {
    "conversation_id": "conv_919325590143_20251003_115804",
    "call_id": "call_919325590143_20251003_115804",
    "worker_id": "worker_919325590143",
    "mobile_no": "+919325590143",
    "urgency": "CRITICAL",
    "status": "ACTIVE",
    "medium": "Voice",
    "timestamp": "2025-10-03T11:58:04+05:30",
    "messages": [...],
    "total_messages": 10,
    "admin_id": null
  }
}
```

### Stream Live Conversation

```http
GET /api/conversation/{conversation_id}/stream
Authorization: Bearer <your_jwt_token>
Accept: text/event-stream
```

**SSE Events:**
- `initial` - Complete conversation history
- `new_messages` - New messages as they arrive
- `heartbeat` - Connection keep-alive (every 30s)
- `ended` - Conversation/call ended
- `error` - Error occurred

## 🧪 Testing

### Method 1: Web Interface

1. Open `conversation_monitor.html` in your browser
2. Enter your JWT token and conversation ID
3. Click "Start Streaming" to watch live updates

### Method 2: Python Test Client

```powershell
python test_conversation_stream.py <JWT_TOKEN> <CONVERSATION_ID>
```

Example:
```powershell
python test_conversation_stream.py eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... conv_919325590143_20251003_115804
```

### Method 3: cURL

**Snapshot:**
```powershell
curl -X GET "http://localhost:5000/api/conversation/conv_919325590143_20251003_115804" `
  -H "Authorization: Bearer YOUR_JWT_TOKEN" `
  -H "Accept: application/json"
```

**Stream:**
```powershell
curl -N -X GET "http://localhost:5000/api/conversation/conv_919325590143_20251003_115804/stream" `
  -H "Authorization: Bearer YOUR_JWT_TOKEN" `
  -H "Accept: text/event-stream"
```

## 💻 Client Implementation

### JavaScript/Browser

```javascript
const conversationId = 'conv_919325590143_20251003_115804';
const token = 'your_jwt_token';

const eventSource = new EventSource(
  `/api/conversation/${conversationId}/stream`
);

eventSource.addEventListener('initial', (event) => {
  const data = JSON.parse(event.data);
  console.log('Initial conversation:', data);
});

eventSource.addEventListener('new_messages', (event) => {
  const data = JSON.parse(event.data);
  console.log('New messages:', data.messages);
});

eventSource.addEventListener('ended', () => {
  console.log('Conversation ended');
  eventSource.close();
});
```

### Python

```python
import requests
import json

url = 'http://localhost:5000/api/conversation/conv_123/stream'
headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'text/event-stream'
}

with requests.get(url, headers=headers, stream=True) as response:
    for line in response.iter_lines():
        if line.startswith(b'data:'):
            data = json.loads(line[5:])
            print(data)
```

## 📚 Documentation

- **Complete API Documentation:** [CONVERSATION_API_DOCS.md](./CONVERSATION_API_DOCS.md)
- **Firebase Database Structure:** [Firebase Database Structure.md](./Firebase%20Database%20Structure.md)
- **Environment Variables Template:** [.env.example](./.env.example)

## 🔒 Security

### Authentication Flow
1. Admin logs in via `/login` endpoint
2. Receives JWT token with admin_id
3. Token must be included in Authorization header
4. Token is validated and checked against blacklist
5. Admin's access to conversation is verified

### Authorization Rules
Admin can access a conversation if:
- The call is taken over by them (admin_id matches), OR
- The call is unassigned AND the worker belongs to their company

### Token Management
- Tokens are validated on every request
- Blacklisted tokens are rejected
- Expired tokens automatically fail
- Logout adds token to blacklist

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└─────┬───────┘
      │ SSE Connection
      ↓
┌─────────────────┐
│   FastAPI App   │
│  main.py        │
└─────┬───────────┘
      │
      ├──→ Authentication (JWT)
      │
      ├──→ Firestore (admins, workers)
      │
      └──→ Firebase Realtime DB
          (active_calls, active_conversations)
          
Poll every 1 second for new messages
Send SSE events when changes detected
```

## 🎨 Features Breakdown

### Real-time Monitoring
- Poll Firebase every 1 second for changes
- Detect new messages immediately
- Send only new messages (not entire conversation)
- Automatic message counting

### Connection Management
- Heartbeat every 30 seconds
- Graceful disconnection
- Error handling and recovery
- Stream cleanup on conversation end

### Performance
- Efficient polling (1-second interval)
- Only sends delta (new messages)
- Minimal bandwidth usage
- Scalable architecture

## 📊 Usage Statistics

Based on typical usage:
- **Initial Load:** ~2-5 KB (depending on message count)
- **Per Message:** ~500 bytes - 2 KB
- **Heartbeat:** ~50 bytes every 30s
- **Connection Overhead:** Minimal (<100 bytes/second)

## 🐛 Troubleshooting

### Connection Issues

**Problem:** Stream immediately disconnects
- **Cause:** Invalid/expired token
- **Solution:** Get fresh token via `/login`

**Problem:** 403 Forbidden error
- **Cause:** No access to conversation
- **Solution:** Verify worker belongs to your company

**Problem:** No new messages received
- **Cause:** Conversation inactive or ended
- **Solution:** Check conversation status in Firebase

### Performance Issues

**Problem:** High server load
- **Solution:** Increase polling interval from 1s to 2-3s
- **Solution:** Implement connection pooling

**Problem:** Browser crashes with many connections
- **Solution:** Limit simultaneous streams to 3-5
- **Solution:** Close unused connections

## 🔄 Migration from JSON Files

The system now uses environment variables instead of `serviceAccountKey.json`:

**Before:**
```python
cred = credentials.Certificate("serviceAccountKey.json")
```

**After:**
```python
firebase_credentials = {
    "type": os.getenv('FIREBASE_TYPE'),
    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
    # ... other credentials from .env
}
cred = credentials.Certificate(firebase_credentials)
```

### Migration Steps:
1. Copy values from `serviceAccountKey.json` to `.env`
2. Update the code to use environment variables (already done)
3. Test the application
4. Delete or backup `serviceAccountKey.json`
5. Add `.env` to `.gitignore`

## 🚀 Future Enhancements

- [ ] WebSocket support for bi-directional communication
- [ ] Message acknowledgment tracking
- [ ] Typing indicators
- [ ] Rich media support (images, audio, location)
- [ ] Message search and filtering
- [ ] Export conversations (PDF/JSON)
- [ ] Admin-to-user direct messaging
- [ ] Multi-language support
- [ ] Push notifications

## 📝 Changelog

### Version 3.0.0 (Current)
- ✅ Added live conversation streaming via SSE
- ✅ Added conversation snapshot endpoint
- ✅ Migrated Firebase credentials to environment variables
- ✅ Enhanced authentication and authorization
- ✅ Added comprehensive documentation
- ✅ Added test client and web interface

## 📞 Support

For issues or questions:
1. Check the [CONVERSATION_API_DOCS.md](./CONVERSATION_API_DOCS.md)
2. Review error messages in browser console/terminal
3. Verify Firebase and Redis connections
4. Check token validity and permissions

## 📄 License

[Your License Here]

---

**Built with ❤️ for Aurora Emergency Assistant**
