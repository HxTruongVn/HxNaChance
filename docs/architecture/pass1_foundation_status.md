# Pass 1 foundation status

## Scope completed

Pass 1 follows the required order: Model Registry, RuntimeManager, test suite, Workshop/Identity contracts and legacy bridge review.

The Core now owns `core/model_registry.py` as the typed registry contract. `config/model_registry.py` remains a compatibility facade for existing Photo Workshop callers. It keeps the old mapping functions but delegates parsing and validation to the Core registry.

`RuntimeManager` reads Workshop-owned registry data through the Core loader, reports the configured weights directory correctly and retains explicit legacy capability aliases for existing Photo tests and UI callers. The aliases are compatibility views, not the new ownership model.

`core/identity.py` is the canonical Workshop identity contract. The directory name is the canonical ID. A manifest mismatch is visible as a warning and cannot create a second identity. `WorkshopWindow.__getattr__` is documented as a legacy bridge; new code must use explicit Core services/contracts.

## Verification

```text
pytest -q
83 passed, 1 skipped
```

The skipped test is an existing optional test condition. No test failed in the current environment. OpenCV was installed only to allow the existing Photo Workshop integration tests to collect and run; no Photo model or weight was downloaded.

## Next gate

Pass 2 must not begin until this foundation remains green. The next work may extend Workshop Contract, Resource Warehouse and approved transport, but changes must preserve the typed Registry, RuntimeManager report and Identity Contract. Any change to legacy aliases must include a migration note and targeted tests.
