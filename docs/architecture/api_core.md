# Core API v1

## Scope

The Core API is the Reception control surface. It reports runtime and Workshop state and will own sessions, pipelines and jobs. It does not expose Photo-specific implementation as the platform contract.

## Read endpoints implemented in the first rewrite pass

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/api/v1/runtime` | Runtime state, package/model signals, GPU information and discovered Workshops. |
| `GET` | `/api/v1/workshops` | Deterministic list of discovered Workshop descriptors. |
| `GET` | `/api/v1/workshops/{id}` | One Workshop descriptor or `404`. |
| `GET` | `/api/v1/workshops/{id}/readiness` | Whether a Workshop is enabled, valid and resource-ready. |

These endpoints are read-only. They never download resources or import Workshop UI code.

## Compatibility endpoints

`GET /health` remains the existing Photo engine health endpoint. `POST /process` remains a Photo Workshop-specific multipart endpoint. Clients must not infer that a successful Photo request means the whole NaChance runtime is ready.

## Planned mutation endpoints

The next layer will add explicit lifecycle operations:

```text
POST /api/v1/resources/{resource_id}/resolve
POST /api/v1/pipelines
PUT  /api/v1/pipelines/{pipeline_id}
POST /api/v1/sessions
POST /api/v1/jobs
POST /api/v1/jobs/{job_id}/cancel
GET  /api/v1/jobs/{job_id}
GET  /api/v1/jobs/{job_id}/events
```

Every mutation must return an identifier, current state and request ID. Long-running work must be represented by a Job rather than blocking an HTTP request until a model finishes.

## Error envelope

Future endpoints should use a common structure:

```json
{
  "error": {
    "code": "WORKSHOP_NOT_READY",
    "message": "Workshop resources are missing",
    "details": {"workshop_id": "photo", "resources": ["..."]},
    "request_id": "..."
  }
}
```

## Public deployment requirements

Before exposing this API to general users, add authentication, authorization, upload limits, timeouts, cancellation, concurrency limits, structured logs, privacy-aware temporary file cleanup and a queue for GPU work.
