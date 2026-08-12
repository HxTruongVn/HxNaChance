# Backend rewrite status

## Completed in this pass

- Added `core/contracts.py` with explicit Runtime, Resource, Workshop, Pipeline, Session and Job contracts.
- Added `core/workshop_registry.py` for deterministic manifest discovery and visible disabled descriptors on manifest errors.
- Added `core/runtime_service.py` to adapt the existing RuntimeManager into a read-only Core report.
- Added `api/core_routes.py` and mounted four read-only `/api/v1` Runtime/Workshop endpoints.
- Added tests and smoke scripts for the new registry, runtime adapter and API router.
- Added `docs/architecture/backend_rewrite_plan.md` and `docs/architecture/api_core.md` as the implementation boundary and API reference.

## Verification status

The source ZIP environment does not have `pytest` installed (`/usr/bin/python: No module named pytest`), so the selected pytest suite could not run in this environment. The new Core smoke tests and Python compile checks pass. The full pytest suite should run after installing `setup/requirements-dev.txt` or the project development requirements.

No existing Photo/Layout implementation was rewritten in this pass; the changes are additive and deliberately form the first Core contract layer.
