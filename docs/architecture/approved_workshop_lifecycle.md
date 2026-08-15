# Approved Workshop lifecycle

## Boundary

NaChance does not watch arbitrary repositories. External repositories belong to `onboarding` quarantine until their intake report, resource claims, adapter plan and contract tests are complete.

## State flow

```text
EXTERNAL
  → QUARANTINED
  → INSPECTED
  → PLAN_SELECTED
  → RESOURCE_REGISTERED
  → ADAPTER_BUILT
  → CONTRACT_TESTED
  → APPROVED
  → TRANSPORTED
  → ENABLED / MANAGED
```

The transport step copies the approved package into the managed Workshop store and writes `.nachance/approval.json` plus `.nachance/files.sha256`. The marker records the case, version, approver, adapter mode, resource IDs and approval timestamp.

## Managed watcher

`app/workshop_watcher.py` scans only directories containing a valid approval marker. It ignores intake and unapproved directories. It compares the approved file snapshot with the current package. A missing managed directory is a removal event. Any file or manifest change invalidates the approval snapshot and requires a new intake review.

The watcher does not hot-accept changes, execute new code or update the active session. It reports a change so Core can stop/revoke the package and require a fresh approved transport.

## Resource ownership

Transport moves the Workshop package into managed storage. Resource files are not trusted merely because they are present in the package: their Warehouse records, version and SHA-256 must still resolve before execution. A Workshop is enabled only when its approval marker and required resource readiness both pass.
