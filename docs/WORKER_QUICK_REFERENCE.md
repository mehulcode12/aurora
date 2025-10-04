# Worker Management - Quick Reference

## Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/workers` | Create new worker | ✅ |
| GET | `/api/workers` | Get all workers | ✅ |
| GET | `/api/workers/{worker_id}` | Get specific worker | ✅ |
| PUT | `/api/workers/{worker_id}` | Update worker | ✅ |
| DELETE | `/api/workers/{worker_id}` | Delete worker | ✅ |

## Worker ID Format
```
worker_{mobile_number}
```
**Example**: `worker_919325590143`
- Includes country code (no + symbol)
- No spaces or special characters

## Request/Response Examples

### Create Worker
```json
POST /api/workers
Headers: { "Authorization": "Bearer TOKEN" }
Body:
{
  "mobile_numbers": "+91 9325590143",
  "name": "John Doe",
  "department": "Manufacturing"
}

Response:
{
  "success": true,
  "worker_id": "worker_919325590143",
  "message": "Worker created successfully"
}
```

### Get All Workers
```json
GET /api/workers
Headers: { "Authorization": "Bearer TOKEN" }

Response:
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
    }
  ]
}
```

### Update Worker
```json
PUT /api/workers/worker_919325590143
Headers: { "Authorization": "Bearer TOKEN" }
Body:
{
  "name": "John Updated",
  "department": "Quality Control",
  "is_active": false
}

Response:
{
  "success": true,
  "message": "Worker updated successfully"
}
```

### Delete Worker
```json
DELETE /api/workers/worker_919325590143
Headers: { "Authorization": "Bearer TOKEN" }

Response:
{
  "success": true,
  "message": "Worker deleted successfully"
}
```

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (invalid data) |
| 401 | Unauthorized (invalid/missing token) |
| 403 | Forbidden (no access to this worker) |
| 404 | Not Found (worker doesn't exist) |
| 409 | Conflict (worker already exists) |
| 500 | Internal Server Error |

## Field Specifications

### Required Fields (Create)
- `mobile_numbers` (string): Phone number with country code
- `name` (string): Worker's full name
- `department` (string): Department name

### Optional Fields (Update)
- `name` (string): Updated name
- `department` (string): Updated department
- `is_active` (boolean): Active status

### Read-Only Fields
- `worker_id` (auto-generated)
- `admin_id` (from auth token)
- `created_at` (auto-generated)

## Firebase Schema
```
Firestore Collection: workers/
Document ID: worker_{mobile_number}
Fields:
  - mobile_numbers: string
  - name: string
  - department: string
  - admin_id: string
  - created_at: timestamp
  - is_active: boolean
```

## Security Notes
- All endpoints require valid JWT access token
- Workers are isolated by admin_id
- Cross-admin access is prevented
- Tokens are validated against Redis blacklist

## Testing
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- Test with Postman or curl

## Common Issues

### Issue: "Worker already exists"
**Solution**: Each mobile number can only be registered once. Use a different number or delete the existing worker first.

### Issue: "You don't have permission to access this worker"
**Solution**: You can only access workers you created. Check that you're logged in with the correct admin account.

### Issue: "Mobile number must contain only digits"
**Solution**: Ensure the mobile number contains only digits after removing +, spaces, and hyphens.

### Issue: "No fields to update"
**Solution**: Provide at least one field (name, department, or is_active) in the update request.
