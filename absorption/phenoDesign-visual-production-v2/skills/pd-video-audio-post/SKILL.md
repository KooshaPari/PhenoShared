---
name: pd-video-audio-post
description: "Finish video and audio derivatives with reproducible FFmpeg processing, captions and delivery checks."
license: MIT (original guidance; linked tools and assets keep their own licenses)
---

# Video Audio Post

Treat editorial choices and signal transforms as first-class source data. Record clip order, in/out times, speed changes, audio gain, captions, crop, codec and output profile. Keep original captures and high-quality masters; never replace them with a recompressed social export.

Use FFprobe for measured stream metadata and FFmpeg for explicit transforms with argument arrays, bounded execution and job-owned paths. The included media auditor actually decodes files and checks requested metadata, but does not prove visual quality, loudness safety, correct caption text or lip sync. Those need separate measurements and review.

Choose formats by consumer, not fashion. A silent looping background, transparent overlay, instructional recording and a long product film have different audio/alpha/seek/compression needs. Provide a poster and useful text alternative. Do not force autoplay audio or encode a gigantic GIF where a video works better.

Inspect first/last frames, scene cuts, subtitles at mobile size, clipping, color changes, banding and audio intelligibility. Check stream presence and duration independently; a video-only render can look right while dropping narration. Measure audio peaks/loudness with a configured target rather than guessing normalization. Test actual browser/native playback after final encode, not only the editor preview.

## Related contracts

Read the repository's `docs/visual-production/E2E-CONTRACT.md`, `ALL-FORMS.md`, and source catalog for the selected tool. In the standalone kit these are under `docs/` and `resources/`. Preserve exact failure/blocked states and the existing source/evidence owners.
