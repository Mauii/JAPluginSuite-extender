from __future__ import annotations

import bpy
from bpy.types import Panel, UIList

from .operators import PK3_OT_apply_skin, PK3_OT_import_model, PK3_OT_refresh_models, PK3_OT_save_textures


class PK3_UL_models(UIList):
    bl_idname = "PK3_UL_models"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):  # noqa: D401
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.label(text=item.label)
            icon_id = "FILE_FOLDER" if item.source == "disk" else "FILE_ARCHIVE"
            row.label(text=item.source or "", icon=icon_id)
        elif self.layout_type == "GRID":
            layout.alignment = "CENTER"
            layout.label(text=item.label)


class PK3_PT_panel(Panel):
    bl_idname = "PK3_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PK3"
    bl_label = "PK3 Browser"

    def draw(self, context):
        props = context.scene.pk3_browser
        layout = self.layout
        layout.prop(props, "game_path")

        row = layout.row()
        row.prop(props, "search", text="", icon="VIEWZOOM")
        row.operator(PK3_OT_refresh_models.bl_idname, text="", icon="FILE_REFRESH")

        layout.template_list("PK3_UL_models", "", props, "model_items", props, "active_model_index", rows=10)

        if props.active_model_index >= 0 and props.model_items:
            layout.prop(props, "skin_name")
            row = layout.row(align=True)
            row.operator(PK3_OT_import_model.bl_idname, icon="IMPORT")
            row.operator(PK3_OT_apply_skin.bl_idname, text="Apply Skin", icon="TEXTURE")
            layout.separator()
            layout.prop(props, "texture_save_dir")
            layout.operator(PK3_OT_save_textures.bl_idname, icon="FILE_TICK")
