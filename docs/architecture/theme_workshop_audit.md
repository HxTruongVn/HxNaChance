# Theme, Core–Workshop coupling and external Workshop audit

## Executive assessment

NaChance has a coherent platform direction: Core owns bootstrap, runtime checks, discovery, resource inspection, pipeline persistence and host navigation; Workshops own domain behavior. The strongest existing contract is metadata-first discovery through `workshops/*/manifest.json`. The weakest area is that the current desktop host still couples discovery to importable UI mixins and method names, while resource metadata, provisioning and runtime readiness are spread across several modules.

The current theme is serviceable and recognizable, but it is not yet a typed theme contract. `app/main_ui.py` centralizes colors and icon setup, while Workshop UI code consumes host mixins and direct color dictionaries. This is adequate for the current desktop application, but a future mobile/web Reception should move to semantic tokens and a ThemeProvider so a Workshop declares intent rather than platform-specific colors.

## Theme evaluation

| Area | Current state | Assessment | Required direction |
|---|---|---|---|
| Color ownership | Central colors in `app/main_ui.py` and UI mixins | Good principle, weak typing | Introduce `ThemeTokens` with semantic roles: surface, panel, text, accent, warning, success, danger, focus. |
| Workshop consistency | Workshops use host UI helpers but can reach direct CustomTkinter details | Partial | Give Workshops a narrow `WorkshopUIContext`; prohibit global theme mutation. |
| Light/dark behavior | Host controls the desktop theme | Good for desktop | Preserve intent tokens for mobile/web and keep platform rendering in Reception. |
| Icons/assets | Host loads a central app icon; Workshop assets are local | Partial | Define icon sizes, contrast, licensing and fallback rules in the Workshop contract. |
| Layout/accessibility | Mixins and host windows provide conventions | Partial | Standardize spacing, minimum sizes, focus order, keyboard navigation and text scaling. |
| Mobile readiness | No shared theme contract with the Expo prototype | Not ready | Do not port Photo screens as the product shell; build a Core Reception shell first. |

## Core–Workshop connection points

| Connection | Current mechanism | Coupling risk | Recommended contract |
|---|---|---|---|
| Identity | Directory name is canonical; manifest describes the package | Low if enforced | `workshop_id` must equal the directory identity; mismatch is a visible validation error. |
| Discovery | `app/workshop_discovery.py` scans manifests and imports UI mixins | Medium | Separate metadata discovery from UI import; heavy modules load only after activation. |
| UI | Manifest names module, mixin and build methods | High | Keep a compatibility adapter now; migrate to `WorkshopUIAdapter` protocol later. |
| Requirements | `requirements.txt`, manifest fields and `app/workshop_requirements.py` | Medium | One normalized requirement schema for packages, models, binaries, RAM, VRAM and capabilities. |
| Resources | `model_registry`, `weights_sources`, `weights/` and RuntimeManager | Medium/high | Introduce `ResourceDescriptor` and explicit resolve/verify lifecycle. |
| Capabilities | Workshop capability registries are inspected by RuntimeManager | Medium | Capability IDs must be namespaced, typed and tied to readiness predicates. |
| Pipeline | `PipelineStore` persists Workshop steps and snapshots | Low/medium | Pipeline stores references and state; it never imports processor internals. |
| Execution | Workshop-specific methods and Photo API engine | High | Core creates Session/Job; a Workshop adapter executes one bounded operation. |
| Errors | Console/UI messages and HTTP errors vary | High | Use stable error codes, details and request IDs across desktop/API/mobile. |
| Theme | Host colors/helpers are consumed by Workshop UI | Medium | Workshop receives a theme/context object and never changes global theme state. |

## Minimum structure for an external Workshop

```text
workshops/<workshop_id>/
├── manifest.json
├── __init__.py
├── ABOUT.md
├── README.md
├── ui.py
├── requirements.txt
├── resources/
│   ├── capabilities_registry.json
│   ├── model_registry.json
│   └── weights_sources.json
├── weights/
└── tests/
```

`engine.py`, `document.py`, `processors/`, `analyzers/`, `presets/` and `assets/` are optional domain-specific additions. The Workshop may add any internal structure, but Core must interact only through the manifest, normalized resource/capability metadata, the UI adapter and the execution adapter.

## Minimum manifest contract

```json
{
  "workshop_id": "example",
  "workshop_name": "Example",
  "version": "1.0.0",
  "description": "A concise description.",
  "ui": {
    "module": "workshops.example.ui",
    "mixin_class": "ExampleUIMixin",
    "build_method": "_build_example_tab"
  },
  "capabilities_required": [],
  "capabilities_optional": [],
  "resources": {
    "requirements_file": "requirements.txt",
    "capabilities_file": "resources/capabilities_registry.json",
    "model_registry_file": "resources/model_registry.json",
    "weight_sources_file": "resources/weights_sources.json",
    "weights_directory": "weights"
  },
  "about_file": "ABOUT.md"
}
```

Optional UI methods may be declared for menus, opening, running and window actions, but the host must validate that a declared method exists and report a structured error if it does not.

## Acceptance checklist

A repo becomes a compatible Workshop only when its directory identity and manifest agree; metadata parses deterministically; the UI adapter imports without loading heavy models; resources and capabilities are declared; readiness can be calculated without downloading; explicit provisioning records versions and checksums; execution is represented by a Session/Job; the UI consumes host theme tokens; the Workshop does not import another Workshop; tests pass in isolation; and removal of the Workshop requires no Core code edit.

## Main recommendation

The next engineering milestone should be a `WorkshopAdapter` protocol plus a typed `ThemeTokens`/`WorkshopUIContext`. Keep the current manifest and mixin adapter as a compatibility layer. This creates a stable bridge for external repos without forcing every Workshop to know whether it is running in CustomTkinter, a web client or the mobile Reception.
