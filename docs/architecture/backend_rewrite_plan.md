# Backend rewrite plan — NaChance Core

## Purpose

NaChance is a platform/runtime and orchestration layer. It discovers and presents independent Workshops, verifies runtime and resources, manages pipelines and sessions, and exposes a stable control surface for desktop and mobile clients. Photo and Layout are Workshop implementations, not the product boundary.

## Non-negotiable boundaries

| Boundary | Responsibility | Must not do |
|---|---|---|
| Bootstrap | Locate the project, initialize logging, invoke runtime checks and enter setup/app. | Own Workshop business logic. |
| Runtime | Report Python, packages, GPU/CUDA, resource and readiness state. | Silently install or mutate state during a read-only check. |
| Resource | Describe, resolve, download, verify and version resources. | Know Photo-specific processing. |
| Reception/Core | Discover Workshops, expose metadata, create sessions, validate pipelines and coordinate jobs. | Import a hard-coded list of Workshops. |
| Workshop | Own its manifest, UI, capabilities, adapters, requirements and business logic. | Call another Workshop directly. |
| Pipeline | Connect Workshop steps and persist configuration/snapshots. | Embed model implementation. |
| API | Expose stable versioned contracts for clients. | Treat Photo `/process` as the whole NaChance API. |

## Domain objects

The first stable contracts are `RuntimeReport`, `WorkshopDescriptor`, `ResourceStatus`, `PipelineDefinition`, `Session`, `Job` and `DomainError`. All status values use explicit enums. Every mutating operation returns an id and an observable state transition.

## API v1 surface

```text
GET  /api/v1/runtime
GET  /api/v1/workshops
GET  /api/v1/workshops/{workshop_id}
GET  /api/v1/workshops/{workshop_id}/readiness
GET  /api/v1/pipelines
POST /api/v1/pipelines
GET  /api/v1/pipelines/{pipeline_id}
POST /api/v1/sessions
POST /api/v1/jobs
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/cancel
GET  /api/v1/jobs/{job_id}/events
```

The existing `/health` and Photo-specific `/process` endpoints remain compatibility endpoints. They should delegate to Core services rather than define the entire platform.

## Resource lifecycle

```text
DECLARED → MISSING → RESOLVING → DOWNLOADING → VERIFYING → READY
                                      └──────────────→ ERROR
READY → OUTDATED
```

A read-only runtime report never downloads resources. Provisioning is an explicit command and records source, version, checksum, timestamps and error details.

## Rewrite order

1. Add pure contracts and deterministic discovery without changing Workshop internals.
2. Add registry validation and runtime/readiness reporting.
3. Add Core services for pipelines, sessions and jobs.
4. Mount versioned API routes for desktop/mobile.
5. Add adapters for Photo and Layout.
6. Add authentication, limits, cancellation, structured logs and integration tests before public exposure.

## Compatibility rule

No existing Photo/Layout processor is rewritten during the Core rewrite. The first milestone is additive: existing UI and `/process` continue to work while new Core contracts are introduced and tested beside them.
