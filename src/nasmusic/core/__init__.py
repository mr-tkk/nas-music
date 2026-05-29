from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from platformdirs import user_config_dir


APP_NAME = "nasmusic"
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = Path(user_config_dir(APP_NAME))
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"


class LibraryConfig(BaseModel):
    music_dir: Path = Field(default=PROJECT_DIR / "music")
    format: str = "mp3"
    bitrate: int = 320
    structure: str = "{artist}/{album}/{track_number:02d} - {title}"


class NavidromeConfig(BaseModel):
    url: str = ""
    username: str = ""
    password: str = ""


class SpotifyConfig(BaseModel):
    client_id: str = ""
    client_secret: str = ""


class NeteaseConfig(BaseModel):
    phone: str = ""
    password: str = ""


class QQMusicConfig(BaseModel):
    cookie: str = ""


class MusicBrainzConfig(BaseModel):
    user_agent: str = "NASMusic/0.1.0"


class DatabaseConfig(BaseModel):
    path: str = "data/library.db"


class AppConfig(BaseModel):
    library: LibraryConfig = Field(default_factory=LibraryConfig)
    navidrome: NavidromeConfig = Field(default_factory=NavidromeConfig)
    spotify: SpotifyConfig = Field(default_factory=SpotifyConfig)
    netease: NeteaseConfig = Field(default_factory=NeteaseConfig)
    qqmusic: QQMusicConfig = Field(default_factory=QQMusicConfig)
    musicbrainz: MusicBrainzConfig = Field(default_factory=MusicBrainzConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


_config: Optional[AppConfig] = None


def load_config(path: Optional[Path] = None) -> AppConfig:
    global _config

    if path is None:
        local = Path("config.yaml")
        if local.exists():
            path = local
        elif DEFAULT_CONFIG_PATH.exists():
            path = DEFAULT_CONFIG_PATH

    if path and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _config = AppConfig(**data)
    else:
        _config = AppConfig()

    return _config


def get_config() -> AppConfig:
    global _config
    if _config is None:
        return load_config()
    return _config


def get_db_path() -> Path:
    cfg = get_config()
    db_path = Path(cfg.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_music_dir() -> Path:
    cfg = get_config()
    cfg.library.music_dir.mkdir(parents=True, exist_ok=True)
    return cfg.library.music_dir


def save_default_config(path: Optional[Path] = None) -> Path:
    if path is None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        path = DEFAULT_CONFIG_PATH

    music_dir = str(PROJECT_DIR / "music").replace("\\", "/")
    template = f"""library:
  music_dir: "{music_dir}"
  format: mp3
  bitrate: 320
  structure: "{{artist}}/{{album}}/{{track_number:02d}} - {{title}}"

navidrome:
  url: "http://your-nas-ip:4533"
  username: admin
  password: ""

spotify:
  client_id: ""
  client_secret: ""

netease:
  phone: ""
  password: ""

qqmusic:
  cookie: ""

musicbrainz:
  user_agent: "NASMusic/0.1.0 (your-email@example.com)"

database:
  path: "data/library.db"
"""
    path.write_text(template, encoding="utf-8")
    return path
