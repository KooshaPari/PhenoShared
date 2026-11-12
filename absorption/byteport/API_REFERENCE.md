# BytePort API Reference

Base URL: `http://localhost:8080`

## Authentication

All protected endpoints require a Bearer token:

```
Authorization: Bearer <jwt_token>
```

Obtain a token via `POST /login` or `POST /signup`.

---

## Public Endpoints

### POST /login

Authenticate and receive a JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": { "id": "...", "email": "..." }
}
```

### POST /signup

Create a new account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "name": "User Name"
}
```

**Response (201):**
```json
{
  "message": "Account created",
  "user": { "id": "...", "email": "..." }
}
```

### GET /health

Health check endpoint. No authentication required.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "byteport",
  "uptime": "1h23m45s"
}
```

### GET /metrics

Prometheus metrics endpoint. No authentication required.

**Response (200):** Prometheus text format
```
byteport_uptime_seconds 5025.00
byteport_requests_total 1234
byteport_errors_total 3
byteport_deploys_total 42
byteport_sandboxes_active 5
byteport_memory_alloc_bytes 12345678
byteport_memory_sys_bytes 23456789
byteport_goroutines 15
```

---

## Protected Endpoints

### GET /projects

List all projects for the authenticated user.

**Response (200):**
```json
{
  "projects": [
    {
      "id": "...",
      "name": "my-project",
      "status": "deployed",
      "repository": "https://github.com/user/repo"
    }
  ]
}
```

### GET /instances

List all running instances/sandboxes.

**Response (200):**
```json
{
  "instances": [
    {
      "uuid": "sb-123",
      "name": "my-project",
      "status": "running"
    }
  ]
}
```

### POST /deploy

Deploy a project to NanoVMS.

**Request:**
```json
{
  "name": "my-project",
  "repository_id": "repo-uuid",
  "repository": "https://github.com/user/repo"
}
```

**Response (200):**
```json
{
  "message": "Success",
  "sandbox_id": "native-2",
  "status": "running"
}
```

**NanoVMS contract:** Sends `POST /v1/deploy` to NanoVMS with:
```json
{
  "name": "my-project",
  "image": "alpine:latest",
  "sandbox_type": "native",
  "labels": { "byteport-project-id": "..." }
}
```

### POST /terminate

Stop and remove a deployed instance.

**Request:**
```json
{
  "uuid": "sb-123"
}
```

**Response (200):**
```json
{
  "message": "Success"
}
```

**NanoVMS contract:** Sends `POST /v1/stop?id=<sandbox_id>` to NanoVMS.

### GET /link

Get deployment link information.

### POST /link

Validate a deployment link.

### GET /authenticate

GitHub authentication check.

### GET /api/github/repositories

List repositories from connected GitHub account.

### GET /user/:id/creds

Update user credentials.

### PUT /user/:id/creds

Update user profile.

---

## Error Responses

All errors follow the format:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common status codes:
- `400` — Bad request (invalid input)
- `401` — Unauthorized (missing/invalid token)
- `404` — Resource not found
- `500` — Internal server error

---

## NanoVMS Integration

BytePort communicates with NanoVMS for sandbox lifecycle management:

| BytePort Action | NanoVMS Endpoint | Method |
|----------------|-----------------|--------|
| Deploy project | `/v1/deploy` | POST |
| Stop instance | `/v1/stop?id=<id>` | POST |
| List sandboxes | `/v1/sandboxes` | GET |
| Get status | `/v1/sandboxes/<id>` | GET |
| Delete sandbox | `/v1/sandboxes/<id>` | DELETE |

**Authentication:** Bearer token via `NVMS_TOKEN` environment variable.
