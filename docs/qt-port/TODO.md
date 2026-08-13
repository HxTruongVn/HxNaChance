# Qt-only port TODO

## Parity matrix required before more porting

- [x] Inventory host chrome and title-bar actions
- [x] Inventory theme system: themes, theme groups, switching, persistence, injection
- [x] Inventory all menu groups and every menu action
- [x] Inventory all shortcuts and context-dependent enable/disable rules
- [x] Inventory Workshop launcher and session ordering
- [x] Inventory WindowManager open/close/toggle/focus/placement behavior
- [x] Inventory each Workshop window's nested panels and dialogs
- [x] Inventory input/output/state persistence and error/loading states
- [x] Record each item in `docs/qt-port/PARITY_MATRIX.md` before implementation


## Main screenshot parity requirements

- [x] Reproduce host title/menu strip: brand, RUN, info, menu and close actions
- [x] Reproduce the ordered WORKSHOPS session launcher with numbered rows
- [x] Reproduce per-Workshop OPEN/CLOSE state and active-window indication
- [x] Reproduce side-by-side Workshop windows and WindowManager placement/order
- [x] Reproduce the main menu groups: File, Edit, Pipeline, Window, View, Tool, System, Help
- [ ] Reproduce keyboard shortcuts and Workshop switching actions
- [x] Reproduce the main status/runtime report placement and visibility

## Multi-level UI parity correction

- [x] Preserve Core host versus Workshop window hierarchy
- [x] Port Workshop launcher buttons and open/close/toggle behavior
- [x] Port separate Workshop windows instead of flattening all UI into host tabs
- [x] Port nested side panels for orientation, result and Layout preview
- [x] Preserve active workspace/window state and session ordering
- [ ] Port context-sensitive menu/shortcut behavior at each display level
- [ ] Port multi-level dialogs and About/Environment/Resource panels
- [x] Add hierarchy tests for host, Workshop windows and side panels

## Layout parity correction

- [x] Port every Layout preset from `layout_presets.json`
- [x] Support selecting multiple presets at the same time
- [x] Preserve per-preset count and formula editing
- [x] Preserve canvas size, resolution, gap, margins and `valF`
- [x] Preserve CAF mode, stroke, color and width controls
- [x] Preserve source append mode and existing output continuation
- [x] Preserve preview/render behavior and output sidecar metadata
- [x] Add parity tests for multi-preset configuration and output

## UI parity correction

- [x] Match the main window geometry, title bar and overall visual hierarchy
- [ ] Port the full adaptive menu and keyboard shortcut behavior
- [ ] Port theme switching and persisted theme selection
- [x] Port left/right panels, workspace navigation and status areas
- [ ] Port the full Photo, Layout and Repo Intake tab presentation
- [ ] Port preview, orientation, saved-state and dialog interactions
- [ ] Compare Qt screenshots against the main UI before calling the port complete


- [x] Create clean branch from `origin/main`
- [x] Make the branch's primary `NaChance.py` entrypoint launch PySide6
- [x] Keep the original main Tk entrypoint available only as an explicit legacy fallback
- [x] Keep main application logic and Workshop implementations unchanged
- [x] Add optional PySide6 dependency and entrypoint
- [x] Add Core/runtime/workshop discovery view
- [x] Add Layout tab using the existing main Layout engine
- [x] Add Photo tab using the existing main Photo engine/agent
- [x] Add Repo Intake manifest view
- [x] Add offscreen Qt smoke test
- [x] Run main regression tests
- [ ] Port remaining main UI actions and dialogs
- [ ] Port adaptive menus and shortcuts with main behavior parity
- [ ] Port orientation preview, side panels and saved-state dialogs
- [ ] Validate full desktop flows on Windows/Linux with PySide6

## Native Qt and asset fidelity correction

- [x] Verify every Qt logo/icon source against the canonical logo asset in the repository
- [x] Remove duplicated/fake Close buttons from Qt windows that already use native window controls
- [x] Keep only custom window actions that provide behavior not supplied by native Qt
- [x] Test native close, focus, active-window state, and WindowManager cleanup after closing
- [x] Document intentional differences between main's custom Tk title bar and Qt native chrome


## Full parity execution backlog

- [x] Implement theme loading, grouping, live switching, persistence, and injection
- [ ] Implement adaptive File/Edit/Pipeline/Window/View/Tool/System/Help menus from main
- [ ] Connect ContextCommandRouter providers to Qt actions and context-sensitive enablement
- [ ] Implement all main keyboard shortcuts and workshop navigation semantics
- [x] Complete WindowManager focus, native close cleanup, active state, ordering, and placement
- [ ] Port Core Resource Compatibility, Workshop Requirements, Environment Report, and About dialogs
- [ ] Port Pipeline Builder and Workshop exchange entry points
- [ ] Complete Layout menu, orientation/state dialogs, preview and save-state interactions
- [x] Complete Photo controls, preview/orientation panels, and processing options
- [x] Complete Repo Intake folder/ZIP intake, dossier, resources, scaffold, contract tests, and approval flow
- [x] Implement config/state persistence, watcher updates, missing-workshop notices, and cancellation
- [ ] Add action-level, shortcut-level, theme, hierarchy, and full-workshop parity tests


## Keyboard and theme parity correction

- [x] Inject the active Core theme palette into every Workshop content widget, native Workshop window, and side panel
- [x] Remove Workshop-local hardcoded colors that override the active Core theme
- [x] Port Ctrl+` active-state/workspace transition exactly as defined by main
- [x] Port Ctrl+Shift+` reverse transition and all Workshop navigation combinations from main
- [ ] Port state transition feedback, active marker, and status updates for keyboard navigation
- [x] Port Alt+key menu mnemonics and menu focus/open behavior from main
- [x] Test theme propagation across host, Workshop, and side panel
- [x] Test Ctrl backtick, reverse transition, navigation combinations, and Alt-menu keys with Qt key events

