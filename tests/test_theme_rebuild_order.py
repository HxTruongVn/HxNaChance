from pathlib import Path


def test_theme_rebuild_keeps_title_before_menu():
    source = Path("ui/theme_mixin.py").read_text(encoding="utf-8")
    rebuild = source.split("self.configure(fg_color=self.COLORS['bg_dark'])", 1)[1]
    assert rebuild.index("self._build_title_bar()") < rebuild.index("self._build_menu_bar()")
