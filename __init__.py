from __future__ import annotations

bl_info = {
    "name": "PK3 Model Browser",
    "author": "Maui",
    "version": (0, 5, 6),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > PK3",
    "description": "Browse PK3 files and import Jedi Academy GLM with skins and textures",
    "category": "Import-Export",
}

# All functionality lives in addon_impl to keep __init__ lean.
from .addon_impl import *  # noqa: F401,F403
from .addon_impl import register, unregister

__all__ = ["register", "unregister"]
