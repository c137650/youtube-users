# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Memory Graph — a tool that processes Google Takeout YouTube watch history data, classifies videos into personality-style tags, and renders an interactive graph in the browser.

## Commands

### Python backend
```bash
pip install google-api-python-client pandas
python main.py
```

### Frontend
```bash
cd frontend
npm install
npx vite --port 3888   # dev server at http://localhost:3888
# Or simply open frontend/index.html directly in a browser (requires internet for D3.js CDN)
```

There are no test commands in this project.

## Configuration

Before running `main.py`, edit `config.json`:
- `api.key` — YouTube Data API v3 key
- `api.proxy.http` / `api.proxy.https` — optional proxy (leave empty strings if not needed)
- `paths.takeout_dir` — absolute path to the directory containing the Google Takeout export

Place the Google Takeout ZIP or the extracted folder at `paths.takeout_dir`. The pipeline auto-detects both Chinese and English Takeout folder names (`"YouTube 和 YouTube Music"` / `"YouTube and YouTube Music"`).

## Architecture

### Data pipeline (`main.py`)

Single-file Python script that runs a sequential 6-step pipeline:

1. **Extract** — unzips Takeout archive if needed
2. **Parse HTML** — regex-extracts video IDs and watch timestamps from `watch-history.html` (handles Chinese date format `YYYY年MM月DD日`)
3. **YouTube API** — batch-fetches video metadata (title, tags, channel, description) in groups of 50
4. **Format** — converts API results into `{title: [watch_time, video_id, tags_str, channel, description]}` dict
5. **Tag matching** — regex-matches video metadata against keywords in `user_tags.json`; output format is `{title: [matched_tags_str, url, watch_time]}`
6. **Save** — writes timestamped JSON files to `outcome/<N>/` (auto-incremented folder)

Output files in each run folder:
- `video_labels_<timestamp>.json` — **the file the frontend consumes**
- `video_details_<timestamp>.json` — raw API response data
- `video_dict_<timestamp>.json` — intermediate formatted dict
- `video_times_<timestamp>.json` — video_id → watch_time mapping
- `metadata.json` — run summary

### Tag system (`user_tags.json`)

Four categories of tags: `core_tags`, `meme_tags`, `social_tags`, `time_tags`. Each tag has a `keywords` array used for case-insensitive regex matching against `"<title> <description> <api_tags> <channel>"`. Tags from all categories are merged and applied uniformly during matching.

### Frontend (`frontend/`)

Vanilla JS + HTML Canvas + D3-force (loaded from CDN). No build step required for the static files.

**Two-view architecture:**
- **Bubble view** — one bubble per tag, sized by video count, rendered with `d3.forceSimulation` + Canvas. Click a bubble → switches to graph view.
- **Graph view** — nodes are videos within the selected tag; edges connect videos sharing a tag. Node color opacity encodes watch recency (older = more transparent). Click a node → opens the YouTube video in a new tab. ESC / back button → returns to bubble view.

**Data flow:** User clicks "Load Data" → file picker → `loadData()` parses `video_labels_<timestamp>.json` → `calculateTagStats()` builds `tagStats` map → `renderBubbleChart()`.

The drag vs. click distinction on graph nodes uses a 5px movement threshold tracked via `state.isDragging` / `state.justDragged`.
