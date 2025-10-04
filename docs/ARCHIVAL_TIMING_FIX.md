# Call Archival Timing Fix

## Issue Reported
**Problem**: Instead of archiving chats on hanging up call, it was archiving chats to Firestore on every new message added.

**Date Fixed**: October 5, 2025

---

## Root Cause Analysis

### The Problem
In `/process-speech` endpoint (lines 1316-1325), there was archival code that executed **on EVERY message exchange**:

```python
# Archive the call immediately since we're hanging up
if call_id:
    print(f"📦 Call ending naturally, archiving {call_id}")
    # Schedule archival after a short delay to allow Twilio to complete
    import threading
    def delayed_archive():
        import time
        time.sleep(2)  # Wait 2 seconds for call to complete
        active_calls_manager.end_call(call_id)
    threading.Thread(target=delayed_archive, daemon=True).start()
```

### Why This Was Wrong

The `/process-speech` endpoint flow is:
1. User speaks → Aurora responds
2. `response.say()` - Aurora's voice response
3. `gather = Gather(...)` - **Continue listening for more input**
4. `response.append(gather)` - Add gather to response
5. `response.say("If you need more help...")` - Fallback message
6. `response.hangup()` - Fallback action **IF timeout occurs**
7. **ARCHIVAL CODE** ← This runs EVERY time, even when call continues!

The key misunderstanding: **`response.hangup()` is just a FALLBACK instruction**. It doesn't mean the call is ending. The `Gather` keeps the call active and loops back to `/process-speech` for the next message.

**Result**: Every single message → Archive → Delete from Firebase → Create new call → Archive again → Loop

---

## The Fix

### What Changed
**Removed archival code from `/process-speech` entirely.**

### Where Archival Now Happens

Archival is triggered **ONLY when the call actually ends** via:

1. **`/call-status` webhook** (PRIMARY METHOD):
   - Twilio calls this when call status changes to: `completed`, `failed`, `busy`, `no-answer`
   - User MUST configure this in Twilio Console
   - Location: Phone Numbers → Voice Configuration → "Call status changes" webhook

2. **`/hangup` endpoint** (EXPLICIT HANGUP):
   - Triggered when user explicitly hangs up
   - Finds call by phone number and archives it

3. **MAX_CONVERSATION_LENGTH reached**:
   - When conversation exceeds 20 exchanges
   - Aurora says goodbye and hangs up
   - This does NOT archive (relies on /call-status webhook)

### Updated Code

```python
# In /process-speech endpoint (line ~1311)
response.say(
    "If you need more help, please call back. Stay safe. Goodbye.",
    voice=config.TTS_VOICE, rate=config.SPEECH_RATE
)
response.hangup()

# Note: Archival happens via /call-status webhook when call actually ends
# Do NOT archive here - this runs on every message exchange!

return Response(content=str(response), media_type="application/xml")
```

---

## How It Works Now

### Message Exchange Flow (No Archival)
```
User speaks → /process-speech
    ↓
Aurora responds
    ↓
Gather added to response (continue listening)
    ↓
Response sent back to Twilio
    ↓
Call continues → User speaks again → Loop back to /process-speech
```

### Call End Flow (Archival Triggered)
```
User hangs up OR Call naturally ends OR Timeout
    ↓
Twilio detects call ended
    ↓
Twilio calls /call-status webhook with status="completed"
    ↓
Server finds call by phone number
    ↓
active_calls_manager.end_call(call_id)
    ↓
Archive to Firestore (calls/ + conversations/)
    ↓
Clean up from Firebase Realtime DB
    ↓
Clean up from local JSON
```

---

## Critical Configuration

### Twilio Webhook Setup (REQUIRED)
For archival to work, you MUST configure Twilio:

1. Go to: **Twilio Console** → **Phone Numbers** → **Active Numbers**
2. Select your Aurora number
3. Scroll to **Voice Configuration**
4. Find **"Call status changes"**
5. Change from **"None"** to **"Webhook"**
6. Enter URL: `https://your-domain.com/call-status`
7. Method: **POST**
8. **Save Configuration**

Without this configuration, calls will NEVER be archived automatically.

---

## Testing the Fix

### Test 1: Normal Conversation
1. Call Aurora
2. Have a 3-4 message conversation
3. Check Firebase Realtime DB → active_calls/ should show the call
4. Check Firestore → calls/ should be EMPTY (not archived yet)
5. Continue conversation → Firebase updates with new messages
6. No archival should happen during conversation

### Test 2: Natural Call End
1. Call Aurora
2. Say something
3. Wait for Aurora's response
4. Wait for timeout (10 seconds of silence)
5. Call ends naturally
6. Twilio sends /call-status with status="completed"
7. Check Firestore → Call should be archived
8. Check Firebase Realtime DB → Call should be removed

### Test 3: User Hangup
1. Call Aurora
2. Have a brief conversation
3. Hang up manually
4. /hangup endpoint receives notification
5. Call is archived immediately
6. Check Firestore and Firebase Realtime DB

### Expected Logs
```
🎤 SPEECH RECEIVED
   Call: CAxxxx
   Worker: Hello Aurora
   Confidence: 0.95
   🤖 Aurora: Hello! How can I help you?
   📊 Urgency Level: normal
   📚 Sources: []
   ✅ Added/updated conversation entry

🎤 SPEECH RECEIVED
   Call: CAxxxx
   Worker: I need help with equipment
   Confidence: 0.92
   🤖 Aurora: What equipment do you need help with?
   
📊 CALL STATUS UPDATE
   Call SID: CAxxxx
   Status: completed
   From: +1234567890
   📦 Archiving call call_1234567890_20251005_143022 to Firestore...
   ✅ Call archived to Firestore calls/ collection
   💬 Conversation archived to Firestore conversations/ collection
```

---

## Summary

### Before Fix
- ❌ Archival triggered on EVERY message
- ❌ Calls archived 5-10 times during conversation
- ❌ Firebase Realtime DB constantly updated/deleted
- ❌ Conversations fragmented across multiple Firestore documents
- ❌ Unnecessary load on Firebase

### After Fix
- ✅ Archival triggered ONLY when call ends
- ✅ One archive per call
- ✅ Clean conversation history
- ✅ Efficient Firebase usage
- ✅ Proper call lifecycle management

### Key Principle
**Never archive in the conversation loop - only archive when the call lifecycle completes.**

---

## Files Modified
- `main.py` (lines 1316-1325): Removed archival code from `/process-speech`

## Dependencies
- Twilio "Call status changes" webhook configuration (USER ACTION REQUIRED)
- `/call-status` endpoint (already implemented)
- `/hangup` endpoint (already implemented)

## Related Documentation
- `CALL_ARCHIVAL_FIX.md` - Previous archival bug fix
- `CALL_ARCHIVAL_IMPLEMENTATION.md` - Complete archival implementation
- `Firebase Database Structure.md` - Schema reference
