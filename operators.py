from __future__ import annotations

from pathlib import Path
import shutil

import bpy
from bpy.types import Operator

from .cache import extract_assets, relink_images_from_cache, rewrite_skin_paths
from .constants import CACHE_FOLDER, TEXTURE_EXTS
from .index import clear_index, ensure_index, get_base_dir
from .props import ensure_skin_selected, get_selected_model_from_props, refresh_model_list
from .skin import collect_assets_for_skin, derive_skin_suffix


class PK3_OT_refresh_models(Operator):
    bl_idname = "pk3.refresh_models"
    bl_label = "Refresh Models"

    def execute(self, context):
        clear_index()
        refresh_model_list(context)
        return {"FINISHED"}


class PK3_OT_import_model(Operator):
    bl_idname = "pk3.import_model"
    bl_label = "Import Model"

    def execute(self, context):
        props = context.scene.pk3_browser
        base_dir = get_base_dir(props.game_path)
        if not base_dir.is_dir():
            self.report({"ERROR"}, "Game path is invalid")
            return {"CANCELLED"}
        index = ensure_index(base_dir)
        if not index:
            self.report({"ERROR"}, "No models found")
            return {"CANCELLED"}
        model_name = get_selected_model_from_props(props)
        if not model_name:
            self.report({"ERROR"}, "Select a model first")
            return {"CANCELLED"}
        ensure_skin_selected(props)
        if not props.skin_name:
            self.report({"ERROR"}, "Select a skin file before import")
            return {"CANCELLED"}
        skin_rel = Path(props.skin_name)
        try:
            assets, missing, replacements = collect_assets_for_skin(index, base_dir, model_name, skin_rel)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        cache_root = base_dir / CACHE_FOLDER
        texture_map, failed = extract_assets(base_dir, cache_root, assets)
        rewrite_skin_paths(cache_root, skin_rel, replacements)
        glm_dest = cache_root / assets[0][1]
        skin_suffix = derive_skin_suffix(skin_rel)
        try:
            bpy.ops.import_scene.glm(
                filepath=str(glm_dest),
                skin=skin_suffix,
                basepath=str(cache_root),
                guessTextures=False,
            )
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, f"Import failed: {exc}")
            return {"CANCELLED"}
        relink_images_from_cache(texture_map)
        if missing:
            self.report({"WARNING"}, f"Missing textures: {len(missing)}")
        if failed:
            self.report({"WARNING"}, f"Failed to extract: {', '.join(failed)}")
        return {"FINISHED"}


class PK3_OT_apply_skin(Operator):
    bl_idname = "pk3.apply_skin"
    bl_label = "Apply Skin Textures"

    def execute(self, context):
        props = context.scene.pk3_browser
        base_dir = get_base_dir(props.game_path)
        if not base_dir.is_dir():
            self.report({"ERROR"}, "Game path is invalid")
            return {"CANCELLED"}
        index = ensure_index(base_dir)
        model_name = get_selected_model_from_props(props)
        if not index or not model_name:
            self.report({"ERROR"}, "Select a model first")
            return {"CANCELLED"}
        ensure_skin_selected(props)
        if not props.skin_name:
            self.report({"ERROR"}, "Select a skin file")
            return {"CANCELLED"}
        skin_rel = Path(props.skin_name)
        try:
            assets, missing, replacements = collect_assets_for_skin(index, base_dir, model_name, skin_rel)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        cache_root = base_dir / CACHE_FOLDER
        texture_map, failed = extract_assets(base_dir, cache_root, assets)
        rewrite_skin_paths(cache_root, skin_rel, replacements)
        relink_images_from_cache(texture_map)
        if missing:
            self.report({"WARNING"}, f"Missing textures: {len(missing)}")
        if failed:
            self.report({"WARNING"}, f"Failed to extract: {', '.join(failed)}")
        return {"FINISHED"}


class PK3_OT_save_textures(Operator):
    bl_idname = "pk3.save_textures"
    bl_label = "Save Textures"

    def execute(self, context):
        props = context.scene.pk3_browser
        base_dir = get_base_dir(props.game_path)
        cache_root = base_dir / CACHE_FOLDER
        if not cache_root.is_dir():
            self.report({"ERROR"}, "Cache is empty")
            return {"CANCELLED"}
        if not props.texture_save_dir:
            self.report({"ERROR"}, "Select an output folder")
            return {"CANCELLED"}
        out_dir = Path(props.texture_save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for tex in cache_root.rglob("*"):
            if tex.is_file() and tex.suffix.lower() in TEXTURE_EXTS:
                rel = tex.relative_to(cache_root)
                dest = out_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tex, dest)
                copied += 1
        self.report({"INFO"}, f"Saved {copied} texture(s)")
        return {"FINISHED"}
