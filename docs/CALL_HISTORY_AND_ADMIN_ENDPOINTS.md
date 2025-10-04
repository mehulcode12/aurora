# Call History & Admin Profile Endpoints

## Overview
This document describes the REST API endpoints for accessing call history, conversation archives, and managing admin profiles in the Aurora Emergency Assistant system. All endpoints require admin authentication via JWT token.

---

## Call History Endpoints

### 1. Get All Calls History
**GET** `/api/calls/history`

Retrieve all completed/archived calls for workers under the authenticated admin's management.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "success": true,
  "calls": [
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
      "admin_notes": "Medical emergency handled"
    },
    {
      "call_id": "call_919876543210_20251005_120015",
      "worker_id": "worker_919876543210",
      "mobile_no": "+91 9876543210",
      "conversation_id": "conv_919876543210_20251005_120015",
      "urgency": "NORMAL",
      "status": "COMPLETE",
      "timestamp": "2025-10-05T12:00:15Z",
      "medium": "Voice",
      "final_action": null,
      "admin_id": null,
      "resolved_at": "2025-10-05T12:05:42Z",
      "duration_seconds": 327,
      "admin_notes": ""
    }
  ],
  "total_calls": 2
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **500 Internal Server Error**: Server error

#### Notes
- Returns calls sorted by timestamp (most recent first)
- Only returns calls from workers belonging to this admin
- Handles batch queries efficiently (Firestore 'in' query limitation)

---

### 2. Get Conversation for Specific Call
**GET** `/api/calls/{call_id}/conversation`

Retrieve the complete archived conversation for a specific call from Firestore.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Path Parameters
- `call_id` (string): The call's ID (e.g., `call_919325590143_20251005_143022`)

#### Response (200 OK)
```json
{
  "success": true,
  "conversation": {
    "conversation_id": "conv_919325590143_20251005_143022",
    "call_id": "call_919325590143_20251005_143022",
    "messages": [
      {
        "role": "user",
        "content": "I need help, there's a fire in the factory!",
        "sources": "",
        "timestamp": "2025-10-05T14:30:25Z"
      },
      {
        "role": "assistant",
        "content": "Evacuate immediately. Use the nearest exit. Do not use elevators. Call emergency services at 911.",
        "sources": "Emergency Procedures Manual - Fire Safety Protocol",
        "timestamp": "2025-10-05T14:30:28Z"
      },
      {
        "role": "user",
        "content": "I'm out of the building now, what should I do?",
        "sources": "",
        "timestamp": "2025-10-05T14:31:15Z"
      },
      {
        "role": "assistant",
        "content": "Good. Move to the assembly point. Stay there until emergency services arrive. Do not re-enter the building.",
        "sources": "Emergency Procedures Manual - Evacuation Protocol",
        "timestamp": "2025-10-05T14:31:18Z"
      }
    ],
    "archived_at": "2025-10-05T14:45:30Z",
    "total_messages": 4
  }
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Call doesn't belong to admin's workers
- **404 Not Found**: Call or conversation not found
- **500 Internal Server Error**: Server error

#### Notes
- Verifies that the call belongs to a worker under this admin
- Returns complete conversation with all messages
- Includes timestamps and sources for each message

---

## Admin Profile Endpoints

### 3. Get Admin Profile
**GET** `/api/admin/profile`

Retrieve the authenticated admin's profile information.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "admin_id": "admin123",
  "email": "john.doe@company.com",
  "name": "John Doe",
  "company_name": "Acme Manufacturing Inc.",
  "designation": "Safety Manager"
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **404 Not Found**: Admin profile not found
- **500 Internal Server Error**: Server error

---

### 4. Update Admin Profile
**PUT** `/api/admin/profile`

Update the admin's profile information. Only name and designation can be updated.

#### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Request Body (all fields optional)
```json
{
  "name": "John Updated Doe",
  "designation": "Senior Safety Manager"
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "message": "Admin profile updated successfully",
  "admin": {
    "admin_id": "admin123",
    "email": "john.doe@company.com",
    "name": "John Updated Doe",
    "company_name": "Acme Manufacturing Inc.",
    "designation": "Senior Safety Manager"
  }
}
```

#### Error Responses
- **400 Bad Request**: No fields to update
- **401 Unauthorized**: Missing or invalid token
- **404 Not Found**: Admin profile not found
- **500 Internal Server Error**: Server error

#### Notes
- Email and company_name are read-only and cannot be changed
- At least one field (name or designation) must be provided
- Returns updated admin profile

---

## Authentication

All endpoints require a valid JWT access token obtained from the `/login` endpoint.

### Getting Access Token
1. Login via `/login` endpoint
2. Extract `access_token` from response
3. Include in Authorization header: `Bearer <access_token>`

### Token Format
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Usage Examples

### Example 1: Get Call History

```bash
curl -X GET https://your-api.com/api/calls/history \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**JavaScript/Fetch:**
```javascript
const response = await fetch('https://your-api.com/api/calls/history', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
  }
});
const data = await response.json();
console.log(`Total calls: ${data.total_calls}`);
```

---

### Example 2: Get Conversation for Call

```bash
curl -X GET https://your-api.com/api/calls/call_919325590143_20251005_143022/conversation \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**JavaScript/Fetch:**
```javascript
const callId = 'call_919325590143_20251005_143022';
const response = await fetch(`https://your-api.com/api/calls/${callId}/conversation`, {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
  }
});
const data = await response.json();
console.log(`Messages: ${data.conversation.total_messages}`);
```

---

### Example 3: Get Admin Profile

```bash
curl -X GET https://your-api.com/api/admin/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**JavaScript/Fetch:**
```javascript
const response = await fetch('https://your-api.com/api/admin/profile', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
  }
});
const profile = await response.json();
console.log(`Admin: ${profile.name} - ${profile.designation}`);
```

---

### Example 4: Update Admin Profile

```bash
curl -X PUT https://your-api.com/api/admin/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Updated",
    "designation": "Senior Safety Manager"
  }'
```

**JavaScript/Fetch:**
```javascript
const response = await fetch('https://your-api.com/api/admin/profile', {
  method: 'PUT',
  headers: {
    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'John Updated',
    designation: 'Senior Safety Manager'
  })
});
const result = await response.json();
console.log(result.message);
```

---

## Data Models

### CallHistory
```typescript
{
  call_id: string;              // Unique call identifier
  worker_id: string;            // Worker who made the call
  mobile_no: string;            // Worker's phone number
  conversation_id: string;      // Associated conversation ID
  urgency: "CRITICAL" | "URGENT" | "NORMAL";
  status: "COMPLETE" | "TAKEOVER";
  timestamp: string;            // ISO 8601 format
  medium: "Text" | "Voice";
  final_action?: string | null; // "Police" | "Ambulance" | "Fire" | null
  admin_id?: string | null;     // If admin took over
  resolved_at: string;          // ISO 8601 format
  duration_seconds?: number | null;
  admin_notes?: string;         // Optional admin notes
}
```

### ConversationHistory
```typescript
{
  conversation_id: string;
  call_id: string;
  messages: [
    {
      role: "user" | "assistant";
      content: string;
      sources?: string;
      timestamp: string;        // ISO 8601 format
    }
  ];
  archived_at: string;         // ISO 8601 format
  total_messages: number;
}
```

### AdminProfile
```typescript
{
  admin_id: string;
  email: string;               // Read-only
  name: string;                // Updatable
  company_name: string;        // Read-only
  designation: string;         // Updatable
}
```

---

## Integration with Firebase

### Firestore Collections Used

#### calls/
```
calls/
  {call_id}/
    worker_id: string
    mobile_no: string
    conversation_id: string
    urgency: string
    status: string
    timestamp: timestamp
    medium: string
    final_action: string | null
    admin_id: string | null
    resolved_at: timestamp
    duration_seconds: number | null
    admin_notes: string
```

#### conversations/
```
conversations/
  {conversation_id}/
    call_id: string
    messages: array
    archived_at: timestamp
    total_messages: number
```

#### admins/
```
admins/
  {admin_id}/
    email: string
    name: string
    company_name: string
    designation: string
    sop_manuals_id: string
    created_at: timestamp
    last_login: timestamp
```

---

## Security Considerations

1. **Authentication Required**: All endpoints require valid JWT tokens
2. **Admin Authorization**: Calls are filtered by admin's workers
3. **Worker Verification**: Cross-admin access is prevented
4. **Read-Only Fields**: Email and company_name cannot be changed
5. **Token Blacklisting**: Revoked tokens are checked against Redis

---

## Business Logic

### Call History Filtering
- Only returns calls from workers under the admin's management
- Batches Firestore queries to handle 'in' query limitations (max 10 items)
- Sorts results by timestamp (most recent first)

### Conversation Access Control
- Verifies call exists in Firestore
- Checks worker belongs to requesting admin
- Returns complete conversation with all messages

### Profile Updates
- Only name and designation can be modified
- Email is tied to authentication and cannot change
- Company name is organizational data and cannot change
- Returns updated profile after successful modification

---

## Error Handling

### Common Error Scenarios

#### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```
**Solution**: Re-authenticate via `/login` endpoint

#### 403 Forbidden
```json
{
  "detail": "You don't have permission to access this call"
}
```
**Solution**: You can only access calls from your own workers

#### 404 Not Found
```json
{
  "detail": "Call with ID {call_id} not found"
}
```
**Solution**: Verify the call_id is correct and the call exists

#### 400 Bad Request
```json
{
  "detail": "No fields to update"
}
```
**Solution**: Provide at least one field to update

---

## Testing

You can test these endpoints using:
- **Swagger UI**: Visit `/docs` on your API server
- **ReDoc**: Visit `/redoc` on your API server
- **Postman**: Import the OpenAPI spec from `/openapi.json`
- **curl**: Use command-line examples above

---

## Performance Considerations

1. **Batch Queries**: Call history endpoint handles large numbers of workers efficiently
2. **Sorting**: Results are sorted in-memory after retrieval
3. **Timestamps**: All timestamps converted to ISO 8601 format
4. **Message Arrays**: Conversations stored as arrays in Firestore for efficient retrieval

---

## Best Practices

1. **Cache Profiles**: Cache admin profile data on the frontend to reduce API calls
2. **Paginate History**: For large call volumes, consider implementing pagination
3. **Filter Locally**: Use client-side filtering for urgency levels, date ranges, etc.
4. **Conversation Display**: Display messages chronologically with clear role indicators
5. **Update Sparingly**: Only update profile when actually changing values

---

## Support

For issues or questions about these endpoints, refer to:
- Main documentation: `README.md`
- Firebase structure: `Firebase Database Structure.md`
- API documentation: `/docs` endpoint
- Worker endpoints: `WORKER_ENDPOINTS.md`
