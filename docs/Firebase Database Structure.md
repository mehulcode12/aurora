# Firebase Database Structure

### 1. Firebase Realtime Database (Active Calls)

**Purpose:** Store real-time, actively changing data that requires instant synchronization and low latency.

**Structure:**
```
active_calls/
  {call_id}/
    worker_id: "string"
    mobile_no: "string"
    conversation_id: "string"
    urgency: "CRITICAL" | "URGENT" | "NORMAL"
    status: "ACTIVE"
    timestamp: timestamp
    medium: "Text" | "Voice"
    last_message_at: timestamp
    admin_id: "string" (if taken over)
    
active_conversations/
  {conversation_id}/
    call_id: "string"
    messages/
      {message_id}/
        role: "user" | "assistant"
        content: "string"
        timestamp: timestamp
        sources: "string"
```
---

### 2. Firestore (Historical & Reference Data)

**Purpose:** Store structured, queryable data for completed calls, user profiles, and audit trails.

**Collections:**

**admins/** (Collection)
```
{admin_id}/ (Document)
  email: "string"
  name: "string"
  company_name: "string"
  designation: "string"
  sop_manuals_id: "string" (reference to sop_manuals)
  created_at: timestamp
  last_login: timestamp
```

**sops_manuals/** (Collection)
```
{sop_manuals_id}/ (Document)
  sop_manual_guidelines: "string"
```

**workers/** (Collection)
```
{worker_id}/ (Document)
  mobile_numbers: ["string"]
  name: "string"
  department: "string"
  admin_id: "string" (reference to admin)
  created_at: timestamp
  is_active: boolean
```

**calls/** (Collection)
```
{call_id}/ (Document)
  worker_id: "string"
  mobile_no: "string"
  conversation_id: "string"
  urgency: "CRITICAL" | "URGENT" | "NORMAL"
  status: "COMPLETE" | "TAKEOVER"
  timestamp: timestamp
  medium: "Text" | "Voice"
  final_action: "Police" | "Ambulance" | "Fire" | null
  admin_id: "string" (if taken over)
  resolved_at: timestamp
  duration_seconds: number (optional)
  admin_notes: "string" (optional)
```

**conversations/** (Collection)
```
{conversation_id}/ (Document)
  call_id: "string"
  messages: [
    {
      role: "user" | "assistant",
      content: "string",
      timestamp: timestamp
    }
  ]
  archived_at: timestamp
  total_messages: number
```