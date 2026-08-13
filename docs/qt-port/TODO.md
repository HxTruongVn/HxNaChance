# Qt-only port TODO

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
