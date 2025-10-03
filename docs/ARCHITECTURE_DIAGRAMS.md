# Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Aurora Emergency Assistant                   │
│                        Live Conversation Streaming                   │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Browser    │         │   Python     │         │    Mobile    │
│   Client     │◄───────►│   Client     │◄───────►│     App      │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │ HTTPS/SSE
                                ↓
                    ┌───────────────────────┐
                    │    FastAPI Server     │
                    │      (main.py)        │
                    └───────────┬───────────┘
                                │
                ┌───────────────┼───────────────┐
                ↓               ↓               ↓
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │   Firebase   │ │  Firestore   │ │    Redis     │
        │  Realtime DB │ │  (Metadata)  │ │ (Blacklist)  │
        └──────────────┘ └──────────────┘ └──────────────┘
```

## Authentication Flow

```
┌─────────┐                                    ┌──────────────┐
│ Client  │                                    │  FastAPI     │
└────┬────┘                                    └──────┬───────┘
     │                                                │
     │  1. POST /login                               │
     │  {email, password}                            │
     ├───────────────────────────────────────────────►
     │                                                │
     │                         2. Verify credentials │
     │                            in Firestore       │
     │                                                ├──────────┐
     │                                                │          │
     │                                                │◄─────────┘
     │                                                │
     │  3. Return JWT token                          │
     │◄───────────────────────────────────────────────┤
     │  {access_token, admin_id}                     │
     │                                                │
     │  4. Store token                               │
     ├────────┐                                      │
     │        │                                      │
     │◄───────┘                                      │
     │                                                │
     │  5. Use token for all requests                │
     │  Authorization: Bearer <token>                │
     ├───────────────────────────────────────────────►
     │                                                │
```

## Streaming Connection Flow

```
┌─────────┐                  ┌──────────────┐                  ┌──────────────┐
│ Client  │                  │  FastAPI     │                  │  Firebase    │
└────┬────┘                  └──────┬───────┘                  └──────┬───────┘
     │                              │                                 │
     │ 1. GET /api/conversation/    │                                 │
     │    {id}/stream               │                                 │
     ├──────────────────────────────►                                 │
     │                              │                                 │
     │                              │ 2. Verify JWT token             │
     │                              ├──────────┐                      │
     │                              │          │                      │
     │                              │◄─────────┘                      │
     │                              │                                 │
     │                              │ 3. Check authorization          │
     │                              │    (admin → worker → conv)      │
     │                              ├──────────┐                      │
     │                              │          │                      │
     │                              │◄─────────┘                      │
     │                              │                                 │
     │                              │ 4. Fetch conversation           │
     │                              ├─────────────────────────────────►
     │                              │                                 │
     │                              │ 5. Return messages              │
     │                              │◄─────────────────────────────────┤
     │                              │                                 │
     │ 6. Send 'initial' event      │                                 │
     │◄──────────────────────────────┤                                 │
     │  {messages: [...]}           │                                 │
     │                              │                                 │
     │                              │ ╔══════════════════════════╗    │
     │                              │ ║   Polling Loop (1s)      ║    │
     │                              │ ╚══════════════════════════╝    │
     │                              │                                 │
     │                              │ 7. Poll for new messages        │
     │                              ├─────────────────────────────────►
     │                              │                                 │
     │                              │ 8. Return current state         │
     │                              │◄─────────────────────────────────┤
     │                              │                                 │
     │                              │ 9. Compare message count        │
     │                              ├──────────┐                      │
     │                              │          │                      │
     │                              │◄─────────┘                      │
     │                              │                                 │
     │ 10. Send 'new_messages'      │                                 │
     │     event (if new)           │                                 │
     │◄──────────────────────────────┤                                 │
     │  {messages: [new1, new2]}    │                                 │
     │                              │                                 │
     │                              │ ╔══════════════════════════╗    │
     │                              │ ║   Every 30 seconds       ║    │
     │                              │ ╚══════════════════════════╝    │
     │                              │                                 │
     │ 11. Send 'heartbeat' event   │                                 │
     │◄──────────────────────────────┤                                 │
     │  {status: "connected"}       │                                 │
     │                              │                                 │
     │                              │ 12. Detect conversation end     │
     │                              ├─────────────────────────────────►
     │                              │                                 │
     │                              │ 13. No data returned            │
     │                              │◄─────────────────────────────────┤
     │                              │                                 │
     │ 14. Send 'ended' event       │                                 │
     │◄──────────────────────────────┤                                 │
     │  {message: "Conversation..."}│                                 │
     │                              │                                 │
     │ 15. Close connection         │                                 │
     ├──────────────────────────────►                                 │
     │                              │                                 │
```

## Authorization Logic

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Authorization Decision Tree                      │
└─────────────────────────────────────────────────────────────────────┘

                         Admin Requests Conversation
                                    ↓
                         ┌──────────────────────┐
                         │  Get Conversation    │
                         │  from Firebase       │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │  Get Associated Call │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Call has admin_id?   │
                         └──────────┬───────────┘
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
                   YES                             NO
                    │                               │
         ┌──────────▼──────────┐      ┌────────────▼────────────┐
         │ admin_id matches    │      │ Get worker from call    │
         │ requesting admin?   │      └────────────┬────────────┘
         └──────────┬──────────┘                   ↓
                    │              ┌────────────────────────────┐
        ┌───────────┴────────┐     │ Worker belongs to admin's │
        │                    │     │ company?                  │
       YES                  NO     └────────────┬───────────────┘
        │                    │                  │
        │                    │      ┌───────────┴────────┐
        │                    │      │                    │
        ↓                    ↓     YES                  NO
  ┌──────────┐       ┌──────────┐  │                    │
  │  ALLOW   │       │  DENY    │  │                    │
  │  ACCESS  │       │  403     │  ↓                    ↓
  └──────────┘       └──────────┘ ┌──────────┐   ┌──────────┐
                                   │  ALLOW   │   │  DENY    │
                                   │  ACCESS  │   │  403     │
                                   └──────────┘   └──────────┘

Access Granted if:
✅ Call is assigned to the admin (admin_id matches), OR
✅ Call is unassigned AND worker belongs to admin's company
```

## Data Flow - Message Detection

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Message Detection Algorithm                       │
└─────────────────────────────────────────────────────────────────────┘

                              Start Streaming
                                    ↓
                         ┌──────────────────────┐
                         │  Initialize          │
                         │  last_message_count  │
                         │  = initial count     │
                         └──────────┬───────────┘
                                    ↓
                         ╔═════════════════════╗
                         ║  Wait 1 second      ║
                         ╚══════════┬══════════╝
                                    ↓
                         ┌──────────────────────┐
                         │  Fetch current       │
                         │  conversation state  │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │  current_count =     │
                         │  len(messages)       │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ current_count >      │
                         │ last_message_count?  │
                         └──────────┬───────────┘
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
                   YES                             NO
                    │                               │
         ┌──────────▼──────────┐      ┌────────────▼────────────┐
         │ Get new messages    │      │ No action needed        │
         │ [last_count:]       │      └────────────┬────────────┘
         └──────────┬──────────┘                   │
                    │                              │
         ┌──────────▼──────────┐                   │
         │ Send 'new_messages' │                   │
         │ event to client     │                   │
         └──────────┬──────────┘                   │
                    │                              │
         ┌──────────▼──────────┐                   │
         │ Update              │                   │
         │ last_message_count  │                   │
         └──────────┬──────────┘                   │
                    │                              │
                    └──────────────┬───────────────┘
                                   ↓
                         ┌──────────────────────┐
                         │ Conversation still   │
                         │ active?              │
                         └──────────┬───────────┘
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
                   YES                             NO
                    │                               │
                    │              ┌────────────────▼────────────┐
                    │              │ Send 'ended' event          │
                    │              │ Close connection            │
                    │              └─────────────────────────────┘
                    │
                    └───────────────┐
                                    ↓
                         ╔═════════════════════╗
                         ║  Loop back to       ║
                         ║  "Wait 1 second"    ║
                         ╚═════════════════════╝
```

## Database Structure

```
Firebase Realtime Database
├── active_calls/
│   └── call_{phone}_{timestamp}/
│       ├── worker_id: "worker_123"
│       ├── mobile_no: "+919325590143"
│       ├── conversation_id: "conv_123"
│       ├── urgency: "CRITICAL"
│       ├── status: "ACTIVE"
│       ├── timestamp: "2025-10-03T11:58:04+05:30"
│       ├── medium: "Voice"
│       ├── last_message_at: "2025-10-03T23:43:59+05:30"
│       └── admin_id: "admin_456" (optional)
│
└── active_conversations/
    └── conv_{phone}_{timestamp}/
        ├── call_id: "call_123"
        └── messages/
            ├── msg_001/
            │   ├── role: "user"
            │   ├── content: "Emergency message"
            │   ├── timestamp: "2025-10-03T11:58:04+05:30"
            │   └── sources: ""
            │
            └── msg_002/
                ├── role: "assistant"
                ├── content: "Help is on the way"
                ├── timestamp: "2025-10-03T11:58:10+05:30"
                └── sources: "Emergency Manual"

Firestore
├── admins/ (Collection)
│   └── {admin_id}/ (Document)
│       ├── email: "admin@example.com"
│       ├── name: "John Doe"
│       ├── company_name: "Acme Corp"
│       ├── designation: "Safety Manager"
│       ├── sop_manuals_id: "sop_123"
│       ├── created_at: timestamp
│       └── last_login: timestamp
│
└── workers/ (Collection)
    └── {worker_id}/ (Document)
        ├── mobile_numbers: ["+919325590143"]
        ├── name: "Worker Name"
        ├── department: "Manufacturing"
        ├── admin_id: "admin_456"
        ├── created_at: timestamp
        └── is_active: true

Redis
└── token_blacklist/
    └── {token_hash}: expiry_timestamp
```

## Event Types Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SSE Event Types                               │
└─────────────────────────────────────────────────────────────────────┘

Connection Established
        ↓
┌───────────────┐
│   'initial'   │  ← Sent once at connection start
└───────┬───────┘
        │        • Contains all existing messages
        │        • Call metadata (urgency, status, etc.)
        │        • Total message count
        ↓
┌───────────────┐
│ Polling Loop  │
└───────┬───────┘
        │
        ├──► New messages detected?
        │         ↓
        │    ┌──────────────────┐
        │    │ 'new_messages'   │  ← Sent when new messages arrive
        │    └──────────────────┘
        │         • Contains only new messages
        │         • Updated total count
        │
        ├──► Every 30 seconds
        │         ↓
        │    ┌──────────────────┐
        │    │  'heartbeat'     │  ← Keep connection alive
        │    └──────────────────┘
        │         • Confirms connection is active
        │         • Current timestamp
        │
        ├──► Conversation ended?
        │         ↓
        │    ┌──────────────────┐
        │    │    'ended'       │  ← Sent when conversation closes
        │    └──────────────────┘
        │         • Reason for ending
        │         • Final state
        │         ↓
        │    ═══ Connection Closed ═══
        │
        └──► Error occurred?
                  ↓
             ┌──────────────────┐
             │    'error'       │  ← Sent on error
             └──────────────────┘
                  • Error description
                  • Error context
                  ↓
             ═══ Connection Closed ═══
```

## Scalability Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Production Deployment                            │
└─────────────────────────────────────────────────────────────────────┘

                         ┌──────────────────┐
                         │   Load Balancer  │
                         │    (Nginx)       │
                         └────────┬─────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                ↓                 ↓                 ↓
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │  FastAPI     │  │  FastAPI     │  │  FastAPI     │
        │  Instance 1  │  │  Instance 2  │  │  Instance 3  │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
               └─────────────────┼─────────────────┘
                                 ↓
                 ┌───────────────────────────────┐
                 │   Shared Resources            │
                 │                               │
                 │  ┌─────────────────────────┐ │
                 │  │  Firebase (Primary)     │ │
                 │  │  - Realtime Database    │ │
                 │  │  - Firestore            │ │
                 │  └─────────────────────────┘ │
                 │                               │
                 │  ┌─────────────────────────┐ │
                 │  │  Redis (Shared)         │ │
                 │  │  - Token blacklist      │ │
                 │  │  - Rate limiting        │ │
                 │  └─────────────────────────┘ │
                 │                               │
                 └───────────────────────────────┘

Recommended Configuration:
- 3-5 FastAPI instances
- Nginx for load balancing
- Redis for shared state
- Firebase with automatic scaling
- Connection limit: 100 per instance
```

---

**These diagrams visualize the complete architecture and flow of the Live Conversation Streaming system.**
