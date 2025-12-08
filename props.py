from __future__ import annotations

from typing import Optional

import bpy
from bpy.props import CollectionProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .index import clear_index, ensure_index, get_base_dir
from .skin import format_skin_label


def clear_skin(props):
    try:
        props.property_unset("skin_name")
    except Exception:
        try:
            props.skin_name = ""
        except Exception:
            pass


def get_selected_model_from_props(props) -> Optional[str]:
    if props.active_model_index < 0 or props.active_model_index >= len(props.model_items):
        return None
    return props.model_items[props.active_model_index].name


def on_model_index_changed(self, context):
    try:
        base_dir = get_base_dir(self.game_path)
        index = ensure_index(base_dir)
        if not index:
            return None
        model_name = get_selected_model_from_props(self)
        if not model_name:
            clear_skin(self)
            return None
        entry = index["models"].get(model_name)
        if entry and entry["skins"]:
            self.skin_name = entry["skins"][0].as_posix()
        else:
            clear_skin(self)
    except Exception as exc:  # noqa: BLE001
        print(f"model index update failed: {exc}")
    return None


def update_game_path(self, context):
    clear_index()
    refresh_model_list(context)


def update_search(self, context):
    refresh_model_list(context)


def update_model_index(self, context):
    return on_model_index_changed(self, context)


def refresh_model_list(context) -> None:
    props = context.scene.pk3_browser
    base_dir = get_base_dir(props.game_path)
    index = ensure_index(base_dir)
    props.model_items.clear()
    clear_skin(props)
    if not index:
        props.active_model_index = -1
        return
    filter_text = props.search.lower().strip()
    for name in sorted(index["models"].keys()):
        if filter_text and filter_text not in name.lower():
            continue
        item = props.model_items.add()
        item.name = name
        item.label = name
        primary = index["models"][name]["primary"]
        if primary.origin == "disk":
            item.source = "disk"
        elif primary.container:
            item.source = primary.container.name
        else:
            item.source = "pk3"
    if not props.model_items:
        props.active_model_index = -1
        return
    if props.model_items and (props.active_model_index < 0 or props.active_model_index >= len(props.model_items)):
        props.active_model_index = 0
    if props.active_model_index >= 0 and props.model_items:
        model_name = props.model_items[props.active_model_index].name
        entry = index["models"].get(model_name)
        if entry and entry["skins"]:
            props.skin_name = entry["skins"][0].as_posix()
        else:
            props.skin_name = ""


def skin_enum_items(self, context):
    try:
        props = context.scene.pk3_browser if context and getattr(context, "scene", None) else self
    except Exception:
        props = self
    base_dir = get_base_dir(getattr(props, "game_path", ""))
    index = ensure_index(base_dir)
    model_name = get_selected_model_from_props(props) if hasattr(props, "model_items") else None
    if not index or not model_name:
        return [("", "No model", "")]
    entry = index["models"].get(model_name)
    if not entry or not entry["skins"]:
        return [("", "No .skin files", "")]
    items = []
    for rel in entry["skins"]:
        label = format_skin_label(rel)
        items.append((rel.as_posix(), label, rel.as_posix()))
    return items


def ensure_skin_selected(props, *, assign: bool = True):
    base_dir = get_base_dir(props.game_path)
    index = ensure_index(base_dir)
    if not index:
        if assign:
            clear_skin(props)
        return None
    model_name = get_selected_model_from_props(props)
    if not model_name:
        if assign:
            clear_skin(props)
        return None
    entry = index["models"].get(model_name)
    if not entry or not entry["skins"]:
        if assign:
            clear_skin(props)
        return None
    valid = [rel.as_posix() for rel in entry["skins"]]
    if props.skin_name not in valid:
        if assign:
            props.skin_name = valid[0]
        return valid[0]
    return props.skin_name


class PK3ModelItem(PropertyGroup):
    name: StringProperty()
    label: StringProperty()
    source: StringProperty()


class PK3BrowserProperties(PropertyGroup):
    game_path: StringProperty(
        name="Game Path",
        description="Path to the game folder (GameData or base)",
        subtype="DIR_PATH",
        update=update_game_path,
    )
    search: StringProperty(
        name="Search",
        description="Filter models",
        default="",
        update=update_search,
    )
    model_items: CollectionProperty(type=PK3ModelItem)
    active_model_index: IntProperty(
        name="Model Index",
        default=-1,
        update=update_model_index,
    )
    skin_name: EnumProperty(
        name="Skin File",
        description="Select a skin before importing",
        items=skin_enum_items,
    )
    texture_save_dir: StringProperty(
        name="Texture Output",
        description="Folder to copy extracted textures to",
        subtype="DIR_PATH",
    )
