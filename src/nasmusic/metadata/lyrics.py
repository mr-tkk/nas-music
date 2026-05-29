from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx


def fetch_lyrics_netease(song_id: str) -> Optional[str]:
    url = "https://music.163.com/api/song/lyric"
    params = {"id": song_id, "lv": -1, "tv": -1}
    headers = {"Referer": "https://music.163.com/", "User-Agent": "Mozilla/5.0"}

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=15, verify=False)
        data = resp.json()
        lrc = data.get("lrc", {}).get("lyric", "")
        return lrc if lrc else None
    except Exception:
        return None


def fetch_lyrics_qqmusic(song_mid: str) -> Optional[str]:
    url = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
    params = {"songmid": song_mid, "format": "json", "nobase64": 1}
    headers = {"Referer": "https://y.qq.com/"}

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=15, verify=False)
        data = resp.json()
        return data.get("lyric") or None
    except Exception:
        return None


def save_lrc_file(filepath: Path, lrc_content: str) -> Path:
    lrc_path = filepath.with_suffix(".lrc")
    lrc_path.write_text(lrc_content, encoding="utf-8")
    return lrc_path


def has_lrc_file(filepath: Path) -> bool:
    return filepath.with_suffix(".lrc").exists()
