# removeaudio

Documentation: https://hongyime.github.io/removeaudio/

![Project screenshot](./screenshot.png)

> Strip audio tracks from video files (MP4, AVI, MOV) using ffmpeg — secure version

## What it does
Batch-processes all video files in a directory and produces muted copies prefixed with `noaudio_`. Uses `ffmpeg` with stream-copy mode (no re-encoding — very fast). The secure version (`noaudio_secure.py`) uses subprocess list args to prevent command injection.

## Features
- Supports `.mp4`, `.avi`, `.mov` files (case-insensitive)
- No re-encoding — copies streams directly (`-c copy -an`), preserving quality
- Skips already-processed files (those starting with `noaudio_`)
- Skips files where output already exists
- Validates directory and ffmpeg availability before processing
- Prints per-file status + final summary
- Publishes each completed output atomically; failures and timeouts do not leave
  a partial `noaudio_` file that a later run could mistake for success
- Preserves existing outputs, including files created by another process during conversion

## Requirements
```
Python 3.8 or newer
ffmpeg installed and in PATH
```

## Usage
```bash
python noaudio_secure.py
# Enter directory path when prompted
```

The converter runs locally. GitHub Pages hosts its documentation and source;
it does not process videos or upload media.

Each conversion has a five-minute timeout and uses a temporary file beside the
destination. Only a successful, non-empty FFmpeg output is published. Temporary
files are removed after failures, timeouts and keyboard interrupts. An abrupt
process or machine termination may leave a `.noaudio-` temporary file; these
files are not completed outputs. The input videos are preserved.

Existing `noaudio_` outputs are skipped without an integrity check. This includes
files made by older versions; inspect a questionable existing output before
manually moving it aside for another run. On non-Windows systems, the output
filesystem must support hard links for atomic publication without replacement.
Unsupported publication fails without replacing an existing output.

The command exits with status `1` if any video fails, a dependency/input check
fails, or processing is interrupted. Successful processing or choosing not to
start exits with status `0`.

The legacy `noaudio.py` is a disabled reference entry point that exits with a
message. Use `noaudio_secure.py`.

## Checks

```bash
python -B -m unittest discover -s tests -v
```

Tests use temporary synthetic files and fake FFmpeg results. They cover output
publication, failure/timeout cleanup, existing/concurrent output preservation,
batch counts and failure exit status. CI runs them on Windows and Linux.

## Installation (ffmpeg)
- Windows: `choco install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
