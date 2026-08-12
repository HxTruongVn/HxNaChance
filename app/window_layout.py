"""Shared window sizing/placement rules.

System-wide UI convention:
- Workshop windows open in a compact/content-fit presentation.
- Double-clicking the custom title bar restores that same compact presentation.
- The compact width is based on the *intrinsic* width of visible content, not
  on the current width of an expanding/scrollable host frame.
- Long vertical content is intentionally allowed to scroll; compact height is
  capped so a Workshop does not become a screen-height monster.
- Labels/buttons are never intentionally truncated just to make a window
  smaller.
- When another Workshop is opened, it prefers the right side of the active
  Workshop when enough screen space exists.
"""
from __future__ import annotations


def _padding_from_manager(widget, manager: str):
    """Return requested external padding for a managed child."""
    try:
        info = widget.pack_info() if manager == "pack" else widget.grid_info()
    except Exception:
        return 0, 0

    def _pair(value):
        try:
            if isinstance(value, (tuple, list)):
                if len(value) == 1:
                    return int(float(value[0])), int(float(value[0]))
                return int(float(value[0])), int(float(value[1]))
            value = int(float(value or 0))
            return value, value
        except Exception:
            return 0, 0

    padx = _pair(info.get("padx", 0))
    pady = _pair(info.get("pady", 0))
    return sum(padx), sum(pady)


def _intrinsic_size(widget):
    """Measure the smallest useful size implied by the widget's content.

    The key rule is *content first, container second*.  Expanding hosts such
    as ``CTkScrollableFrame`` must never feed their current expanded width
    back into Auto-Fit.

    For ordinary vertical ``pack`` containers, width is the widest child.
    For horizontal ``pack`` rows, width is the sum of the children.
    For ``grid`` containers we deliberately measure *each visual row* and
    use the widest row as the minimum content width.  This matches the UI
    convention used by the Shops: a row is the smallest horizontal unit the
    user must be able to read/use.  Grid padding on each child is included.
    """
    try:
        children = [c for c in widget.winfo_children() if c.winfo_manager()]
    except Exception:
        children = []

    if not children:
        # A leaf widget's requested size is its intrinsic size. For an empty
        # expanding container, keep the fallback tiny so the parent does not
        # inherit the current window width as a fake content requirement.
        try:
            return max(1, int(widget.winfo_reqwidth())), max(1, int(widget.winfo_reqheight()))
        except Exception:
            return 1, 1

    managers = {str(c.winfo_manager()) for c in children}

    if "grid" in managers:
        return _intrinsic_grid_size(widget, children)

    # Pack-based containers.
    total_h = 0
    max_w = 0
    left_right = []
    top_bottom = []
    for child in children:
        try:
            info = child.pack_info()
            side = str(info.get("side", "top"))
        except Exception:
            side = "top"
        (left_right if side in {"left", "right"} else top_bottom).append(child)

    if left_right and not top_bottom:
        total_w = 0
        max_h = 0
        for child in left_right:
            cw, ch = _intrinsic_size(child)
            px, py = _padding_from_manager(child, "pack")
            total_w += cw + px
            max_h = max(max_h, ch + py)
        return max(1, total_w), max(1, max_h)

    for child in children:
        cw, ch = _intrinsic_size(child)
        px, py = _padding_from_manager(child, "pack")
        total_h += ch + py
        max_w = max(max_w, cw + px)

    return max(1, max_w), max(1, total_h)


def _intrinsic_grid_size(widget, children):
    """Return content size for a grid by measuring its visual rows.

    ``grid_columnconfigure(weight=1)`` is intentionally ignored here: it
    describes how a container should consume *extra* space, not how much
    space its content actually needs.
    """
    rows = {}
    for child in children:
        try:
            info = child.grid_info()
            row = int(info.get("row", 0))
            padx, pady = _padding_from_manager(child, "grid")
            cw, ch = _intrinsic_size(child)
        except Exception:
            continue
        rows.setdefault(row, []).append((cw + padx, ch + pady))

    if not rows:
        try:
            return max(1, int(widget.winfo_reqwidth())), max(1, int(widget.winfo_reqheight()))
        except Exception:
            return 1, 1

    # A row is the unit that must remain usable.  The widest row determines
    # the minimum width; heights stack vertically because rows are stacked.
    row_widths = []
    total_h = 0
    for row in sorted(rows):
        items = rows[row]
        row_width = sum(w for w, _ in items)
        row_height = max((h for _, h in items), default=0)
        row_widths.append(row_width)
        total_h += row_height

    try:
        ipadx = int(float(widget.grid_info().get("padx", 0))) * 2
        ipady = int(float(widget.grid_info().get("pady", 0))) * 2
    except Exception:
        ipadx = ipady = 0

    return max(1, max(row_widths, default=1) + ipadx), max(1, total_h + ipady)

def _content_intrinsic_size(window):
    """Measure Workshop content without measuring the expanding viewport.

    A ``CTkScrollableFrame`` is a viewport, not content. Depending on the
    CustomTkinter version, user children may live directly on the scrollable
    frame or on its private parent frame. Prefer the latter only when it has
    actual user children; never use the viewport's current width as the
    intrinsic width.
    """
    content = getattr(window, "main_frame", None)
    if content is None:
        return _intrinsic_size(window)

    try:
        children = [c for c in content.winfo_children() if c.winfo_manager()]
    except Exception:
        children = []

    if children:
        return _intrinsic_size(content)

    # CustomTkinter has changed the internal ownership of CTkScrollableFrame
    # across versions.  If the public frame has no user children, inspect the
    # internal parent frame when available. This is deliberately structural
    # rather than class-name based so it remains compatible across versions.
    internal = getattr(content, "_parent_frame", None)
    if internal is not None and internal is not content:
        try:
            if any(c.winfo_manager() for c in internal.winfo_children()):
                return _intrinsic_size(internal)
        except Exception:
            pass

    return _intrinsic_size(content)


def compact_window(window, *, min_width=0, min_height=0,
                   max_width=None, max_height=None, width_extra=28,
                   height_extra=74):
    """Resize *window* to its smallest useful content-fit presentation.

    Width is measured from visible content rather than the current expanded
    scrollable frame. Height is capped by a compact viewport so long content
    remains scrollable instead of making the whole Workshop almost full-screen.
    """
    window.update_idletasks()
    screen_w = int(window.winfo_screenwidth())
    screen_h = int(window.winfo_screenheight())
    if max_width is None:
        max_width = screen_w - 24
    if max_height is None:
        # A Workshop is a scrollable panel.  Prefer a compact viewport instead
        # of consuming the whole desktop; the exact value scales with screen
        # height but leaves room for the desktop/taskbar.
        max_height = min(screen_h - 60, max(600, int(screen_h * 0.78)))

    req_w, req_h = _content_intrinsic_size(window)

    # There is deliberately no system-wide Workshop width floor.  The only
    # lower bound is the actual content requirement plus a small amount of
    # window chrome.  This prevents a hard-coded 420px floor from defeating
    # content-fit for compact Shops.
    chrome_min_w = 220
    chrome_min_h = 150
    width = max(chrome_min_w, int(min_width), min(int(max_width), req_w + int(width_extra)))
    height = max(chrome_min_h, int(min_height), min(int(max_height), req_h + int(height_extra)))

    # Keep the native window minimum aligned with the calculated compact
    # presentation.  It must not be larger than the content-fit result.
    try:
        window.minsize(width, height)
    except Exception:
        pass
    window.geometry(f"{width}x{height}")
    window.update_idletasks()
    return width, height


def place_right_of(anchor, window, *, gap=8, screen_margin=12):
    """Place *window* immediately to the right of *anchor* when possible."""
    window.update_idletasks()
    anchor.update_idletasks()
    screen_w = int(window.winfo_screenwidth())
    screen_h = int(window.winfo_screenheight())
    width = max(1, int(window.winfo_width()))
    height = max(1, int(window.winfo_height()))
    ax = int(anchor.winfo_x())
    ay = int(anchor.winfo_y())
    aw = int(anchor.winfo_width())

    x = ax + aw + int(gap)
    if x + width > screen_w - screen_margin:
        return False

    y = min(max(screen_margin, ay), max(screen_margin, screen_h - height - screen_margin))
    window.geometry(f"{width}x{height}+{x}+{y}")
    return True


def place_below(anchor, window, *, gap=8, screen_margin=12):
    """Fallback placement directly below an anchor when the right side is full."""
    window.update_idletasks()
    anchor.update_idletasks()
    screen_w = int(window.winfo_screenwidth())
    screen_h = int(window.winfo_screenheight())
    width = max(1, int(window.winfo_width()))
    height = max(1, int(window.winfo_height()))
    ax = int(anchor.winfo_x())
    ay = int(anchor.winfo_y())
    ah = int(anchor.winfo_height())

    x = min(max(screen_margin, ax), max(screen_margin, screen_w - width - screen_margin))
    y = ay + ah + int(gap)
    if y + height > screen_h - screen_margin:
        return False
    window.geometry(f"{width}x{height}+{x}+{y}")
    return True
