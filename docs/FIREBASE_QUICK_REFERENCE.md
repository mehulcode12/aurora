# Firebase Real-Time Updates - Developer Quick Reference

## 🎯 Key Principle

**NEVER block the conversation for Firebase updates!**

Local JSON → Instant (< 1ms)  
Firebase Sync → Background (100-500ms)  
**Result:** ZERO conversation delays ✅

---

## 📝 Code Examples

### 1. Adding a New Call (Correct Implementation ✅)

```python
def add_conversation_entry(self, phone_number, user_query, aurora_response, urgency_level):
    # Step 1: Update local JSON (FAST)
    data = self._load_data()
    
    # ... create call and conversation data ...
    
    # Save locally (< 1ms)
    self._save_data(data)
    
    # Step 2: Update Firebase asynchronously (NON-BLOCKING)
    self._update_firebase_async(call_id, conv_id, call_data, conv_data)
    
    # Return immediately - conversation continues!
    return call_id, conv_id
```

### 2. Asynchronous Firebase Update

```python
def _update_firebase_async(self, call_id, conv_id, call_data, conv_data):
    """Update Firebase without blocking"""
    import threading
    
    def firebase_update():
        try:
            # Update active_calls
            db.reference(f'active_calls/{call_id}').set(call_data)
            
            # Update active_conversations
            db.reference(f'active_conversations/{conv_id}').set(conv_data)
            
            print(f"🔥 Firebase updated: {call_id}")
        except Exception as e:
            # Log error but don't crash
            print(f"⚠️ Firebase error (non-critical): {e}")
    
    # Run in background thread
    threading.Thread(target=firebase_update, daemon=True).start()
```

### 3. Wrong Implementation ❌ (Don't Do This!)

```python
# ❌ WRONG - This blocks the conversation!
def add_conversation_entry_WRONG(self, phone_number, user_query, aurora_response):
    data = self._load_data()
    
    # ... create data ...
    
    # Save to local JSON
    self._save_data(data)
    
    # ❌ BLOCKING FIREBASE CALL - ADDS 200ms DELAY!
    db.reference(f'active_calls/{call_id}').set(call_data)
    db.reference(f'active_conversations/{conv_id}').set(conv_data)
    
    return call_id, conv_id
```

---

## 🔍 Firebase Database Structure

### Active Calls
```
active_calls/{call_id}
├── worker_id: "worker_1234567890"
├── mobile_no: "+1234567890"
├── conversation_id: "conv_xxx"
├── urgency: "CRITICAL" | "URGENT" | "NORMAL"
├── status: "ACTIVE" | "ENDED"
├── timestamp: "2025-10-04T14:30:00+05:30"
├── medium: "Voice" | "Text"
├── last_message_at: "2025-10-04T14:35:00+05:30"
└── admin_id: "admin_uuid" (optional)
```

### Active Conversations
```
active_conversations/{conversation_id}
├── call_id: "call_xxx"
└── messages/
    ├── msg_xxx_0001/
    │   ├── role: "user"
    │   ├── content: "message text"
    │   ├── timestamp: "2025-10-04T14:30:15+05:30"
    │   └── sources: ""
    └── msg_xxx_0002/
        ├── role: "assistant"
        ├── content: "response text"
        ├── timestamp: "2025-10-04T14:30:18+05:30"
        └── sources: "Emergency Manual"
```

---

## 🚀 Admin Dashboard - Server-Sent Events (SSE)

### Endpoint
```
GET /api/conversation/{conversation_id}/stream
Authorization: Bearer {access_token}
```

### Event Types

#### 1. Initial Event (Sent immediately)
```json
{
  "event": "initial",
  "data": {
    "conversation_id": "conv_xxx",
    "call_id": "call_xxx",
    "worker_id": "worker_xxx",
    "mobile_no": "+1234567890",
    "urgency": "CRITICAL",
    "status": "ACTIVE",
    "medium": "Voice",
    "timestamp": "2025-10-04T14:30:00+05:30",
    "messages": [
      {
        "message_id": "msg_xxx_0001",
        "role": "user",
        "content": "There's a fire!",
        "timestamp": "2025-10-04T14:30:15+05:30",
        "sources": ""
      }
    ],
    "total_messages": 1
  }
}
```

#### 2. New Messages Event (Real-time updates)
```json
{
  "event": "new_messages",
  "data": {
    "conversation_id": "conv_xxx",
    "messages": [
      {
        "message_id": "msg_xxx_0002",
        "role": "assistant",
        "content": "Evacuate immediately!",
        "timestamp": "2025-10-04T14:30:18+05:30",
        "sources": "Emergency Procedures Manual"
      }
    ],
    "total_messages": 2
  }
}
```

#### 3. Ended Event
```json
{
  "event": "ended",
  "data": {
    "message": "Call has ended",
    "conversation_id": "conv_xxx"
  }
}
```

#### 4. Heartbeat (Every 30 seconds)
```json
{
  "event": "heartbeat",
  "data": {
    "timestamp": "2025-10-04T14:31:00",
    "status": "connected"
  }
}
```

### Frontend Implementation (JavaScript)

```javascript
// Connect to SSE stream
const eventSource = new EventSource(
  `https://api.aurora.com/api/conversation/${conversationId}/stream`,
  {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  }
);

// Handle initial conversation data
eventSource.addEventListener('initial', (e) => {
  const data = JSON.parse(e.data);
  console.log('Initial conversation:', data);
  
  // Render initial messages
  renderMessages(data.messages);
  updateUrgency(data.urgency);
});

// Handle new messages in real-time
eventSource.addEventListener('new_messages', (e) => {
  const data = JSON.parse(e.data);
  console.log('New messages:', data.messages);
  
  // Append new messages to UI
  data.messages.forEach(msg => {
    appendMessage(msg);
  });
  
  // Update total count
  updateMessageCount(data.total_messages);
});

// Handle conversation end
eventSource.addEventListener('ended', (e) => {
  const data = JSON.parse(e.data);
  console.log('Conversation ended:', data.message);
  
  // Update UI to show ended state
  markConversationAsEnded();
  
  // Close SSE connection
  eventSource.close();
});

// Handle heartbeat (keep-alive)
eventSource.addEventListener('heartbeat', (e) => {
  console.log('Connection alive');
});

// Handle errors
eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
  
  // Reconnect logic
  setTimeout(() => {
    reconnect();
  }, 5000);
};
```

---

## ⚡ Performance Metrics

### Conversation Flow Timeline

| Time | Event | Location |
|------|-------|----------|
| 0ms | User speaks | Phone/Web |
| 50ms | LLM response generated | Cerebras |
| 51ms | Local JSON updated | Server |
| 52ms | Response sent to caller | ✅ ZERO DELAY |
| 100ms | Firebase update starts | Background thread |
| 300ms | Firebase update complete | Firebase |
| 1000ms | Admin receives update | Dashboard SSE |

### Key Metrics
- **Conversation latency:** < 1ms ✅
- **Firebase sync time:** 100-500ms
- **Admin update delay:** 1-2 seconds
- **Total caller impact:** ZERO ✅

---

## 🐛 Debugging Tips

### Check Local JSON Updates
```bash
# Watch total.json for changes
tail -f active_calls/total.json

# Or on Windows
Get-Content active_calls/total.json -Wait
```

### Check Firebase Updates
```bash
# View Firebase logs
# Look for "🔥 Firebase updated successfully" messages

# Check Firebase console
# Navigate to Realtime Database → active_calls
```

### Test Conversation Latency
```bash
# Send test message and measure response time
time curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Test message", "ph_no": "+1234567890"}'

# Should be < 100ms
```

### Monitor Background Threads
```python
# Add logging to Firebase update function
def firebase_update():
    start_time = time.time()
    try:
        db.reference(f'active_calls/{call_id}').set(call_data)
        elapsed = time.time() - start_time
        print(f"🔥 Firebase update took {elapsed*1000:.2f}ms")
    except Exception as e:
        print(f"⚠️ Firebase error: {e}")
```

---

## ✅ Best Practices Checklist

- [x] Local JSON is always updated first
- [x] Firebase updates use background threads
- [x] All threads use `daemon=True`
- [x] Firebase errors are logged, not raised
- [x] Conversations never wait for Firebase
- [x] SSE polling interval is 1 second
- [x] Heartbeat events every 30 seconds
- [x] Admin authentication verified for SSE
- [x] Proper error handling in SSE stream
- [x] Connection cleanup on stream end

---

## 🔐 Security Notes

### Firebase Security Rules
```json
{
  "rules": {
    "active_calls": {
      ".read": "auth != null",
      ".write": "auth != null"
    },
    "active_conversations": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

### SSE Authentication
```python
# Always verify token before streaming
async def stream_conversation(
    conversation_id: str,
    token_data: dict = Depends(verify_access_token_with_blacklist)
):
    admin_id = token_data["admin_id"]
    
    # Verify admin has access to this conversation
    # ... access control logic ...
```

---

## 🎓 Common Mistakes to Avoid

### ❌ Mistake 1: Blocking Firebase Calls
```python
# WRONG - Blocks conversation
db.reference(f'active_calls/{call_id}').set(data)
```

### ✅ Correct: Async Firebase Update
```python
# RIGHT - Non-blocking
self._update_firebase_async(call_id, conv_id, data)
```

---

### ❌ Mistake 2: Not Using Daemon Threads
```python
# WRONG - Thread prevents shutdown
threading.Thread(target=firebase_update).start()
```

### ✅ Correct: Daemon Thread
```python
# RIGHT - Clean shutdown
threading.Thread(target=firebase_update, daemon=True).start()
```

---

### ❌ Mistake 3: Raising Firebase Errors
```python
# WRONG - Crashes conversation
def firebase_update():
    db.reference(...).set(data)  # No error handling
```

### ✅ Correct: Error Handling
```python
# RIGHT - Conversation continues
def firebase_update():
    try:
        db.reference(...).set(data)
    except Exception as e:
        print(f"⚠️ Non-critical Firebase error: {e}")
```

---

## 📞 Support

### Check System Status
```bash
# Test Redis connection
curl http://localhost:5000/health/redis

# Test API
curl http://localhost:5000/status

# Test conversation flow
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Hello Aurora", "ph_no": "+1234567890"}'
```

### Common Issues

**Issue:** Firebase updates not appearing  
**Solution:** Check Firebase credentials and database URL

**Issue:** Slow conversation responses  
**Solution:** Verify Firebase calls are asynchronous (background threads)

**Issue:** SSE not receiving updates  
**Solution:** Check Firebase polling interval and connection status

---

## 🚀 Quick Start

1. **Environment Setup**
```bash
# Set Firebase credentials
export FIREBASE_DATABASE_URL="https://your-project.firebaseio.com"
export FIREBASE_PROJECT_ID="your-project-id"
# ... other Firebase env vars ...
```

2. **Start Server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

3. **Test Conversation**
```bash
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Test", "ph_no": "+1234567890"}'
```

4. **Monitor Logs**
```bash
# Look for these messages:
# ✅ "📝 Conversation updated locally"
# ✅ "🔥 Firebase updated successfully"
```

---

## 📚 Related Documentation

- [Firebase Realtime Implementation](./FIREBASE_REALTIME_IMPLEMENTATION.md) - Detailed explanation
- [Firebase Visual Flows](./FIREBASE_VISUAL_FLOWS.md) - Architecture diagrams
- [Firebase Database Structure](./Firebase%20Database%20Structure.md) - Schema reference

---

**Remember:** The conversation flow should NEVER be blocked by Firebase operations! 🚀
