# NaChance State & Workflow Contract

**Status: LOCKED — architectural baseline**

This document defines the Core meaning of Workflow, State, History, Checkpoint,
Artifact, Capability and Environment.

The contract is Workshop-agnostic. Photo, Code, Audio and future Workshops must
adapt to this contract instead of defining their own incompatible state model.

---

## 1. Core model

```text
Workflow
   │
   ├── State 0
   │     ↓
   ├── State 1
   │     ↓
   ├── State 2  ← current
   │     ↓
   └── State 3
```

A **State** is the complete restorable condition of a Workflow at a point in
time.

A State is not synonymous with an image, source file, or final output.

---

## 2. Workflow

A Workflow describes the process being executed.

It contains, conceptually:

```text
workflow_id
workshop_id
definition/version
steps
inputs
parameters
capabilities
environment requirements
```

A Workflow may be executed more than once.

---

## 3. State

A State represents the condition of a Workflow that can be restored.

Minimum conceptual structure:

```text
State
├── workflow identity
├── workshop identity
├── current step
├── inputs
├── parameters
├── artifacts
├── execution information
├── environment requirements
└── metadata
```

The Core must not assume that the primary artifact is an image.

Examples:

```text
Photo Workshop → image/mask/metadata
Code Workshop  → source tree/test results/build artifacts
Audio Workshop → audio/project/metadata
```

---

## 4. History

History records movement between states.

```text
S0 → S1 → S2 → S3
          ↑
       current
```

Undo and Redo navigate History.

History is not the same as saved State.

### Undo

Moves the active Workflow to a previous restorable State.

### Redo

Moves it forward when a later State is still available.

A Workshop may expose only the history capabilities it can safely restore.

---

## 5. Checkpoint

A Checkpoint is a State deliberately retained as a durable recovery/transfer
point.

```text
S0 → S1 → S2 → S3
          ★
       checkpoint
```

Not every History entry must become a Checkpoint.

Checkpoints are useful for:

- long-running workflows;
- expensive execution;
- branching;
- transfer between machines/shops;
- resuming work later.

---

## 6. Ctrl+S semantics

`Ctrl+S` in a stateful Workshop means:

> **Save the current Workflow State.**

It does not mean "save the latest output regardless of where the user currently
is in History."

Example:

```text
Execute:
S0 → S1 → S2 → S3 → S4

Undo:
S4 → S3 → S2

Ctrl+S
```

The saved State is **S2**.

Later States must not silently replace the saved current State.

The saved bundle may retain compatible history/checkpoints so the workflow can
continue or redo where supported.

---

## 7. Export Output

Saving State and exporting Output are different operations.

```text
Ctrl+S
    ↓
Workflow State / Checkpoint

Export
    ↓
Artifact for external use
```

For example:

```text
Photo:
Save State → workflow can continue
Export PNG → finished image

Code:
Save State → workflow can continue
Export/Package → source/build deliverable
```

---

## 8. Artifact

An Artifact is a concrete object produced or consumed by a Workflow.

Examples:

```text
image.png
mask.png
source/
test-report.json
build.zip
audio.wav
```

Artifacts belong to State/Workflow context.

The Core must treat artifacts generically.

---

## 9. Capability

A Workshop declares what it can do.

Examples:

```text
history.undo
history.redo
state.save
state.load
checkpoint.create
artifact.export
workflow.resume
state.transfer
```

Edit menus and shortcuts must be derived from available capabilities where
appropriate.

If a Workshop cannot safely perform Undo, Undo must not be presented as
available merely because the global UI has Ctrl+Z.

---

## 10. Environment

A State may require an execution environment.

Examples:

```text
OS
Python/runtime version
GPU/backend
dependencies
models/weights
plugins
tools
configuration
```

Environment requirements are metadata of the Workflow/State.

They are not themselves the State's business data.

Before resuming a transferred State:

```text
State
  ↓
Environment Resolver
  ↓
compatible?
 ├── yes → Resume
 └── no  → report missing requirements
```

NaChance must not silently substitute incompatible dependencies.

---

## 11. Transfer between Workshops

A saved State may be transferred only when the receiving Workshop declares
compatibility.

```text
Workshop A
    ↓
Save State
    ↓
NaChance State Package
    ↓
Workshop B
    ↓
Capability + environment check
    ↓
Resume
```

The package should carry enough identity/version information for the receiving
Workshop to decide whether it can restore it.

Cross-Workshop transfer is therefore a **contracted capability**, not an
assumption that every Workshop can open every State.

---

## 12. Branching

Undo followed by a new operation creates a branch.

```text
S0 → S1 → S2 → S3
          │
          └→ S2a → S2b
```

A saved Checkpoint may serve as the root of a new branch.

The Core must not destroy a saved Checkpoint merely because the active History
branch changed.

---

## 13. Workshop boundary

Workshop-specific code belongs behind an adapter.

```text
NaChance Core
│
├── Workflow
├── State
├── History
├── Checkpoint
├── Artifact
├── Capability
└── Environment
        │
        ▼
Workshop Adapter
        │
   ┌────┼────┐
 Photo Code Audio
```

The Core must not contain Photo-specific assumptions.

---

## 14. UI consequences

The UI is a projection of the active Workshop capabilities.

Example:

```text
Edit
├── Undo       Ctrl+Z   ← if available
├── Redo       Ctrl+Y   ← if available
└── Save State Ctrl+S   ← if state.save is available
```

`File → Export...` is separate from `Ctrl+S`.

`Ctrl+O` opens an input/resource.

A future `Open Saved State` operation loads a State package, subject to
Workshop compatibility.

---

## 15. Implementation rule

When adding a new Workshop:

1. Do not create a private incompatible State model.
2. Declare its capabilities.
3. Declare its artifacts.
4. Declare environment requirements.
5. Implement State serialize/restore adapter.
6. Implement History adapter where supported.
7. Implement checkpoint support where meaningful.
8. Register commands through Core.

The UI should consume these declarations instead of hard-coding Workshop names.

---

## 16. Architectural decision

This contract is the baseline for subsequent implementation.

Do not expand Photo-specific persistence into Core before the generic State
contract is implemented.

The next implementation layer is:

```text
Core State
    ↓
History / Checkpoint
    ↓
Command / Shortcut
    ↓
UI
    ↓
Workshop adapters
```
