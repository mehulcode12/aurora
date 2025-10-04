# Worker Management Endpoints

## Overview
This document describes the REST API endpoints for managing workers in the Aurora Emergency Assistant system. All endpoints require admin authentication via JWT token.

## Worker ID Format
- **Format**: `worker_{mobile_number}`
- **Example**: `worker_919325590143`
- Mobile number includes country code (e.g., 91 for India)
- Mobile number excludes the `+` symbol
- All spaces, hyphens, and special characters are removed

## Data Model

### Worker Schema (Firestore Collection: `workers/`)
```json
{
  "worker_id": "worker_919325590143",
  "mobile_numbers": "+91 9325590143",
  "name": "John Doe",
  "department": "Manufacturing",
  "admin_id": "admin123",
  "created_at": "2025-10-05T10:30:00Z",
  "is_active": true
}
```

## Endpoints

### 1. Create Worker
**POST** `/api/workers`

Create a new worker in the system.

#### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Request Body
```json
{
  "mobile_numbers": "+91 9325590143",
  "name": "John Doe",
  "department": "Manufacturing"
}
```

#### Response (201 Created)
```json
{
  "success": true,
  "worker_id": "worker_919325590143",
  "message": "Worker created successfully"
}
```

#### Error Responses
- **400 Bad Request**: Invalid mobile number format
- **401 Unauthorized**: Missing or invalid token
- **409 Conflict**: Worker with this mobile number already exists
- **500 Internal Server Error**: Server error

---

### 2. Get All Workers
**GET** `/api/workers`

Retrieve all workers belonging to the authenticated admin.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Response (200 OK)
```json
{
  "success": true,
  "workers": [
    {
      "worker_id": "worker_919325590143",
      "mobile_numbers": "+91 9325590143",
      "name": "John Doe",
      "department": "Manufacturing",
      "admin_id": "admin123",
      "created_at": "2025-10-05T10:30:00Z",
      "is_active": true
    },
    {
      "worker_id": "worker_919876543210",
      "mobile_numbers": "+91 9876543210",
      "name": "Jane Smith",
      "department": "Quality Control",
      "admin_id": "admin123",
      "created_at": "2025-10-05T11:00:00Z",
      "is_active": true
    }
  ]
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **500 Internal Server Error**: Server error

---

### 3. Get Specific Worker
**GET** `/api/workers/{worker_id}`

Retrieve details of a specific worker.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Path Parameters
- `worker_id` (string): The worker's ID (e.g., `worker_919325590143`)

#### Response (200 OK)
```json
{
  "success": true,
  "worker": {
    "worker_id": "worker_919325590143",
    "mobile_numbers": "+91 9325590143",
    "name": "John Doe",
    "department": "Manufacturing",
    "admin_id": "admin123",
    "created_at": "2025-10-05T10:30:00Z",
    "is_active": true
  }
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Worker doesn't belong to this admin
- **404 Not Found**: Worker not found
- **500 Internal Server Error**: Server error

---

### 4. Update Worker
**PUT** `/api/workers/{worker_id}`

Update a worker's information. Only provided fields will be updated.

#### Headers
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

#### Path Parameters
- `worker_id` (string): The worker's ID (e.g., `worker_919325590143`)

#### Request Body (all fields optional)
```json
{
  "name": "John Updated",
  "department": "Quality Control",
  "is_active": false
}
```

#### Response (200 OK)
```json
{
  "success": true,
  "message": "Worker updated successfully"
}
```

#### Error Responses
- **400 Bad Request**: No fields to update
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Worker doesn't belong to this admin
- **404 Not Found**: Worker not found
- **500 Internal Server Error**: Server error

---

### 5. Delete Worker
**DELETE** `/api/workers/{worker_id}`

Permanently delete a worker from the system.

#### Headers
```
Authorization: Bearer <access_token>
```

#### Path Parameters
- `worker_id` (string): The worker's ID (e.g., `worker_919325590143`)

#### Response (200 OK)
```json
{
  "success": true,
  "message": "Worker deleted successfully"
}
```

#### Error Responses
- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: Worker doesn't belong to this admin
- **404 Not Found**: Worker not found
- **500 Internal Server Error**: Server error

---

## Authentication

All worker endpoints require a valid JWT access token obtained from the `/login` endpoint.

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

### Example 1: Create a Worker

```bash
curl -X POST https://your-api.com/api/workers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_numbers": "+91 9325590143",
    "name": "John Doe",
    "department": "Manufacturing"
  }'
```

### Example 2: Get All Workers

```bash
curl -X GET https://your-api.com/api/workers \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Example 3: Update a Worker

```bash
curl -X PUT https://your-api.com/api/workers/worker_919325590143 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "department": "Quality Control",
    "is_active": true
  }'
```

### Example 4: Delete a Worker

```bash
curl -X DELETE https://your-api.com/api/workers/worker_919325590143 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Notes

1. **Worker ID Generation**: The system automatically generates worker IDs based on mobile numbers. You cannot specify a custom worker_id.

2. **Mobile Number Format**: The API accepts mobile numbers with spaces, hyphens, and + symbols, but internally stores and uses cleaned versions.

3. **Admin Isolation**: Each admin can only access workers they created. Cross-admin access is prevented.

4. **Soft Delete Option**: Instead of deleting workers, consider setting `is_active: false` to maintain historical records.

5. **Unique Mobile Numbers**: Each mobile number can only be registered once in the system.

6. **Field Validation**: 
   - `mobile_numbers`: Must contain only digits after cleaning
   - `name`: Required, non-empty string
   - `department`: Required, non-empty string

---

## Integration with Firebase

Workers are stored in Firestore under the `workers/` collection according to the schema defined in `Firebase Database Structure.md`.

### Firestore Structure
```
workers/
  worker_919325590143/
    mobile_numbers: "+91 9325590143"
    name: "John Doe"
    department: "Manufacturing"
    admin_id: "admin123"
    created_at: <timestamp>
    is_active: true
```

---

## Security Considerations

1. **Authentication Required**: All endpoints require valid JWT tokens
2. **Admin Authorization**: Workers are isolated by admin_id
3. **Input Validation**: Mobile numbers and other fields are validated
4. **Error Messages**: Sensitive information is not exposed in error messages
5. **Token Blacklisting**: Revoked tokens are checked against Redis blacklist

---

## Testing

You can test these endpoints using:
- **Swagger UI**: Visit `/docs` on your API server
- **ReDoc**: Visit `/redoc` on your API server
- **Postman**: Import the OpenAPI spec from `/openapi.json`
- **curl**: Use command-line examples above

---

## Support

For issues or questions about worker management endpoints, refer to:
- Main documentation: `README.md`
- Firebase structure: `Firebase Database Structure.md`
- API documentation: `/docs` endpoint
