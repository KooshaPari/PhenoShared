# focus-asset-fetcher

Asset downloader and post-processor for FocalPoint audio resources. Fetches SFX and phoneme samples from manifest, post-processes via ffmpeg, and caches locally for incremental builds.

## Purpose

Enables deterministic, reproducible builds with declarative asset dependencies. Parses `SOUND_SOURCES.md` manifest, fetches audio files with integrity validation, post-processes (normalize, compress, resample), and caches to avoid re-downloads. Used during `focus-mcp-server` and native app builds.

## Key Types

- `AssetSpec` — parsed asset declaration (url, format, post_process_step)
- `FetcherConfig` — configuration (cache_dir, ffmpeg_path, max_concurrent)
- `Fetcher` — orchestrates download, post-processing, caching
- `PostProcessor` — runs ffmpeg commands (normalize, resample, encode)

## Entry Points

- `Fetcher::new()` — initialize with cache directory
- `Fetcher::fetch_all()` — download and post-process all assets in manifest
- `Fetcher::fetch_one()` — download and cache a single asset

## Functional Requirements

- Build system integration
- Cache coherency and integrity validation
- Deterministic output for reproducible builds

## Consumers

- Build scripts (Cargo build hooks)
- CI asset pre-caching
- `focus-mcp-server` audio resource bundles
