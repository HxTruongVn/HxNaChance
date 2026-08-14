# Main parity audit: naming, storage and preview

## Storage rules

The main application uses `save_dir` only as a user-selected root. The user may choose an existing folder/drive, and the business output path is then created as `save_dir/year/thang MM`. The generated Photo filename is `DD-HhMmSs-source_basename.jpg`. A Workshop or Shop identifier is not a storage directory. Qt now routes this policy through Core `BusinessOutputStore`, persists the selected root through `ConfigStore`, and exposes Choose/Open Save Folder actions.

Layout output is not only a raster image. The main implementation calls `save_layout(canvas, payload, out_path)`, which writes the image and a sidecar metadata file containing the layout payload. Qt preview saving now calls the same `save_layout` contract instead of calling `canvas.save` directly. Photo processing now generates its output path through the shared business-time policy instead of a fixed `photo_result.jpg` name.

## Preview rules

The main Photo Workshop uses a committed preview interaction contract and a revision guard: expensive processing runs outside the UI thread, and only the newest revision may update the panel. Qt now follows the same pattern with `_PhotoPreviewWorker`, `_photo_preview_revision`, and `_photo_preview_finished_qt`.

Layout option controls and the open side panel now share `_layout_controls_changed`; preset counts, checkboxes, technical fields and stroke options refresh the canvas and the already-open panel. Photo preset, sliders, toggles and background controls request a new revision while the panel is open.

## Remaining parity work

The next audit should compare every user-facing filename label and all legacy Workshop menu captions. Tkinter compatibility remains intentionally present until native Qt validation is complete; it must not be removed solely from this audit.
