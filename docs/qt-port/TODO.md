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
- [x] Reproduce keyboard shortcuts and Workshop switching actions
- [x] Reproduce the main status/runtime report placement and visibility

## Multi-level UI parity correction

- [x] Preserve Core host versus Workshop window hierarchy
- [x] Port Workshop launcher buttons and open/close/toggle behavior
- [x] Port separate Workshop windows instead of flattening all UI into host tabs
- [x] Port nested side panels for orientation, result and Layout preview
- [x] Preserve active workspace/window state and session ordering
- [x] Port context-sensitive menu/shortcut behavior at each display level
- [x] Port multi-level dialogs and About/Environment/Resource panels
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
- [x] Port the full adaptive menu and keyboard shortcut behavior
- [x] Port theme switching and persisted theme selection
- [x] Port left/right panels, workspace navigation and status areas
- [x] Port the full Photo, Layout and Workshop Onboarding tab presentation
- [x] Port preview, orientation, saved-state and dialog interactions
- [ ] Compare Qt screenshots against the main UI before calling the port complete


- [x] Create clean branch from `origin/main`
- [x] Make the branch's primary `NaChance.py` entrypoint launch PySide6
- [x] Keep the original main Tk entrypoint available only as an explicit legacy fallback
- [x] Keep main application logic and Workshop implementations unchanged
- [x] Add optional PySide6 dependency and entrypoint
- [x] Add Core/runtime/workshop discovery view
- [x] Add Layout tab using the existing main Layout engine
- [x] Add Photo tab using the existing main Photo engine/agent
- [x] Add Workshop Onboarding manifest view
- [x] Add offscreen Qt smoke test
- [x] Run main regression tests
- [x] Port remaining main UI actions and dialogs
- [x] Port adaptive menus and shortcuts with main behavior parity
- [x] Port orientation preview, side panels and saved-state dialogs
- [ ] Validate full desktop flows on Windows/Linux with PySide6

## Native Qt and asset fidelity correction

- [x] Verify every Qt logo/icon source against the canonical logo asset in the repository
- [x] Remove duplicated/fake Close buttons from Qt windows that already use native window controls
- [x] Keep only custom window actions that provide behavior not supplied by native Qt
- [x] Test native close, focus, active-window state, and WindowManager cleanup after closing
- [x] Document intentional differences between main's custom Tk title bar and Qt native chrome


## Full parity execution backlog

- [x] Implement theme loading, grouping, live switching, persistence, and injection
- [x] Implement adaptive File/Edit/Pipeline/Window/View/Tool/System/Help menus from main
- [x] Connect ContextCommandRouter providers to Qt actions and context-sensitive enablement
- [x] Implement all main keyboard shortcuts and workshop navigation semantics
- [x] Complete WindowManager focus, native close cleanup, active state, ordering, and placement
- [x] Port Core Resource Compatibility, Workshop Requirements, Environment Report, and About dialogs
- [x] Port Pipeline Builder and Workshop exchange entry points
- [x] Complete Layout menu, orientation/state dialogs, preview and save-state interactions
- [x] Complete Photo controls, preview/orientation panels, and processing options
- [x] Complete Workshop Onboarding folder/ZIP intake, dossier, resources, scaffold, contract tests, and approval flow
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
- [x] Port missing Core, Workshop, Pipeline, Layout, Photo, panel, dialog, and text-input shortcuts
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
- [x] Restore automatic weight/resource loading only through the canonical resource contract
- [x] Add tests for adjustment layout and Core weight intake/hash lifecycle


## Clarification: Core owns weights; one-line Layout adjustment

- [x] Keep Layout Điều chỉnh as three side-by-side sections on one row, with responsive minimum widths
- [x] Document that Shops never own the canonical weight store or downloader
- [x] Make Core intake any Shop-supplied weight, hash it with SHA-256, and register it centrally
- [x] Make Core resolve/download/cache missing weights from canonical resource manifests
- [x] Make Shops expose only resource requirements and consume Core-provided resolved paths
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
- [x] Let Workshops consume resolved Core resources after sync completes
- [x] Add deterministic worker tests with mocked downloader and no-redownload assertions


## Theme propagation to open Workshops

- [x] Propagate Core theme changes to every open Workshop immediately
- [x] Propagate the same theme and font scale to Workshop-owned Preview/Side Panel windows
- [x] Preserve each Workshop's current state while applying the new stylesheet
- [x] Add tests for idle and active Workshop theme updates


## Hotkey reliability and routing

- [x] Inventory every QAction, QShortcut, widget shortcut, keyPressEvent, mnemonic, and focus scope
- [x] Remove duplicate bindings and route global commands through one application-level dispatcher
- [x] Keep text-input exceptions deterministic for Ctrl+S/Z/Y and related commands
- [x] Verify F2, Ctrl+R, grave navigation, Esc, mnemonics, and Layout/Photo shortcuts with real key events
- [x] Add regression tests for focus changes and repeated key presses


## Core sequential pipeline contract

- [x] Define the Pipeline input as an explicit initial source selected by Core
- [x] Configure the active Shop before adding its snapshot as a Pipeline step
- [x] Store each step's complete Workshop configuration at insertion time
- [x] Pass Shop N output as Shop N+1 input
- [x] Continue sequential execution until the final configured Shop
- [x] Stop and report the exact failing step when a Shop has no receiver or output
- [x] Add chain tests proving input → Shop A → output A → Shop B → output B


## Extended pipeline chain regression tests

- [x] Add a pipeline handoff test with more than three sequential steps
- [x] Add a repeated-workshop test with distinct snapshots for each occurrence
- [x] Verify outputs remain ordered and each repeated step keeps its own snapshot


## Qt UI coverage report

- [x] Run the complete Qt UI test suite with coverage enabled
- [x] Export detailed HTML, XML, and Markdown coverage reports
- [x] Include per-file and per-module coverage summary


## Shop manifest auto-sync correction

- [x] Add verified SHA-256 metadata to every Photo weight manifest entry
- [x] Confirm Core reads Shop manifests through `setup_models.MODELS`
- [x] Confirm existing canonical weights are adopted without download
- [x] Confirm missing Photo weights are downloaded and verified by Core
- [x] Add regression test preventing checksum-less Shop manifest entries


## Corrected repo intake and participation gate

- [x] Allow incoming Shop manifests without pre-supplied SHA-256
- [x] Stage repo resources in Core intake quarantine and compute discovered SHA-256
- [x] Preserve optional expected checksum when a repo provides one, but do not require it for intake
- [x] Promote discovered checksum/resource to the canonical gate only after intake resource test passes
- [x] Add explicit test-room states: intake, hashing, testing, passed, failed, approved
- [x] Grant Workshop participation permission only after Shop and resource tests pass
- [x] Prevent failed or untested Shop resources from entering the canonical store or Pipeline



## Workshop Onboarding operational setup

- [ ] Document Workshop Onboarding directory roles: incoming, quarantine, test-room, canonical, rejected, audit
- [x] Define the Core resource intake adapter for local files, ZIP repositories, and source URLs
- [ ] Define manifest-to-resource claim normalization when SHA-256 is absent
- [ ] Add durable intake case and resource state persistence with recovery after restart
- [ ] Add resource test contracts and an explicit approval/participation command
- [ ] Block Workshop discovery and Pipeline insertion unless participation permission is present
- [ ] Add operator-facing Workshop Onboarding setup and status documentation
- [ ] Add end-to-end smoke test from repository submission to approved Workshop participation
- [x] Add downloader integration that stages URL resources in quarantine before testing
- [ ] Add cleanup/retention policy for rejected and expired quarantine cases
- [ ] Add audit records for checksum, test result, approver, and transport events


## Approved managed Workshop package

- [x] Define the complete approval marker and managed package file set
- [x] Write approval metadata, participation permission, manifest snapshot, and resource registry during transport
- [x] Make WorkshopWatcher reject packages with missing or invalid approval artifacts
- [x] Make watcher snapshot include the approval/resource metadata files
- [x] Add tests for approved package acceptance and incomplete package rejection
- [x] Document the post-approval package layout and watcher lifecycle


## Manifest weight link intake

- [x] Inspect and document the existing Workshop weight manifest format
- [x] Normalize `weights_sources.json` entries into Workshop Onboarding resource claims
- [x] Preserve source URL, method, filename, optional size and optional SHA-256 metadata
- [x] Make Workshop Onboarding include discovered weight links in its intake report/profile
- [x] Route normalized weight claims through CoreResourceDownloader and resource-gate/intake
- [x] Add tests using the existing sample Workshop weight manifest format


## External Workshop Onboarding reference review

- [x] Read and summarize the supplied reference content
- [x] Compare reference resource/manifest assumptions with current Core contracts
- [x] Apply only compatible reference improvements
- [x] Record rejected or deferred ideas and reasons
- [x] Add regression tests for any adopted behavior


## Repository audit

- [ ] Audit Core/Workshop Onboarding boundary and package placement
- [ ] Audit resource downloader, checksum, canonical and no-redownload paths
- [ ] Audit approval marker, watcher acceptance and post-approval mutation detection
- [ ] Audit ReviewWorkflow state transitions and restart/persistence behavior
- [ ] Audit Workshop/Pipeline participation gates
- [ ] Audit tests, generated artifacts, stale docs and repository hygiene
- [x] Record verified findings with severity and recommended fix


## Remediation plan

- [ ] Define one shared participation/managed-package acceptance policy
- [ ] Apply the policy to WorkshopDiscovery and Pipeline Builder
- [ ] Validate approval marker identity, participation file, resource registry, and snapshot together
- [ ] Add built-in Workshop trust policy without weakening external repo quarantine
- [ ] Move canonical resources to collision-safe content-addressed or resource-scoped paths
- [ ] Add atomic writes and locking for resource-gate registry
- [ ] Add safe recovery for corrupt/unknown resource states
- [ ] Add ReviewCase rehydration after Core restart
- [ ] Route legacy weight downloads through CoreResourceDownloader/resource-gate
- [ ] Run complete regression and update architecture/runbook documentation


## Scope correction: Pipeline is a feature branch

- [ ] Document Pipeline as an optional feature branch, not the parent of NaChance
- [ ] Keep Core lifecycle and Workshop lifecycle independent from Pipeline
- [ ] Apply participation checks only at Pipeline add/run boundaries
- [ ] Ensure Workshop Onboarding approval does not imply that a Pipeline must exist
- [ ] Remove audit wording that treats Pipeline as the system-wide acceptance layer


## Workshop Onboarding migration

- [x] Inventory all workshop-onboarding directory, module, import, manifest and documentation references
- [x] Create canonical `workshops/onboarding` package structure
- [x] Move or re-export Workshop Onboarding domain modules under workshop_onboarding
- [x] Keep a temporary compatibility bridge for old workshop-onboarding imports and paths
- [x] Update Workshop IDs, labels and discovery metadata without changing persisted case IDs unexpectedly
- [x] Update tests and add old-import/new-import compatibility coverage
- [x] Update architecture, setup, audit and Qt-port documentation
- [x] Run full regression suite and verify no stale production imports remain


## Short Workshop naming convention

- [ ] Define canonical short names: `Ws_Onboarding`, `Ws_Layout`, `Ws_Photo`
- [ ] Separate filesystem/module identifiers from user-facing display names
- [ ] Add legacy ID/import mapping for `workshop_onboarding`, `workshop_onboarding`, `layout`, and `photo`
- [ ] Update manifests, discovery, launcher and pipeline references to the short convention
- [ ] Preserve loading of old state bundles and saved pipeline snapshots
- [ ] Add naming convention documentation and regression coverage


## Naming rule correction

- [x] Restore display labels/window titles to the canonical Workshop folder name
- [x] Keep `Ws_` only for internal module, contract, registry, or variable terminology
- [x] Remove `short_name` from user-facing discovery output or treat it as non-display metadata
- [x] Update naming documentation and tests to assert folder-derived display names


## Roadmap re-check

- [ ] Freeze the current Core/Workshop/Onboarding boundaries before further naming refactors
- [ ] Define and implement one acceptance policy for built-in and externally onboarded Workshops
- [ ] Close WorkshopDiscovery acceptance gaps without making Pipeline the system-wide gate
- [ ] Close Pipeline add/run checks as an optional feature branch
- [ ] Stabilize resource canonical storage and atomic persistence
- [ ] Add ReviewCase restart recovery
- [ ] Unify legacy weight sync with Core downloader
- [ ] Perform physical Qt parity validation after service contracts stabilize
- [ ] Defer mobile/backend expansion until desktop Core contracts are stable


## Workshop acceptance policy implementation

- [x] Define built-in, managed-approved and unaccepted Workshop classifications
- [x] Implement shared acceptance validator with explicit rejection reasons
- [x] Add acceptance tests for built-in, approved package, incomplete package and mutated package
- [x] Apply acceptance policy to WorkshopDiscovery without requiring Pipeline
- [x] Apply acceptance check when adding a Workshop to a Pipeline
- [x] Apply acceptance check again immediately before running a Pipeline
- [x] Preserve independent Core and Workshop lifecycle behavior
- [x] Update audit/setup documentation and run full regression


## Remove legacy workshop_onboarding terminology

- [ ] Inventory all remaining `workshop_onboarding` references and classify them as canonical, compatibility, historical or generated
- [ ] Rename canonical UI methods, state fields and user-facing labels to Workshop Onboarding terminology
- [ ] Remove `workshop_onboarding` from current documentation and manifests
- [ ] Move legacy imports/state migration into an explicitly isolated migration module
- [ ] Remove active `core.review` and `workshops/onboarding` compatibility paths after migration policy is defined
- [ ] Add tests proving canonical code has no active workshop_onboarding dependency
- [ ] Run full regression and stale-reference audit


## Internal Ws terminology correction

- [x] Keep canonical folder and display names unchanged
- [x] Use `Ws_Onboarding`, `Ws_Layout`, and `Ws_Photo` only in detailed internal descriptions and technical identifiers
- [x] Keep UI labels/window titles derived from folder names
- [x] Apply the same rule to contracts, registries, class descriptions and technical documentation
- [x] Add regression coverage for folder/display versus internal naming separation


## Canonical onboarding identity correction

- [x] Rename canonical Workshop folder to `workshops/onboarding`
- [x] Set folder-derived display name to `onboarding`
- [x] Set internal Workshop ID to `Ws_onboarding`
- [x] Add migration mapping from `workshop_onboarding` and earlier legacy names
- [x] Update discovery, launcher, state, Pipeline and approval identity references
- [x] Update tests and documentation to use the corrected mapping


## Canonical resource storage hardening

- [x] Audit current ResourceTestGate/ResourceWarehouse canonical paths and registry records
- [x] Design content-addressed canonical blob layout with legacy read compatibility
- [x] Store resource blobs by verified SHA-256 without basename collisions
- [x] Update downloader promotion and registry resolution to the new blob path
- [x] Add collision, duplicate-content and no-redownload regression tests
- [x] Document canonical storage migration and recovery behavior


## Workflow terminology clarification

- [ ] Define Pipeline as the optional user-facing feature area
- [ ] Define Workflow/Workshop Chain as the task-connection domain model
- [ ] Separate chain definition, execution engine and Pipeline UI terminology
- [ ] Add canonical names and compatibility aliases for current pipeline code
- [ ] Update architecture and user-facing documentation without changing runtime behavior prematurely
- [ ] Add tests for chain semantics: output of one Workshop becomes input of the next


## Workflow Builder UI ownership

- [ ] Define Workflow Builder as the sole owner while a step is being configured
- [ ] Create a draft Step Configuration Session independent from the live Workshop window
- [ ] Prevent opening/activating the live Workshop runtime during add-step configuration
- [ ] Capture immutable Workshop snapshot only when the user confirms Add Step
- [ ] Allow repeated use of one Workshop through separate draft sessions and snapshots
- [ ] Keep Workshop runtime state and Workflow draft state separate
- [ ] Add tests for UI ownership, cancel, confirm, duplicate Workshop steps and snapshot isolation


## Repository bloat and risk audit

- [x] Measure file counts, directory counts and largest files by category
- [x] Classify runtime, compatibility, test, documentation and generated artifacts
- [x] Detect duplicate modules, stale renamed paths and duplicate manifests
- [x] Check import/discovery/packaging risks caused by extra directories
- [x] Check tracked generated files, coverage reports, caches and temporary outputs
- [x] Record safe cleanup candidates without deleting before review
- [x] Save a repository risk audit with cleanup priorities


## PySide6-only runtime migration

- [ ] Inventory Tkinter entrypoints, imports and runtime dependencies
- [ ] Map remaining Tkinter logic to PySide6 implementations or identify missing parity
- [ ] Make PySide6 the sole production entrypoint
- [ ] Mark Tkinter files as historical/temporary before removal
- [ ] Remove Tkinter runtime imports and stale launch paths
- [ ] Update packaging, startup docs and test commands to PySide6
- [ ] Run full parity/regression and native startup checks before deleting Tkinter


## Early Mixin migration

- [x] Inventory every Mixin class, caller and owned state
- [x] Define replacement ownership for theme, menu, shortcuts, side panels and Workflow
- [x] Convert low-risk stateless UI helpers to composition components
- [ ] Introduce WorkshopUiAdapter instead of Workshop UI Mixins
- [ ] Introduce WorkflowBuilder/WorkflowRunner controllers instead of PipelineMixin orchestration
- [ ] Remove Mixin inheritance from the PySide6 main window
- [ ] Delete obsolete Mixin modules after import and test scans are clean
- [ ] Update architecture docs and run full Qt regression


## First Mixin replacement implementation

- [x] Create QtWidgetFactory for shared section/header/control helpers
- [ ] Create ThemeController/ThemeState boundary for PySide6 theme ownership
- [ ] Create ConfigStore boundary for persisted settings
- [x] Replace direct Mixin-style helper ownership in the selected Qt paths
- [x] Add compatibility tests without importing Tkinter in the Qt path
- [x] Run focused and full Qt regression before removing legacy modules


## Next migration: Theme and Config

- [x] Inventory ThemeMixin, ConfigMixin and all current Qt theme/config paths
- [x] Create ThemeState/ThemeController without Tkinter dependency
- [x] Create ConfigStore for persisted settings and font scaling
- [x] Connect Qt host to the new theme/config boundaries
- [x] Replace relevant Mixin callers and preserve compatibility during transition
- [x] Add focused tests for theme switching, scaling and config persistence
- [x] Run full regression before moving to Menu/Workflow migration


## Theme and Config composition migration

- [x] Inventory ThemeMixin, ConfigMixin and all current Qt theme/config paths
- [x] Create ThemeController without Tkinter dependency
- [x] Create ConfigStore for persisted settings and font scaling
- [x] Connect Qt host to the new theme/config boundaries
- [x] Replace relevant Mixin callers and preserve compatibility during transition
- [x] Add focused tests for theme switching, scaling and config persistence
- [x] Run full regression before moving to Menu/Workflow migration
- [ ] Refactor remaining MenuBar, SidePanel and Orientation mixins into controllers
- [x] Implement draft Workflow Configuration Sessions
- [ ] Route legacy weight synchronization through CoreResourceDownloader and ResourceTestGate
- [ ] Remove Tkinter bridge after native Qt validation


## Main parity audit: naming, storage and live preview

- [x] Compare main and Qt naming conventions for workshops, resources, snapshots and output files
- [x] Compare main and Qt file storage directories and generated filename rules
- [x] Identify every preview UI and its option-change/update path
- [x] Make preview refresh react to all relevant option changes without reopening the workshop
- [x] Add tests for naming/storage parity and live preview updates


## Business output storage parity

- [x] Read the main save helper and document drive/folder selection rules
- [x] Preserve business-time directory creation instead of using Workshop names as folders
- [x] Remove fixed `Pictures/ANHTHE` and Workshop-derived output paths from Qt save dialogs where main does not use them
- [x] Keep Layout sidecar metadata under the same business output path
- [x] Add tests for selected drive, timestamp folders and repeated saves


## Interactive preview fidelity

- [x] Map every Layout and Photo option to a preview invalidation event
- [x] Make Layout preview rebuild from the latest state and update the open panel content
- [x] Make Photo preview show loading, latest revision and rendered result for the latest options
- [x] Prevent stale preview results from replacing newer interaction state
- [ ] Add interaction-level tests for open preview panels


## Core architecture hardening

- [x] Make NaChance bootstrap gate on Core readiness, never Workshop presence
- [x] Add and use `setup/core_requirements.txt` for Core dependency checks
- [x] Ensure Workshop requirements are checked independently from Core requirements
- [x] Enforce one Core-owned `weights/` root and reject Workshop weight stores
- [x] Define Core discovery/validation/description ownership and App UI loading boundary
- [x] Introduce normalized ResourceDescriptor with id, kind, required, version, checksum, paths and state
- [x] Mark legacy aliases as compatibility-only and prevent new logic from depending on them
- [x] Run complete Core regression before returning to UI/shortcut work


## Full suite after Core/Workshop dependency separation

- [x] Inventory all test files and identify Qt/native/dependency-sensitive groups
- [x] Run full Python compile and pytest suite
- [x] Separate code regressions from missing optional/native dependencies
- [x] Fix Core/Workshop separation regressions without restoring coupling
- [x] Re-run full suite and record exact pass/fail/skip counts


## Unified Core weights store

- [x] Inventory all manifest/runtime/downloader weight paths
- [x] Remove Workshop-owned weight directory declarations from all manifests
- [x] Normalize every weight resource path to `NaChance/weights/`
- [x] Preserve checksum/source metadata while updating manifests
- [x] Add invariant tests rejecting Workshop-local weight stores
- [x] Run checksum, RuntimeManager, downloader and regression tests


## Workshop Discovery boundary

- [x] Inventory Core registry and App discovery responsibilities
- [x] Make Core the sole discover/validate/describe authority
- [x] Make App load UI only from Core-approved descriptors
- [x] Preserve folder-based display naming and deterministic session ordering
- [x] Add tests proving invalid manifests never reach UI import
- [x] Run Workshop discovery and full regression suite


## Resource Contract validation

- [x] Inventory resource declarations from manifests, registries and weight sources
- [x] Normalize every resource into one ResourceDescriptor schema
- [x] Validate resource IDs, kinds, versions, checksums and safe paths
- [x] Resolve Core-owned resources to READY, MISSING or INVALID
- [x] Preserve legacy resource declarations through an explicit compatibility normalizer
- [x] Add validation tests and run full regression


## Legacy alias compatibility boundary

- [x] Inventory all legacy aliases and canonical replacements
- [x] Classify aliases as compatibility-only with owner and removal conditions
- [x] Centralize alias mapping in one compatibility module
- [x] Ensure Core readiness/resource logic uses canonical names only
- [x] Keep legacy API/test callers working through the bridge
- [x] Add alias compatibility tests and run full regression


## Full Core regression suite

- [x] Inventory Core-focused test groups and environment-sensitive tests
- [x] Run compileall and the complete Core regression suite
- [x] Classify failures versus dependency/environment skips
- [x] Fix any real Core regression without restoring architectural coupling
- [x] Re-run Core suite and record final pass/fail/skip counts


## Final UI and shortcut alignment

- [x] Inventory Qt menus, context commands and global/local shortcuts
- [x] Route readiness/resource/workflow commands through controllers/services
- [x] Preserve adaptive menu behavior by workspace context
- [x] Restore preview F2 and Workshop state switching shortcuts
- [x] Remove duplicate or dead UI actions and shortcut handlers
- [x] Add UI/shortcut tests and run final regression


## Developer documentation

- [x] Document Workshop manifest schema and Core/App boundary
- [x] Document Resource Contract fields and validation states
- [x] Add valid/invalid manifest examples and resource lifecycle
- [x] Add onboarding, weights and troubleshooting guidance


## Workshop manifest validation CLI

- [x] Define validation rules and report format
- [x] Implement CLI scan for all Workshop manifests and resource declarations
- [x] Validate Core path, checksum metadata, UI entry and forbidden Workshop weight stores
- [x] Add unit tests for valid and invalid fixtures
- [x] Document local/CI usage and run against current workshops


## Final startup and weight-path lock

- [ ] Replace bootstrap `env_status["workshops"]` with the canonical report/workshop count field
- [ ] Add explicit `core_ready` to RuntimeReport and use it for App startup gating
- [ ] Keep `can_run_lite` as compatibility only, never as Core readiness
- [ ] Remove all manifest/runtime handling of `weights_directory` and Workshop-local weights
- [ ] Add regression tests for bootstrap key, Core readiness and canonical weights path
- [ ] Run complete Core regression suite
