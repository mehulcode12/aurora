# 🔧 Call Archival Fix - Complete Guide

## 🐛 Issue Identified

**Problem:** Chats were NOT being archived when calls ended. New calls were adding messages to old conversations.

**Root Causes:**
1. ❌ Twilio "Call status changes" webhook was set to "None"
2. ❌ Local JSON was reusing old call_ids even after archival
3. ❌ No verification that call exists in Firebase RT DB
4. ❌ Archived calls were staying in local JSON

---

## ✅ Fixes Applied

### Fix 1: Check Firebase RT DB Before Reusing Call

**Problem:** When creating a new call, the system checked local JSON for active calls but didn't verify if the call still existed in Firebase Realtime Database.

**Solution:**
```python
# Before reusing existing call_id, verify it exists in Firebase
if existing_call_id:
    fb_call = db.reference(f'active_calls/{existing_call_id}').get()
    if not fb_call:
        # Call was archived, create new one
        existing_call_id = None
```

**Result:** ✅ System creates NEW call if old one was archived

---

### Fix 2: Archive Call When Hanging Up Naturally

**Problem:** When conversation ended with `response.hangup()`, the call wasn't being archived.

**Solution:**
```python
response.hangup()

# Archive immediately with 2-second delay
if call_id:
    def delayed_archive():
        time.sleep(2)  # Wait for Twilio to complete
        active_calls_manager.end_call(call_id)
    threading.Thread(target=delayed_archive, daemon=True).start()
```

**Result:** ✅ Calls archived when LLM says goodbye and hangs up

---

### Fix 3: Clean Up Local JSON After Archival

**Problem:** Archived calls were staying in local JSON with status="ENDED", causing clutter and potential conflicts.

**Solution:**
```python
# After archiving to Firestore, remove from local JSON
local_data = self._load_data()
if call_id in local_data["active_calls"]:
    del local_data["active_calls"][call_id]
if conv_id in local_data["active_conversations"]:
    del local_data["active_conversations"][conv_id]
self._save_data(local_data)
```

**Result:** ✅ Local JSON stays clean, only active calls remain

---

## ⚙️ Twilio Configuration Required

### CRITICAL: Update Your Twilio Settings

**Current Configuration (WRONG):**
```
Call status changes: None ❌
```

**Required Configuration (CORRECT):**
```
Call status changes: Webhook ✅
URL: https://nonpedagogical-preparatorily-evon.ngrok-free.dev/call-status
HTTP: HTTP POST
```

### How to Update:

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Phone Numbers** → **Manage** → **Active numbers**
3. Click on your Aurora phone number
4. Scroll to **Voice Configuration** section
5. Find **Call status changes** section
6. Change from "None" to **Webhook**
7. Enter URL: `https://YOUR-NGROK-URL.ngrok-free.dev/call-status`
8. Select **HTTP POST**
9. Click **Save**

**Why This Matters:**
- Without this, Twilio never notifies your server when calls end
- The `/call-status` endpoint won't be triggered
- Calls won't be archived automatically
- Messages will accumulate in old conversations

---

## 🔄 Complete Call Flow After Fixes

### Scenario 1: Call Ends Naturally (LLM Hangs Up)

```
User speaks
    ↓
Aurora responds with goodbye message
    ↓
response.hangup() called
    ↓
Delayed archival thread spawned (2-second delay)
    ↓
Wait 2 seconds for Twilio to complete
    ↓
Archive to Firestore ✅
Remove from Firebase RT DB ✅
Remove from local JSON ✅
    ↓
Call fully archived!
```

---

### Scenario 2: User Hangs Up (Primary Handler Fails)

```
User hangs up
    ↓
Twilio triggers /hangup endpoint
    ↓
Find call_id by phone number
    ↓
Archive to Firestore ✅
Remove from Firebase RT DB ✅
Remove from local JSON ✅
    ↓
Call fully archived!
```

---

### Scenario 3: Call Completed (Twilio Status Update)

```
Call completes
    ↓
Twilio triggers /call-status endpoint
    ↓
Find call_id by phone number
    ↓
Archive to Firestore ✅
Remove from Firebase RT DB ✅
Remove from local JSON ✅
    ↓
Call fully archived!
```

---

### Scenario 4: New Call After Previous Archived

```
New call arrives from same phone number
    ↓
Check local JSON for active call
    ↓
Found old call_id with status="ENDED"? ❌ Not anymore!
(Now deleted from local JSON)
    ↓
Check Firebase RT DB for active call
    ↓
Not found (was archived) ✅
    ↓
Create NEW call_id
    ↓
Fresh conversation starts ✅
```

---

## 🧪 Testing Steps

### Test 1: Verify Twilio Configuration

```bash
# Check Twilio Console
1. Go to your phone number settings
2. Verify "Call status changes" is set to Webhook
3. Verify URL matches your ngrok URL
```

### Test 2: Test Natural Hangup

```bash
# 1. Make a call
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Hello Aurora", "ph_no": "+1234567890"}'

# 2. Let the conversation end naturally (LLM hangs up)
# Aurora will say "Stay safe. Goodbye." and hang up

# 3. Wait 3 seconds

# 4. Check logs - should see:
"📦 Call ending naturally, archiving call_xxx"
"✅ Call archived to Firestore and removed from active calls"

# 5. Check Firebase RT DB
# active_calls/{call_id} should be REMOVED ✅
# active_conversations/{conv_id} should be REMOVED ✅

# 6. Check Firestore
# calls/{call_id} should exist ✅
# conversations/{conv_id} should exist ✅

# 7. Check local JSON
cat active_calls/total.json
# Call should be REMOVED (not just marked ENDED) ✅
```

### Test 3: Test New Call After Archive

```bash
# 1. Make first call
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Hello", "ph_no": "+1234567890"}'

# Note the call_id from logs (e.g., call_1234567890_20251005_100000)

# 2. End the call
curl -X POST http://localhost:5000/api/call/{call_id}/end

# 3. Wait 2 seconds for archival

# 4. Make second call from SAME phone number
curl -X POST http://localhost:5000/api/process-speech \
  -H "Content-Type: application/json" \
  -d '{"speech": "Hello again", "ph_no": "+1234567890"}'

# 5. Check logs - should see NEW call_id:
"📝 Conversation updated locally for +1234567890: call_1234567890_20251005_100030"
# ^^^^^ Different timestamp = NEW call ✅

# 6. Verify in Firebase RT DB
# Should have NEW call_id
# Should have NEW conversation_id
# Should NOT have old messages ✅
```

### Test 4: Test User Hangup

```bash
# 1. Make a real phone call to your Twilio number
# 2. Speak to Aurora
# 3. Hang up manually (press End Call)

# 4. Check logs - should see:
"/hangup endpoint triggered"
"📦 Archiving call {call_id} after explicit hangup"
"✅ Call archived to Firestore and removed from active calls"

# 5. Verify archival as in Test 2
```

---

## 📊 Before vs After Comparison

### Before Fixes ❌

```
Call 1:
Phone: +1234567890
Messages: ["Hello", "Hi there"]
Status: Call ends → NOT archived ❌

Call 2 (Same phone):
Phone: +1234567890
Messages: ["Hello", "Hi there", "Help!", "I'm here"] ← WRONG!
Status: Old messages mixed with new ❌

Firebase RT DB:
active_calls/call_xxx → Still exists ❌
active_conversations/conv_xxx → Still exists ❌

Firestore:
calls/ → Empty ❌
conversations/ → Empty ❌

Local JSON:
{
  "active_calls": {
    "call_xxx": {
      "status": "ENDED" ← Stays forever ❌
    }
  }
}
```

### After Fixes ✅

```
Call 1:
Phone: +1234567890
Messages: ["Hello", "Hi there"]
Status: Call ends → Archived immediately ✅

Call 2 (Same phone):
Phone: +1234567890
Call ID: NEW call_xxx_new ✅
Messages: ["Help!", "I'm here"] ← Fresh conversation ✅

Firebase RT DB:
active_calls/ → Empty (old call removed) ✅
active_conversations/ → Empty (old conv removed) ✅

Firestore:
calls/call_xxx → Archived ✅
conversations/conv_xxx → Archived ✅

Local JSON:
{
  "active_calls": {} ← Clean, only active calls ✅
  "active_conversations": {} ← Clean ✅
}
```

---

## 🎯 Verification Checklist

After implementing fixes:

- [ ] **Twilio Configuration Updated**
  - [ ] Call status changes set to Webhook
  - [ ] URL points to /call-status
  - [ ] HTTP POST selected

- [ ] **Code Changes Applied**
  - [ ] Firebase RT DB check before reusing call_id
  - [ ] Delayed archival on natural hangup
  - [ ] Local JSON cleanup after archival

- [ ] **Testing Complete**
  - [ ] Natural hangup archives call
  - [ ] User hangup archives call
  - [ ] New calls create fresh conversations
  - [ ] Old calls removed from Firebase RT DB
  - [ ] Old calls archived in Firestore
  - [ ] Local JSON stays clean

- [ ] **Logs Show Expected Messages**
  - [ ] "📦 Call ending naturally, archiving..."
  - [ ] "✅ Call archived to Firestore..."
  - [ ] "⚠️ Call was archived, creating new call" (on reuse)

---

## 🐛 Troubleshooting

### Issue: Calls still not archiving

**Check:**
1. Is Twilio "Call status changes" set correctly?
2. Is your ngrok URL up to date?
3. Are there errors in logs?

**Solution:**
```bash
# Check Twilio webhook is being called
tail -f logs.txt | grep "CALL STATUS UPDATE"

# If you don't see this when calls end, Twilio isn't calling the endpoint
# → Update Twilio configuration
```

---

### Issue: Old messages appearing in new calls

**Check:**
```bash
# Check if call exists in Firebase RT DB
curl "https://YOUR_PROJECT.firebaseio.com/active_calls/call_xxx.json"

# If it returns data, archival didn't complete
```

**Solution:**
```bash
# Manually end the call
curl -X POST http://localhost:5000/api/call/{call_id}/end

# Then make new call
```

---

### Issue: Local JSON keeps growing

**Check:**
```bash
cat active_calls/total.json | jq '.active_calls | length'
# If this number keeps growing, archival isn't cleaning up
```

**Solution:**
```bash
# Verify the cleanup code is executing
# Check logs for: "✅ Call archived to Firestore and removed from active calls"
```

---

## 📝 Summary of Changes

### Files Modified:
- `main.py`

### Methods Modified:

1. **`add_conversation_entry()`**
   - Added Firebase RT DB verification before reusing call_id
   - Creates new call if old one was archived

2. **`end_call()` → `archive_and_cleanup()`**
   - Added local JSON cleanup after archival
   - Removes archived calls from local storage

3. **`process_speech()` endpoint**
   - Added delayed archival when hanging up naturally
   - 2-second delay ensures Twilio completes

### New Behavior:

✅ **Archival triggers:**
- Natural hangup (LLM says goodbye)
- User hangup (/hangup endpoint)
- Call status update (/call-status endpoint)

✅ **Cleanup happens:**
- Firebase RT DB: active_calls/ deleted
- Firebase RT DB: active_conversations/ deleted
- Local JSON: call removed completely
- Firestore: call & conversation archived

✅ **New calls:**
- Always create fresh call_id
- Never reuse archived conversations
- Clean message history

---

## 🚀 Next Steps

1. **Update Twilio Configuration** (CRITICAL!)
   - Set "Call status changes" to Webhook
   - URL: `https://YOUR-NGROK-URL/call-status`

2. **Restart Server**
   ```bash
   # Stop current server (Ctrl+C)
   # Restart
   uvicorn main:app --reload --host 0.0.0.0 --port 5000
   ```

3. **Test All Scenarios**
   - Natural hangup
   - User hangup
   - New call after archival
   - Verify Firestore has archived calls

4. **Monitor Logs**
   ```bash
   tail -f logs.txt | grep -E "archiving|archived|CALL STATUS"
   ```

---

**Status:** ✅ **FIXED - Ready to Test**

**Critical Action Required:** Update Twilio "Call status changes" webhook configuration!
