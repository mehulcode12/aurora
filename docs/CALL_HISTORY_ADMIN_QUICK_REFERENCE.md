# Call History & Admin Profile - Quick Reference

## Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/calls/history` | Get all completed calls | ✅ |
| GET | `/api/calls/{call_id}/conversation` | Get conversation for call | ✅ |
| GET | `/api/admin/profile` | Get admin profile | ✅ |
| PUT | `/api/admin/profile` | Update admin profile | ✅ |

---

## Quick Examples

### Get Call History
```bash
GET /api/calls/history
Headers: { "Authorization": "Bearer TOKEN" }

Response:
{
  "success": true,
  "calls": [...],
  "total_calls": 15
}
```

### Get Conversation
```bash
GET /api/calls/call_919325590143_20251005_143022/conversation
Headers: { "Authorization": "Bearer TOKEN" }

Response:
{
  "success": true,
  "conversation": {
    "conversation_id": "conv_919325590143_20251005_143022",
    "call_id": "call_919325590143_20251005_143022",
    "messages": [
      {
        "role": "user",
        "content": "I need help!",
        "timestamp": "2025-10-05T14:30:25Z"
      },
      {
        "role": "assistant",
        "content": "I'm here to help...",
        "sources": "Emergency Manual",
        "timestamp": "2025-10-05T14:30:28Z"
      }
    ],
    "total_messages": 2
  }
}
```

### Get Admin Profile
```bash
GET /api/admin/profile
Headers: { "Authorization": "Bearer TOKEN" }

Response:
{
  "admin_id": "admin123",
  "email": "john@company.com",
  "name": "John Doe",
  "company_name": "Acme Inc.",
  "designation": "Safety Manager"
}
```

### Update Admin Profile
```bash
PUT /api/admin/profile
Headers: { "Authorization": "Bearer TOKEN" }
Body:
{
  "name": "John Updated",
  "designation": "Senior Manager"
}

Response:
{
  "success": true,
  "message": "Admin profile updated successfully",
  "admin": { ... }
}
```

---

## Data Structures

### Call History Item
```json
{
  "call_id": "call_919325590143_20251005_143022",
  "worker_id": "worker_919325590143",
  "mobile_no": "+91 9325590143",
  "conversation_id": "conv_919325590143_20251005_143022",
  "urgency": "CRITICAL",
  "status": "COMPLETE",
  "timestamp": "2025-10-05T14:30:22Z",
  "medium": "Voice",
  "final_action": "Ambulance",
  "admin_id": "admin123",
  "resolved_at": "2025-10-05T14:45:30Z",
  "duration_seconds": 908,
  "admin_notes": "Medical emergency"
}
```

### Conversation Message
```json
{
  "role": "user" | "assistant",
  "content": "Message text",
  "sources": "Source reference",
  "timestamp": "2025-10-05T14:30:25Z"
}
```

---

## Field Descriptions

### Call Fields
- **call_id**: Unique identifier for the call
- **worker_id**: ID of worker who made the call
- **mobile_no**: Worker's phone number
- **conversation_id**: Associated conversation ID
- **urgency**: `CRITICAL`, `URGENT`, or `NORMAL`
- **status**: `COMPLETE` or `TAKEOVER`
- **timestamp**: When call started (ISO 8601)
- **medium**: `Voice` or `Text`
- **final_action**: `Police`, `Ambulance`, `Fire`, or `null`
- **admin_id**: Admin who took over (if applicable)
- **resolved_at**: When call ended (ISO 8601)
- **duration_seconds**: Call duration in seconds
- **admin_notes**: Optional notes from admin

### Admin Profile Fields
- **admin_id**: Unique admin identifier (read-only)
- **email**: Admin email (read-only)
- **name**: Admin full name (updatable)
- **company_name**: Company name (read-only)
- **designation**: Job title (updatable)

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (no fields to update) |
| 401 | Unauthorized (invalid/missing token) |
| 403 | Forbidden (no access to this resource) |
| 404 | Not Found (resource doesn't exist) |
| 500 | Internal Server Error |

---

## Access Control

### Call History Access
- ✅ Returns calls from YOUR workers only
- ❌ Cannot access other admins' calls
- 🔍 Automatically filters by worker ownership

### Conversation Access
- ✅ Can view conversations for YOUR workers' calls
- ❌ Cannot view other admins' conversations
- 🔍 Verifies worker belongs to your company

### Profile Access
- ✅ Can view and update YOUR profile
- ❌ Cannot view or update other admins' profiles
- 🔒 Email and company_name are immutable

---

## Common Use Cases

### 1. Dashboard - Recent Calls
```javascript
// Fetch call history
const response = await fetch('/api/calls/history', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { calls } = await response.json();

// Display last 10 calls
const recent = calls.slice(0, 10);
```

### 2. Call Details Page
```javascript
// Fetch call with conversation
const callId = 'call_919325590143_20251005_143022';

// Get conversation
const response = await fetch(`/api/calls/${callId}/conversation`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { conversation } = await response.json();

// Display messages
conversation.messages.forEach(msg => {
  console.log(`${msg.role}: ${msg.content}`);
});
```

### 3. Profile Settings
```javascript
// Get current profile
const profile = await fetch('/api/admin/profile', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// Update profile
const updated = await fetch('/api/admin/profile', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'New Name',
    designation: 'New Title'
  })
}).then(r => r.json());
```

### 4. Analytics Dashboard
```javascript
// Get all calls
const { calls, total_calls } = await fetch('/api/calls/history', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// Calculate statistics
const critical = calls.filter(c => c.urgency === 'CRITICAL').length;
const avgDuration = calls.reduce((sum, c) => sum + (c.duration_seconds || 0), 0) / calls.length;
const todayCalls = calls.filter(c => isToday(c.timestamp)).length;

console.log(`Total: ${total_calls}, Critical: ${critical}, Avg Duration: ${avgDuration}s`);
```

---

## Filtering & Sorting Tips

### Client-Side Filtering
```javascript
// Filter by urgency
const criticalCalls = calls.filter(c => c.urgency === 'CRITICAL');

// Filter by date range
const lastWeek = calls.filter(c => {
  const callDate = new Date(c.timestamp);
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  return callDate > weekAgo;
});

// Filter by worker
const workerCalls = calls.filter(c => c.worker_id === 'worker_919325590143');
```

### Display Formatting
```javascript
// Format duration
const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
};

// Format urgency badge
const urgencyColor = {
  'CRITICAL': 'red',
  'URGENT': 'orange',
  'NORMAL': 'green'
};
```

---

## Best Practices

### 1. Caching
```javascript
// Cache profile data
const PROFILE_CACHE_KEY = 'admin_profile';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

function getCachedProfile() {
  const cached = localStorage.getItem(PROFILE_CACHE_KEY);
  if (cached) {
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp < CACHE_DURATION) {
      return data;
    }
  }
  return null;
}
```

### 2. Error Handling
```javascript
async function fetchCallHistory() {
  try {
    const response = await fetch('/api/calls/history', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if (response.status === 401) {
      // Token expired, redirect to login
      window.location.href = '/login';
      return;
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch call history:', error);
    showErrorToast('Failed to load call history');
  }
}
```

### 3. Loading States
```javascript
// Show loading indicator while fetching
setLoading(true);
try {
  const data = await fetchCallHistory();
  setCallHistory(data.calls);
} finally {
  setLoading(false);
}
```

---

## Troubleshooting

### Issue: Empty call history
**Check**: Do you have any workers registered?
**Solution**: Create workers first via `/api/workers`

### Issue: Cannot access conversation
**Check**: Does the call belong to your worker?
**Solution**: Verify call_id is correct and worker belongs to your company

### Issue: Profile update fails with "No fields to update"
**Check**: Are you sending at least one field?
**Solution**: Include `name` or `designation` in the request body

### Issue: 401 Unauthorized
**Check**: Is your token still valid?
**Solution**: Login again to get a fresh token

---

## Integration Checklist

- [ ] Implement authentication flow
- [ ] Fetch and display call history
- [ ] Display conversation details for selected call
- [ ] Show admin profile in settings
- [ ] Enable profile updates
- [ ] Add error handling for all endpoints
- [ ] Implement loading states
- [ ] Add client-side filtering/sorting
- [ ] Cache profile data
- [ ] Format timestamps for display
- [ ] Show urgency badges with colors
- [ ] Calculate and display analytics

---

## Testing Checklist

- [ ] Test call history retrieval
- [ ] Test conversation retrieval
- [ ] Test profile retrieval
- [ ] Test profile updates (name only)
- [ ] Test profile updates (designation only)
- [ ] Test profile updates (both fields)
- [ ] Test error handling (invalid token)
- [ ] Test error handling (invalid call_id)
- [ ] Test access control (other admin's calls)
- [ ] Test empty states (no calls)
