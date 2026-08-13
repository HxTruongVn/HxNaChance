"""NaChance application package.

Importing this package is intentionally side-effect free. The legacy Tk
shortcut policy is installed explicitly by ``app.main`` before it imports the
Tk UI, so the Qt frontend can reuse application services without importing Tk.
"""
