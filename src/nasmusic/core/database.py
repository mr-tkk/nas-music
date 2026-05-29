from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from nasmusic.core import get_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT,
    file_size INTEGER,
    duration_seconds REAL,
    title TEXT,
    artist TEXT,
    album_artist TEXT,
    album TEXT,
    track_number INTEGER,
    disc_number INTEGER DEFAULT 1,
    year INTEGER,
    genre TEXT,
    source TEXT,
    source_id TEXT,
    source_url TEXT,
    has_cover_art INTEGER DEFAULT 0,
    has_lyrics INTEGER DEFAULT 0,
    metadata_quality TEXT DEFAULT 'unknown',
    musicbrainz_id TEXT,
    added_at TEXT DEFAULT (datetime('now')),
    modified_at TEXT DEFAULT (datetime('now')),
    last_scanned_at TEXT
);

CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    year INTEGER,
    musicbrainz_release_id TEXT,
    cover_art_path TEXT,
    track_count INTEGER,
    source TEXT,
    source_id TEXT,
    added_at TEXT DEFAULT (datetime('now')),
    UNIQUE(title, artist)
);

CREATE TABLE IF NOT EXISTS download_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    status TEXT NOT NULL,
    result_track_id INTEGER REFERENCES tracks(id),
    error_message TEXT,
    downloaded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    source TEXT,
    source_id TEXT,
    source_url TEXT,
    track_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id INTEGER REFERENCES tracks(id),
    position INTEGER NOT NULL,
    pending_title TEXT,
    pending_artist TEXT,
    pending_source TEXT,
    pending_source_id TEXT,
    added_at TEXT DEFAULT (datetime('now')),
    UNIQUE(playlist_id, position)
);

CREATE TABLE IF NOT EXISTS duplicate_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_track_id INTEGER REFERENCES tracks(id),
    detection_method TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS duplicate_members (
    group_id INTEGER NOT NULL REFERENCES duplicate_groups(id) ON DELETE CASCADE,
    track_id INTEGER NOT NULL REFERENCES tracks(id),
    is_canonical INTEGER DEFAULT 0,
    PRIMARY KEY (group_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album);
CREATE INDEX IF NOT EXISTS idx_tracks_source ON tracks(source, source_id);
CREATE INDEX IF NOT EXISTS idx_tracks_hash ON tracks(file_hash);
CREATE INDEX IF NOT EXISTS idx_download_history_query ON download_history(query, source);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist ON playlist_tracks(playlist_id, position);
"""


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def init(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def add_track(self, **kwargs) -> int:
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.conn.execute(
            f"INSERT OR REPLACE INTO tracks ({cols}) VALUES ({placeholders})",
            list(kwargs.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_track_by_path(self, file_path: str) -> Optional[dict]:
        cur = self.conn.execute("SELECT * FROM tracks WHERE file_path = ?", (file_path,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_track_by_source(self, source: str, source_id: str) -> Optional[dict]:
        cur = self.conn.execute(
            "SELECT * FROM tracks WHERE source = ? AND source_id = ?", (source, source_id)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def search_tracks(self, query: str, limit: int = 20) -> list[dict]:
        cur = self.conn.execute(
            """SELECT * FROM tracks
            WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
            LIMIT ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_all_tracks(self, limit: int = 1000, offset: int = 0) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM tracks ORDER BY artist, album, track_number LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in cur.fetchall()]

    def track_count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM tracks")
        return cur.fetchone()[0]

    def add_download_history(self, query: str, source: str, status: str, **kwargs) -> int:
        kwargs.update({"query": query, "source": source, "status": status})
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.conn.execute(
            f"INSERT INTO download_history ({cols}) VALUES ({placeholders})",
            list(kwargs.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def is_downloaded(self, source: str, source_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM download_history WHERE source = ? AND source_id = ? AND status = 'success'",
            (source, source_id),
        )
        return cur.fetchone() is not None

    def create_playlist(self, name: str, **kwargs) -> int:
        kwargs["name"] = name
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.conn.execute(
            f"INSERT INTO playlists ({cols}) VALUES ({placeholders})",
            list(kwargs.values()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_playlists(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM playlists ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

    def add_playlist_track(self, playlist_id: int, track_id: int, position: int):
        self.conn.execute(
            "INSERT OR REPLACE INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
            (playlist_id, track_id, position),
        )
        self.conn.execute(
            "UPDATE playlists SET track_count = (SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?), updated_at = datetime('now') WHERE id = ?",
            (playlist_id, playlist_id),
        )
        self.conn.commit()

    def get_playlist_tracks(self, playlist_id: int) -> list[dict]:
        cur = self.conn.execute(
            """SELECT t.* FROM playlist_tracks pt
            JOIN tracks t ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position""",
            (playlist_id,),
        )
        return [dict(row) for row in cur.fetchall()]


_db: Optional[Database] = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
        _db.init()
    return _db
