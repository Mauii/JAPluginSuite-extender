from __future__ import annotations

# Central registration for the add-on. Implementation is split into modules for clarity.

import bpy
from bpy.props import PointerProperty

from .props import PK3BrowserProperties, PK3ModelItem
from .operators import PK3_OT_apply_skin, PK3_OT_import_model, PK3_OT_refresh_models, PK3_OT_save_textures
from .ui import PK3_PT_panel, PK3_UL_models

CLASSES = (
    PK3ModelItem,
    PK3BrowserProperties,
    PK3_UL_models,
    PK3_OT_refresh_models,
    PK3_OT_import_model,
    PK3_OT_apply_skin,
    PK3_OT_save_textures,
    PK3_PT_panel,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pk3_browser = PointerProperty(type=PK3BrowserProperties)


def unregister():
    del bpy.types.Scene.pk3_browser
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
