# NaChance Qt-only branch

This branch starts from `origin/main`. Its only purpose is to replace the desktop Tk/CustomTkinter presentation with a PySide6 presentation while preserving the existing NaChance logic.

## Non-goals

The branch does not redesign Core, replace RuntimeManager, rewrite Workshop engines, create a new CLI architecture, or move model/resource ownership. `app/`, `setup/`, `core/`, and `workshops/` remain the source of business behavior from `main`.

## Current entrypoints

The Qt branch primary entrypoint is now:

```bash
pip install -r setup/requirements-qt.txt
python NaChance.py
```

The original Tk entrypoint is retained only as an explicit legacy fallback:

```bash
python NaChanceTk.py
```

## Current Qt slice

The Qt window currently exposes Core status and manifest discovery, a Layout tab that calls `workshops.layout.print_layout.build_layout_canvas` and `save_layout`, a Photo tab that lazily calls `workshops.photo.NaChanceEngine` and `PhotoQAAgent`, and a Repo Intake tab that reads the existing manifest.

No Workshop algorithm is copied into the Qt layer. Qt owns widgets, signals, dialogs and worker threads; the existing main services and Workshop modules own processing behavior.

## Parity rule

A Qt change is acceptable only when the corresponding main behavior remains unchanged and the same existing service/engine can be called by both frontends. Missing Photo dependencies must disable or report Photo, not prevent Core or Layout from opening.
