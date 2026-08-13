# Qt-only port TODO

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
