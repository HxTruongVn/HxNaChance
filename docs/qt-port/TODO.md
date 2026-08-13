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
- [x] Implement all main keyboard shortcuts and workshop navigation semantics
- [x] Complete WindowManager focus, native close cleanup, active state, ordering, and placement
- [ ] Port Core Resource Compatibility, Workshop Requirements, Environment Report, and About dialogs
- [ ] Port Pipeline Builder and Workshop exchange entry points
- [ ] Complete Layout menu, orientation/state dialogs, preview and save-state interactions
- [x] Complete Photo controls, preview/orientation panels, and processing options
- [x] Complete Repo Intake folder/ZIP intake, dossier, resources, scaffold, contract tests, and approval flow
- [x] Implement config/state persistence, watcher updates, missing-workshop notices, and cancellation
- [x] Add action-level, shortcut-level, theme, hierarchy, and full-workshop parity tests


## Keyboard and theme parity correction

- [x] Inject the active Core theme palette into every Workshop content widget, native Workshop window, and side panel
- [x] Remove Workshop-local hardcoded colors that override the active Core theme
- [x] Port Ctrl+` active-state/workspace transition exactly as defined by main
- [x] Port Ctrl+Shift+` reverse transition and all Workshop navigation combinations from main
- [x] Port state transition feedback, active marker, and status updates for keyboard navigation
- [x] Port Alt+key menu mnemonics and menu focus/open behavior from main
- [x] Test theme propagation across host, Workshop, and side panel
- [x] Test Ctrl backtick, reverse transition, navigation combinations, and Alt-menu keys with Qt key events


## Core, Layout and Photo UI correction

- [x] Make Core host content scrollable/adaptive when launcher, log, or status sections exceed viewport height
- [x] Make Workshop content scrollable without hard-coded fixed-height clipping
- [x] Consolidate Layout choose/add/change image controls into one clear three-action group
- [x] Remove duplicate quantity controls and keep one canonical value control with native keyboard adjustment
- [x] Add collapsible Advanced Technical Configuration section with persisted expanded state
- [x] Add Layout shortcuts for choose/add/change image, preview, print, save, run, and cancel
- [x] Make Layout Preview own the Print/Save actions and avoid duplicate always-visible preview canvas
- [x] Make Layout Cancel actually interrupt worker, clear busy state, and restore controls
- [x] Move Photo function actions near image selection and assign shortcuts
- [x] Show Photo background customization only when ReBG is enabled
- [x] Add Photo shortcut/action state tests and conditional ReBG visibility tests


## Exhaustive keyboard and Layout quantity correction

- [x] Extract every main keyboard binding, menu accelerator, mouse/keyboard combination, and context rule
- [x] Compare all extracted bindings against Qt actions and QShortcuts
- [ ] Port missing Core, Workshop, Pipeline, Layout, Photo, panel, dialog, and text-input shortcuts
- [x] Preserve Alt menu mnemonics and Ctrl/Alt/Shift combinations without collisions
- [x] Make Layout preset quantity fields wide enough to display values clearly
- [x] Define selected-preset keyboard adjustment for increase/decrease quantity
- [x] Remove duplicate quantity interaction that is not present in main
- [x] Add exhaustive key-event tests per context and selected preset


## Latest UI refinement from visual review

- [x] Restore Layout quantity cluster as visible minus/value/plus controls with readable value
- [x] Arrange Photo Face options in a compact two-column group
- [x] Arrange Photo Background and post-processing options in a compact two-column group
- [x] Add persisted theme-wide font scale setting with safe bounds and layout reflow
- [x] Add offscreen tests for quantity visibility, two-column groups, and font scaling


## Workshop-owned Preview docking

- [x] Make every Preview panel owned by its originating Workshop window, not the Host
- [x] Anchor Preview to the Workshop right edge and place it on the opposite edge when right-side space is insufficient
- [x] Keep Preview synchronized with Workshop move, resize, focus, close, and native window events
- [x] Route F2 through the active Workshop preview capability instead of Layout-only shortcut
- [x] Add ownership, fallback geometry, lifecycle, and shared F2 tests


## Core/Workshop state transition parity

- [x] Extract main state-transition contract for Core, active Workshop, session order, focus, and close behavior
- [x] Compare Qt active context/state machine against main transition semantics
- [x] Restore Core home transition without incorrectly closing or losing Workshop session state
- [x] Restore next/previous Workshop transitions, focus activation, and active marker semantics
- [x] Restore Workshop close behavior and fallback active state exactly as main
- [x] Add transition tests for Core → Workshop → Workshop → Core and closed-window edge cases


## Quantity glyph clipping correction

- [x] Prevent quantity digits from being clipped at 100% font scale
- [x] Verify quantity cluster rendering at 90%, 100%, 110%, 125%, and 150%


## Layout adjustment and automatic weight loading

- [x] Split Layout Điều chỉnh into three clear sub-sections while preserving all config fields
- [x] Trace why a Shop does not automatically request/download missing weights
- [x] Compare Qt startup/resource flow with main RuntimeManager and Model Registry flow
- [ ] Restore automatic weight/resource loading only through the canonical resource contract
- [x] Add tests for adjustment layout and Core weight intake/hash lifecycle


## Clarification: Core owns weights; one-line Layout adjustment

- [x] Keep Layout Điều chỉnh as three side-by-side sections on one row, with responsive minimum widths
- [x] Document that Shops never own the canonical weight store or downloader
- [x] Make Core intake any Shop-supplied weight, hash it with SHA-256, and register it centrally
- [ ] Make Core resolve/download/cache missing weights from canonical resource manifests
- [ ] Make Shops expose only resource requirements and consume Core-provided resolved paths
- [x] Add tests proving Shop weight files are submitted/hashed by Core before use


## Core weight no-redownload invariant

- [x] Never download a weight when the Core inventory points to an existing file with valid SHA-256
- [x] Never silently overwrite an existing filename with a different SHA-256
- [x] Treat missing file or hash mismatch as an explicit Core resource conflict/missing state
- [x] Add tests proving the downloader is not called for valid existing weights


## Checksum required on every Core weight intake path

- [x] Require expected SHA-256 for Shop-submitted weight files
- [x] Require expected SHA-256 for every Core-downloaded weight
- [x] Reject missing, malformed, or mismatched checksum before canonical registration
- [x] Add tests for valid, missing, malformed, and mismatched download checksums


## Core background automatic weight synchronization

- [x] Start Core-owned background sync after startup without blocking the UI
- [x] Report checking, skipped-existing, downloading, verifying, ready, and failed states
- [x] Download only resources absent from the canonical Core store
- [x] Verify SHA-256 before registering each downloaded resource
- [ ] Let Workshops consume resolved Core resources after sync completes
- [x] Add deterministic worker tests with mocked downloader and no-redownload assertions

