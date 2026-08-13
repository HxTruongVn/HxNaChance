"""
NaChance Application Core

Chứa entry point main.py, UI main_ui.py, và photo agent.
"""

# Install Core keyboard/menu policy before app.main_ui imports MenuBarMixin.
# The policy is isolated from Workshop business logic and keeps startup
# compatible if the optional UI policy cannot load.
try:
    from ui.core_shortcut_policy import install as _install_core_shortcut_policy
    _install_core_shortcut_policy()
except Exception:
    pass
