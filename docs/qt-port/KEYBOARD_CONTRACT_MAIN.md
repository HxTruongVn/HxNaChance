# Main keyboard contract

## Host/Core global bindings

The main branch installs these bindings through `MenuBarMixin` and `core_shortcut_policy`:

| Binding | Meaning | Context rule |
|---|---|---|
| `Alt+F` | Open File menu | Menu mnemonic; stop propagation after opening one menu. |
| `Alt+E` | Open Edit menu | Same mnemonic behavior. |
| `Alt+P` | Open Pipeline menu | Same mnemonic behavior. |
| `Alt+W` | Open Window menu | Same mnemonic behavior. |
| `Alt+V` | Open View menu | Same mnemonic behavior. |
| `Alt+T` | Open Tool menu | Same mnemonic behavior. |
| `Alt+H` | Open Help menu | Same mnemonic behavior. |
| `Ctrl+O` | Open active Workshop / context open | Routes to active-workshop open action. |
| `Ctrl+S` | Save state | Ignored for Entry/Text/Spinbox editing focus; otherwise routes through context command `file.save`. |
| `Ctrl+Z` | Undo | Ignored for text editing focus; otherwise routes through `edit.undo`. |
| `Ctrl+Y` | Redo | Ignored for text editing focus; otherwise routes through `edit.redo`. |
| `Ctrl+R` | Run | Routes to Pipeline or active Workshop provider according to context. |
| `Ctrl+grave` | Next Workshop | Session-based navigation; may open first session when no live Workshop exists. |
| `Ctrl+Shift+grave` | Previous Workshop | Session-based reverse navigation; may open last session when no live Workshop exists. |
| `Ctrl+Alt+grave` | Core/Home | Closes active Workshop windows, restores Core, raises/focuses host. |

The actual source uses the grave key (`KeyPress-grave`), rendered here as `Ctrl+grave` and `Ctrl+Shift+grave` to avoid Markdown escaping ambiguity.

## Menu mnemonic policy

Top-level menus are File, Edit, Pipeline, Window, View, Tool, Help. The first ASCII letter is underlined, and Alt+letter opens exactly one menu. Nested menu items also receive an underline based on the first ASCII letter, with explicit exceptions for Runtime/System commands.

## Layout interaction contract

Each selected layout preset has a quantity entry. Selecting a preset ensures its quantity is at least 1. Changing the quantity to zero deselects the preset; changing it above zero selects the preset. Return and focus-out commit preview interaction. The quantity is a single canonical value per preset; no second quantity state may be introduced.

The Qt implementation must provide a clearly readable quantity field and native keyboard adjustment for the selected preset. The visible field must not be made narrow enough to clip the number. The selected preset's field receives focus so Up/Down can adjust its quantity without requiring a duplicate visible +/- control.

## Non-keyboard bindings not to mistake for shortcuts

The main branch also has title-bar drag/double-click, resize grip, list selection, slider release, Return/FocusOut commits, and mouse click handlers. These are interaction bindings, not global command shortcuts and must not be silently promoted to global Qt shortcuts.
