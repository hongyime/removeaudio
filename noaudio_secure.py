#!/usr/bin/env python3
"""
Secure video audio removal tool
Fixes: Command injection, path traversal, error handling
"""
import subprocess
import os
import sys
from pathlib import Path
import tempfile

POSSIBLE_EXTENSIONS = ["avi", "mp4", "mov"]

def validate_directory(directory_path):
    """Validate and sanitize directory path"""
    try:
        # Convert to absolute path and resolve symlinks
        path = Path(directory_path).resolve()
        
        # Check if directory exists
        if not path.exists():
            print(f"❌ Error: Directory does not exist: {path}")
            return None
        
        # Check if it's actually a directory
        if not path.is_dir():
            print(f"❌ Error: Path is not a directory: {path}")
            return None
        
        # Check read permissions
        if not os.access(path, os.R_OK):
            print(f"❌ Error: No read permission for directory: {path}")
            return None
        
        return path
    except Exception as e:
        print(f"❌ Error validating directory: {e}")
        return None

def check_ffmpeg():
    """Check if ffmpeg is installed and accessible"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True
        else:
            print("❌ Error: ffmpeg is installed but not working correctly")
            return False
    except FileNotFoundError:
        print("❌ Error: ffmpeg is not installed or not in PATH")
        print("Please install ffmpeg:")
        print("  Windows: choco install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ Error checking ffmpeg: {e}")
        return False

def remove_audio_from_video(input_path, output_path):
    """
    Remove audio from video file using ffmpeg
    Uses secure subprocess call with list arguments
    """
    temporary_path = None
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.is_file():
            return False, "Input is not a readable video file"
        if output_path.exists() or output_path.is_symlink():
            return False, "Output already exists; it was preserved"

        # Stage beside the destination so publication stays on one filesystem.
        descriptor, name = tempfile.mkstemp(
            prefix='.noaudio-', suffix=output_path.suffix, dir=output_path.parent
        )
        os.close(descriptor)
        temporary_path = Path(name)

        # Build command as list (prevents command injection)
        command = [
            "ffmpeg",
            "-nostdin",
            "-i", str(input_path),
            "-c", "copy",
            "-an",
            str(temporary_path),
            "-y"  # Only overwrite this invocation's newly created staging file
        ]
        
        # Execute with shell=False (secure)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                return False, "FFmpeg did not produce a non-empty video"
            # Both operations fail if another writer created the destination.
            # POSIX rename would overwrite it, so use an atomic hard link there.
            if os.name == 'nt':
                os.rename(temporary_path, output_path)
            else:
                os.link(temporary_path, output_path)
            return True, "Success"
        else:
            return False, f"ffmpeg error: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, "Timeout: Video processing took too long"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                print(f"⚠️ Could not remove temporary output: {temporary_path}")

def process_directory(directory):
    """Process all video files in directory"""
    processed = 0
    failed = 0
    skipped = 0
    
    print(f"🔍 Searching for video files in: {directory}")
    print(f"📹 Looking for extensions: {', '.join(POSSIBLE_EXTENSIONS)}")
    print()
    
    # Walk through directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # Check if file has valid extension
            if '.' not in filename:
                continue
            
            ext = filename.rsplit('.', 1)[-1].lower()
            if ext not in POSSIBLE_EXTENSIONS:
                continue
            
            # Skip files that already have "noaudio_" prefix
            if filename.startswith(("noaudio_", ".noaudio-")):
                skipped += 1
                continue
            
            # Build paths
            input_path = Path(root) / filename
            output_filename = f"noaudio_{filename}"
            output_path = Path(root) / output_filename
            
            # Check if output file already exists
            if output_path.exists():
                print(f"⏭️  Skipping (output exists): {filename}")
                skipped += 1
                continue
            
            print(f"🎬 Processing: {filename}")
            
            # Remove audio
            success, message = remove_audio_from_video(input_path, output_path)
            
            if success:
                print(f"✅ Success: {output_filename}")
                processed += 1
            else:
                print(f"❌ Failed: {filename} - {message}")
                failed += 1
            
            print()
    
    # Summary
    print("=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Processed successfully: {processed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📁 Total files: {processed + failed + skipped}")
    print()
    return {"processed": processed, "failed": failed, "skipped": skipped}

def main():
    """Main execution flow"""
    print("=" * 60)
    print("🎬 VIDEO AUDIO REMOVAL TOOL")
    print("=" * 60)
    print()
    
    # Check ffmpeg
    print("🔧 Checking dependencies...")
    if not check_ffmpeg():
        sys.exit(1)
    print("✅ ffmpeg is installed and working")
    print()
    
    # Get directory from user
    directory_input = input("📁 Enter directory path containing video files: ").strip()
    
    # Validate directory
    directory = validate_directory(directory_input)
    if directory is None:
        sys.exit(1)
    
    print(f"✅ Directory validated: {directory}")
    print()
    
    # Confirm before processing
    response = input("⚠️  This will create new files with 'noaudio_' prefix. Continue? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled by user")
        sys.exit(0)
    
    print()
    
    # Process directory
    try:
        counts = process_directory(directory)
        if counts["failed"]:
            print("❌ Some videos failed; completed outputs were preserved.")
            sys.exit(1)
        print("✅ Done!")
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
