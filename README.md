# NAS Music

NAS 音乐库管理工具，专为 Navidrome 设计。通过 YouTube 免费下载音乐，自动整理、标签管理和播放列表同步。

## 功能

- **YouTube 下载** — 通过 yt-dlp 从 YouTube 免费下载音乐，无需账号
- **自动整理** — 按 `艺术家/专辑/曲目` 结构组织文件
- **元数据管理** — ID3/FLAC 标签读写、MusicBrainz 匹配、封面获取
- **格式转换** — 基于 FFmpeg 的音频转码（默认 MP3 320kbps）
- **播放列表** — 创建歌单、导出 M3U8、同步 Navidrome
- **重复检测** — 基于哈希和元数据的查重

## 环境要求

- Python >= 3.9
- FFmpeg（加入系统 PATH）
- 能访问 YouTube 的网络环境（需代理）

## 安装

```bash
git clone git@github.com:mr-tkk/nas-music.git
cd nas-music
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e .
```

## 代理配置

由于 YouTube 在国内无法直接访问，需要配置代理：

```bash
# Windows
set HTTPS_PROXY=http://127.0.0.1:7890

# Linux/macOS
export HTTPS_PROXY=http://127.0.0.1:7890
```

也可以写入 `.env` 文件（项目根目录）：

```
HTTPS_PROXY=http://127.0.0.1:7890
```

## 快速开始

```bash
# 初始化配置
nasmusic config-init

# 下载一首歌
nasmusic download get "周杰伦 晴天"

# 批量下载
nasmusic download batch jay.txt
```

## 使用

### 下载音乐

```bash
# 通过关键词搜索下载
nasmusic download get "周杰伦 晴天"

# 通过 YouTube 链接下载
nasmusic download get "https://www.youtube.com/watch?v=..."

# 搜索（不下载，仅查看结果）
nasmusic download search "周杰伦" --limit 20

# 批量下载（文本文件，每行一首歌）
nasmusic download batch songs.txt
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
nasmusic metadata match /path/to/music    # MusicBrainz 自动匹配
nasmusic metadata fetch-cover song.mp3    # 获取封面
nasmusic metadata fix --auto              # 自动修复标签
```

### 播放列表

```bash
nasmusic playlist create "我的歌单"
nasmusic playlist list
nasmusic playlist export "我的歌单"       # 导出 M3U8
nasmusic playlist sync                    # 同步所有歌单到 Navidrome
nasmusic playlist download-all "我的歌单" # 下载歌单中未下载的歌曲
```

## 典型工作流

```bash
nasmusic config-init                    # 首次配置
nasmusic download batch jay.txt         # 批量下载
nasmusic library scan                   # 扫描入库
nasmusic library organize               # 整理目录
nasmusic metadata fix --auto            # 自动修复标签
nasmusic playlist create "周杰伦精选"    # 创建歌单
nasmusic playlist export "周杰伦精选"    # 导出给 Navidrome
```

## 项目结构

```
src/nasmusic/
├── cli/           # CLI 命令（Typer）
├── core/          # 配置、数据模型、数据库
├── downloaders/   # YouTube 下载器（yt-dlp）
├── metadata/      # 标签、MusicBrainz、封面
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
