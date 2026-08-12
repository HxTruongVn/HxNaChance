# Workshop Packaging Standard

## 1. Package boundary

A Workshop is a self-contained directory under `workshops/<workshop_id>/`. The directory name is the canonical identity. The Workshop may contain its own implementation, but it must communicate with NaChance through manifest metadata, host UI adapters and explicit Core/Pipeline contracts.

## 2. Required package layout

```text
workshops/<workshop_id>/
├── manifest.json                 # required discovery contract
├── __init__.py                   # required importable package
├── ABOUT.md                      # required human-facing description
├── ui.py                         # required host UI adapter for desktop
├── requirements.txt              # required, may be empty for zero-dependency Workshop
├── resources/
│   ├── capabilities_registry.json # required when capabilities exist
│   ├── model_registry.json        # required when models exist
│   └── weights_sources.json       # required when downloadable weights exist
├── weights/                       # required path convention; may be empty initially
├── tests/                         # required Workshop-local tests
└── README.md                      # required developer guide
```

A Workshop may add `engine.py`, `document.py`, `processors/`, `analyzers/`, `presets/` or other internal modules. These are private implementation details and must not be imported by Core.

## 3. Manifest minimum

The current desktop host requires a `ui` block and resolves the module/class/method named there. The following is the minimum compatible shape:

```json
{
  "workshop_id": "example",
  "workshop_name": "Example",
  "version": "1.0.0",
  "description": "What this Workshop does.",
  "ui": {
    "module": "workshops.example.ui",
    "mixin_class": "ExampleUIMixin",
    "build_method": "_build_example_tab",
    "menu_build_method": "_menu_example_content",
    "open_method": "open_example",
    "run_method": "run_example"
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

The directory name remains canonical even if a manifest declares a different ID. A mismatch must be reported as a packaging error, not used to create a second identity.

## 4. Theme contract

A Workshop must use host-provided colors, typography, spacing, window helpers, menu conventions and icon rules. It must not call `customtkinter.set_default_color_theme()` globally, replace the root window theme, or hard-code a second visual language. Workshop-specific visual accents may be declared as semantic tokens, but the host owns light/dark mode and accessibility defaults.

The current host theme vocabulary includes `bg_dark`, `bg_card`, `text_primary`, `text_secondary`, `accent`, `accent_hover`, `warning` and `success`. A future typed ThemeProvider should replace direct dictionary access without changing Workshop intent.

## 5. Resource contract

Every model, package, external binary or large data file must be declared in metadata. Runtime detection is read-only; it reports missing resources. Installation/download/verification is an explicit Core operation. Resource records should include ID, kind, version, source, checksum, optionality, local path and license.

## 6. Runtime and lifecycle contract

A Workshop must support discovery without loading heavy models. Heavy imports and model initialization happen only when the user activates the Workshop or a Job executes. A Workshop must expose readiness information and fail with structured, actionable errors when dependencies are missing.

## 7. Prohibited coupling

A Workshop must not import another Workshop directly, write into another Workshop's directory, mutate global Core state, assume the process current working directory, silently download resources during a read-only health request, or expose undocumented global singletons.

## 8. Acceptance checklist

A Workshop is accepted only when its manifest parses, its identity matches its directory, its UI adapter imports without heavy model initialization, its resource metadata validates, its readiness report is deterministic, its local tests pass, its UI follows the host theme, and the Core discovery test can add/remove it without editing Core code.
