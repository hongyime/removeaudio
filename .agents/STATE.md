# removeaudio — Agent State

## Stack
- **Language**: Python
- **Dependencies**: ffmpeg (via subprocess), standard library
- **Type**: CLI utility — removes audio from video files

## Last Commit
- **Date**: 2026-09-10 15:17:30 +0800
- **SHA**: 2b233c7
- **Message**: fix: publish muted videos only after successful conversion

## Status
- Working tree: clean (no uncommitted changes)
- .agents/: exists (AGENTS.md present)
- AGENTS.md: exists

## Issues Found
- `noaudio.py` is deprecated with CVSS 9.8 command injection + path traversal — kept as reference only
- `noaudio_secure.py` is the current safe implementation
- `noaudio.py.VULNERABLE` also present as historical artifact
- No hardcoded secrets found in scanned files

## Triage Date
2026-09-16
