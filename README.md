# NAS Music

NAS 音乐库管理工具，专为 Navidrome 设计。支持多平台下载、自动整理、元数据管理和播放列表同步。

## 功能

- **多源下载** — 网易云音乐、QQ音乐、Spotify、直链
- **自动整理** — 按 `艺术家/专辑/曲目` 结构组织文件
- **元数据管理** — ID3/FLAC 标签读写、MusicBrainz 匹配、歌词封面获取
- **格式转换** — 基于 FFmpeg 的音频转码
- **播放列表** — 导入歌单、导出 M3U8、同步 Navidrome
- **重复检测** — 基于哈希和元数据的查重

## 安装

### 环境要求

- Python >= 3.9
- FFmpeg（加入系统 PATH）
- Git

### 安装步骤

```bash
git clone git@github.com:mr-tkk/nas-music.git
cd nas-music
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 基础安装
pip install -e .

# 安装所有可选功能（Spotify、网易云、音频指纹）
pip install -e ".[all]"
```

## 快速开始

```bash
# 初始化配置
nasmusic config-init

# 查看配置
nasmusic config-show
```

编辑配置文件 `~/.config/nasmusic/config.yaml`，设置音乐库路径和 API 凭证。

## 使用

### 下载音乐

```bash
nasmusic download netease "歌曲链接或ID"
nasmusic download qq "歌曲链接或ID"
nasmusic download spotify "artist - song"
nasmusic download url "https://..."
nasmusic download search "周杰伦 晴天"
nasmusic download batch list.txt
```

### 管理音乐库

```bash
nasmusic library scan          # 扫描建立索引
nasmusic library organize      # 整理目录结构
nasmusic library duplicates    # 查重
nasmusic library convert /path --format mp3
nasmusic library stats         # 统计
nasmusic library verify        # 完整性检查
```

### 元数据

```bash
nasmusic metadata show song.mp3
nasmusic metadata edit song.mp3 --title "晴天" --artist "周杰伦"
nasmusic metadata match /path/to/music    # MusicBrainz 匹配
nasmusic metadata fetch-lyrics song.mp3
nasmusic metadata fetch-cover song.mp3
```

### 播放列表

```bash
nasmusic playlist create "我的歌单"
nasmusic playlist import-netease "歌单链接"
nasmusic playlist import-spotify "歌单链接"
nasmusic playlist export "我的歌单"       # 导出 M3U8
nasmusic playlist sync                    # 同步到 Navidrome
```

## 典型工作流

```bash
nasmusic config-init                    # 首次配置
nasmusic download netease "歌单链接"     # 下载歌单
nasmusic library scan                   # 扫描入库
nasmusic library organize               # 整理目录
nasmusic playlist export "我的歌单"      # 导出给 Navidrome
```

## 项目结构

```
src/nasmusic/
├── cli/           # CLI 命令（Typer）
├── core/          # 配置、数据模型、数据库
├── downloaders/   # 多源下载器
├── metadata/      # 标签、MusicBrainz、歌词、封面
├── organizer/     # 扫描、整理、转码、查重
├── playlists/     # 播放列表管理
└── utils/         # 工具函数
```

## 开发

```bash
pip install -e ".[dev]"
ruff check src/
pytest
```

## License

MIT
