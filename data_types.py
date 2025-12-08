from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileSource:
    origin: str  # "disk" or "pk3"
    container: Optional[Path]
    rel_path: Path


@dataclass
class ModelSource:
    origin: str
    container: Optional[Path]
    glm: Optional[Path] = None
    skins: set = field(default_factory=set)
    glas: set = field(default_factory=set)
