from dataclasses import field, dataclass
from pathlib import Path
from typing import List, Optional

from aiopath import AsyncPath
from marshmallow_dataclass import class_schema
from tomlkit import loads as tomlloads

@dataclass
class Mount:
    mount: str
    root: str
    accel: Optional[str]


@dataclass
class Config:
    name: Optional[str]
    url_prefix: Optional[str]
    route_prefix: Optional[str]
    mounts: List[Mount] = field(default_factory=list)


config_schema = class_schema(Config)()

def load(path):
    path = Path(path)
    data = tomlloads(path.read_text())
    return config_schema.load(data)