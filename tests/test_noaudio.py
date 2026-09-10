"""Exercise conversion failures with synthetic files and a fake FFmpeg process."""
import contextlib
import io
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import noaudio_secure as audio


class AudioOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'synthetic input.mp4'
        self.source.write_bytes(b'synthetic original video')
        self.output = self.root / 'noaudio_synthetic input.mp4'
        self.console = io.StringIO()

    def convert(self, fake):
        with patch.object(audio.subprocess, 'run', side_effect=fake) as process:
            result = audio.remove_audio_from_video(self.source, self.output)
        self.assertEqual(self.source.read_bytes(), b'synthetic original video')
        return result, process

    def test_success_publishes_finished_file_and_cleans_staging(self):
        def success(command, **kwargs):
            self.assertEqual(kwargs['timeout'], 300)
            self.assertIn('-nostdin', command)
            target = Path(command[-2])
            self.assertNotEqual(target, self.output)
            self.assertFalse(self.output.exists())
            target.write_bytes(b'complete muted video')
            return subprocess.CompletedProcess(command, 0, '', '')

        result, _ = self.convert(success)
        self.assertEqual(result, (True, 'Success'))
        self.assertEqual(self.output.read_bytes(), b'complete muted video')
        self.assertEqual(set(self.root.iterdir()), {self.source, self.output})

    def test_failed_conversion_leaves_no_completed_output(self):
        def failure(command, **kwargs):
            Path(command[-2]).write_bytes(b'incomplete video')
            return subprocess.CompletedProcess(command, 1, '', 'synthetic conversion error')

        result, _ = self.convert(failure)
        self.assertFalse(result[0])
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_timeout_removes_only_its_temporary_file(self):
        def timeout(command, **kwargs):
            Path(command[-2]).write_bytes(b'incomplete video')
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])

        result, _ = self.convert(timeout)
        self.assertFalse(result[0])
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_existing_output_is_preserved_without_starting_ffmpeg(self):
        self.output.write_bytes(b'existing user output')
        result, process = self.convert(AssertionError('Must not start FFmpeg'))
        self.assertFalse(result[0])
        process.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b'existing user output')

    def test_empty_success_is_not_published(self):
        result, _ = self.convert(lambda command, **kwargs: subprocess.CompletedProcess(command, 0, '', ''))
        self.assertFalse(result[0])
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_interrupt_cleans_staging_and_propagates(self):
        def interrupt(command, **kwargs):
            Path(command[-2]).write_bytes(b'incomplete video')
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            self.convert(interrupt)
        self.assertEqual(list(self.root.iterdir()), [self.source])
        self.assertEqual(self.source.read_bytes(), b'synthetic original video')

    def test_output_created_during_conversion_is_not_overwritten(self):
        def race(command, **kwargs):
            Path(command[-2]).write_bytes(b'new muted video')
            self.output.write_bytes(b'concurrent user output')
            return subprocess.CompletedProcess(command, 0, '', '')

        result, _ = self.convert(race)
        self.assertFalse(result[0])
        self.assertEqual(self.output.read_bytes(), b'concurrent user output')
        self.assertEqual(set(self.root.iterdir()), {self.source, self.output})

    def test_directory_reports_failures_and_preserves_existing_outputs(self):
        other = self.root / 'other.MOV'
        other.write_bytes(b'synthetic other')
        self.output.write_bytes(b'existing output')
        (self.root / '.noaudio-interrupted.mp4').write_bytes(b'old incomplete temporary video')
        with patch.object(audio, 'remove_audio_from_video', return_value=(False, 'synthetic error')) as convert:
            with contextlib.redirect_stdout(self.console):
                counts = audio.process_directory(self.root)
        self.assertEqual(counts, {'processed': 0, 'failed': 1, 'skipped': 3})
        convert.assert_called_once_with(other, self.root / 'noaudio_other.MOV')

    def test_cli_reports_failed_batch_with_nonzero_exit(self):
        with patch.object(audio, 'check_ffmpeg', return_value=True), \
                patch.object(audio, 'validate_directory', return_value=self.root), \
                patch.object(audio, 'process_directory', return_value={'processed': 0, 'failed': 1, 'skipped': 0}), \
                patch('builtins.input', side_effect=[str(self.root), 'yes']), \
                contextlib.redirect_stdout(self.console):
            with self.assertRaises(SystemExit) as raised:
                audio.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertNotIn('Done!', self.console.getvalue())


if __name__ == '__main__':
    unittest.main()
