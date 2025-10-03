# Conversation API Documentation

## Overview

The Conversation API provides real-time access to emergency call conversations for authenticated admins. It includes both snapshot and streaming endpoints to monitor active conversations.

---

## Endpoints

### 1. Get Conversation Snapshot

**Endpoint:** `GET /api/conversation/{conversation_id}`

**Description:** Retrieves a complete snapshot of a conversation with all messages at the time of the request.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `conversation_id` (string, required): The unique identifier of the conversation

**Response Model:** `GetConversationResponse`

**Response Example:**
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
    "messages": [
      {
        "message_id": "msg_919325590143_20251003_115804_0001",
        "role": "user",
        "content": "My friend is falling from a floor, what should I do?",
        "timestamp": "2025-10-03T11:58:04+05:30",
        "sources": ""
      },
      {
        "message_id": "msg_919325590143_20251003_115804_0002",
        "role": "assistant",
        "content": "Call for help now. Try to break their fall if safe. Clear the area.",
        "timestamp": "2025-10-03T11:58:04+05:30",
        "sources": "Emergency Procedures Manual, OSHA Safety Standards"
      }
    ],
    "total_messages": 2,
    "admin_id": null
  }
}
```

**Error Responses:**

- **401 Unauthorized**: Invalid or missing authentication token
- **403 Forbidden**: Admin doesn't have access to this conversation
- **404 Not Found**: Conversation or associated call not found
- **500 Internal Server Error**: Server error

**Access Control:**
- Admin can access conversations from:
  - Calls taken over by them (admin_id matches)
  - Unassigned calls from workers in their company

---

### 2. Stream Live Conversation

**Endpoint:** `GET /api/conversation/{conversation_id}/stream`

**Description:** Opens a Server-Sent Events (SSE) stream that provides real-time updates when new messages arrive in the conversation.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `conversation_id` (string, required): The unique identifier of the conversation

**Response:** Server-Sent Events (SSE) stream

**Event Types:**

#### 1. `initial` - Initial Conversation Data
Sent immediately upon connection with the complete conversation history.

```json
{
  "event": "initial",
  "data": {
    "conversation_id": "conv_919325590143_20251003_115804",
    "call_id": "call_919325590143_20251003_115804",
    "worker_id": "worker_919325590143",
    "mobile_no": "+919325590143",
    "urgency": "CRITICAL",
    "status": "ACTIVE",
    "medium": "Voice",
    "timestamp": "2025-10-03T11:58:04+05:30",
    "messages": [
      {
        "message_id": "msg_919325590143_20251003_115804_0001",
        "role": "user",
        "content": "My friend is falling from a floor, what should I do?",
        "timestamp": "2025-10-03T11:58:04+05:30",
        "sources": ""
      }
    ],
    "total_messages": 1
  }
}
```

#### 2. `new_messages` - New Messages Arrived
Sent whenever new messages are added to the conversation.

```json
{
  "event": "new_messages",
  "data": {
    "conversation_id": "conv_919325590143_20251003_115804",
    "messages": [
      {
        "message_id": "msg_919325590143_20251003_115804_0003",
        "role": "user",
        "content": "No, please be more clear.",
        "timestamp": "2025-10-03T11:58:18+05:30",
        "sources": ""
      },
      {
        "message_id": "msg_919325590143_20251003_115804_0004",
        "role": "assistant",
        "content": "Call emergency services immediately...",
        "timestamp": "2025-10-03T11:58:18+05:30",
        "sources": "OSHA Safety Standards, Emergency Procedures Manual"
      }
    ],
    "total_messages": 4
  }
}
```

#### 3. `heartbeat` - Connection Keep-Alive
Sent every 30 seconds to keep the connection alive.

```json
{
  "event": "heartbeat",
  "data": {
    "timestamp": "2025-10-03T12:00:00+05:30",
    "status": "connected"
  }
}
```

#### 4. `ended` - Conversation Ended
Sent when the conversation or call has ended.

```json
{
  "event": "ended",
  "data": {
    "message": "Conversation has ended",
    "conversation_id": "conv_919325590143_20251003_115804"
  }
}
```

#### 5. `error` - Error Occurred
Sent when an error occurs during streaming.

```json
{
  "event": "error",
  "data": {
    "error": "Access denied. You don't have permission to view this conversation.",
    "conversation_id": "conv_919325590143_20251003_115804"
  }
}
```

---

## Client Implementation Examples

### JavaScript/TypeScript (Browser)

```javascript
// Using EventSource API
const conversationId = 'conv_919325590143_20251003_115804';
const token = 'your_jwt_token_here';

const eventSource = new EventSource(
  `/api/conversation/${conversationId}/stream`,
  {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  }
);

// Handle initial data
eventSource.addEventListener('initial', (event) => {
  const data = JSON.parse(event.data);
  console.log('Initial conversation:', data);
  displayMessages(data.messages);
});

// Handle new messages
eventSource.addEventListener('new_messages', (event) => {
  const data = JSON.parse(event.data);
  console.log('New messages:', data.messages);
  appendMessages(data.messages);
});

// Handle conversation ended
eventSource.addEventListener('ended', (event) => {
  const data = JSON.parse(event.data);
  console.log('Conversation ended:', data.message);
  eventSource.close();
});

// Handle errors
eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Stream error:', data.error);
  eventSource.close();
});

// Handle heartbeat (optional)
eventSource.addEventListener('heartbeat', (event) => {
  console.log('Connection alive');
});

// Close connection when done
function cleanup() {
  eventSource.close();
}
```

### Python (using requests)

```python
import requests
import json

conversation_id = 'conv_919325590143_20251003_115804'
token = 'your_jwt_token_here'

headers = {
    'Authorization': f'Bearer {token}',
    'Accept': 'text/event-stream'
}

url = f'http://localhost:5000/api/conversation/{conversation_id}/stream'

with requests.get(url, headers=headers, stream=True) as response:
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            
            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                
            elif line.startswith('data:'):
                data = json.loads(line.split(':', 1)[1].strip())
                
                if event_type == 'initial':
                    print(f"Initial messages: {len(data['messages'])}")
                    
                elif event_type == 'new_messages':
                    print(f"New messages: {len(data['messages'])}")
                    for msg in data['messages']:
                        print(f"  {msg['role']}: {msg['content']}")
                        
                elif event_type == 'ended':
                    print("Conversation ended")
                    break
                    
                elif event_type == 'error':
                    print(f"Error: {data['error']}")
                    break
```

### React Hook Example

```typescript
import { useEffect, useState } from 'react';

interface Message {
  message_id: string;
  role: string;
  content: string;
  timestamp: string;
  sources: string;
}

export function useConversationStream(conversationId: string, token: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/conversation/${conversationId}/stream`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    eventSource.addEventListener('initial', (event) => {
      const data = JSON.parse(event.data);
      setMessages(data.messages);
      setIsConnected(true);
    });

    eventSource.addEventListener('new_messages', (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, ...data.messages]);
    });

    eventSource.addEventListener('ended', () => {
      setIsConnected(false);
      eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
      const data = JSON.parse(event.data);
      setError(data.error);
      setIsConnected(false);
      eventSource.close();
    });

    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [conversationId, token]);

  return { messages, isConnected, error };
}

// Usage in component
function ConversationView({ conversationId }: { conversationId: string }) {
  const token = localStorage.getItem('auth_token');
  const { messages, isConnected, error } = useConversationStream(conversationId, token);

  if (error) return <div>Error: {error}</div>;
  if (!isConnected) return <div>Connecting...</div>;

  return (
    <div>
      {messages.map(msg => (
        <div key={msg.message_id}>
          <strong>{msg.role}:</strong> {msg.content}
        </div>
      ))}
    </div>
  );
}
```

---

## Testing with cURL

### Get Conversation Snapshot

```bash
curl -X GET "http://localhost:5000/api/conversation/conv_919325590143_20251003_115804" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Accept: application/json"
```

### Stream Conversation (SSE)

```bash
curl -N -X GET "http://localhost:5000/api/conversation/conv_919325590143_20251003_115804/stream" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Accept: text/event-stream"
```

---

## Best Practices

1. **Connection Management**
   - Always close SSE connections when the component unmounts or user navigates away
   - Handle reconnection logic if the connection drops
   - Monitor heartbeat events to detect connection issues

2. **Error Handling**
   - Always handle the `error` event type
   - Implement fallback to snapshot endpoint if streaming fails
   - Show user-friendly error messages

3. **Performance**
   - Use the snapshot endpoint for initial load if you don't need real-time updates
   - Use streaming only for active monitoring scenarios
   - Limit the number of concurrent SSE connections

4. **Security**
   - Always include the Authorization header with a valid JWT token
   - Token expiration will automatically close the stream
   - Don't expose conversation IDs to unauthorized users

5. **UI/UX**
   - Show a loading indicator while connecting
   - Display connection status to users
   - Auto-scroll to new messages
   - Highlight new messages temporarily

---

## Architecture Notes

### Data Flow

1. **Initial Request**: Admin requests conversation stream
2. **Authentication**: Verify JWT token and check blacklist
3. **Authorization**: Verify admin has access to the conversation
4. **Initial Data**: Send complete conversation history
5. **Monitoring**: Poll Firebase Realtime Database every second
6. **Updates**: Send new messages as they arrive
7. **Cleanup**: Close stream when conversation ends

### Database Structure

- **Firebase Realtime Database**: Stores active conversations
  - Path: `active_conversations/{conversation_id}/`
  - Contains: call_id, messages{}
  
- **Firebase Realtime Database**: Stores active calls
  - Path: `active_calls/{call_id}/`
  - Contains: worker_id, admin_id, urgency, status, etc.

- **Firestore**: Stores admin and worker information
  - Collection: `admins/`
  - Collection: `workers/`

### Polling Interval

- The streaming endpoint polls Firebase every 1 second for new messages
- Heartbeat events are sent every 30 seconds
- This balance ensures real-time updates without overloading the database

---

## Troubleshooting

### Connection Immediately Closes

- **Cause**: Token expired or invalid
- **Solution**: Refresh the JWT token and reconnect

### Not Receiving New Messages

- **Cause**: Conversation ended or polling interval too high
- **Solution**: Check if conversation is still active, verify database updates

### 403 Forbidden Error

- **Cause**: Admin doesn't have access to the conversation
- **Solution**: Verify the worker belongs to the admin's company or call is assigned to the admin

### High Server Load

- **Cause**: Too many concurrent SSE connections
- **Solution**: Implement connection pooling, increase polling interval, or use WebSockets

---

## Future Enhancements

1. **WebSocket Support**: Replace SSE with WebSocket for bi-directional communication
2. **Message Acknowledgment**: Track which messages admin has seen
3. **Typing Indicators**: Show when user is typing
4. **Rich Media Support**: Support for images, audio, location data
5. **Message Search**: Full-text search across conversations
6. **Export Conversation**: Download conversation as PDF or JSON
