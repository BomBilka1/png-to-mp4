"""Real FFmpeg conversion checks; no desktop session is required."""
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image
import convert_v8 as app


class GifTests(unittest.TestCase):
    def test_time_validation(self):
        self.assertEqual(app._gif_time('1:02,5'), 62.5)
        self.assertEqual(app._gif_time('01:02:03'), 3723)
        self.assertIsNone(app._gif_time('', optional=True))
        for value in ('', '-1', 'nan', 'inf', '1:60', 'abc', '1:2:3:4'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app._gif_time(value)

    @unittest.skipUnless(app.FFMPEG_AVAILABLE, 'FFmpeg not available')
    def test_clip_frames_size_and_no_upscale(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = str(Path(tmp) / 'video with spaces.mp4')
            subprocess.run([app.FFMPEG_PATH, '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=640x360:rate=24', '-t', '3',
                            '-c:v', 'mpeg4', source], check=True, timeout=30)
            before = Path(source).read_bytes()
            output = str(Path(tmp) / 'clip.gif')
            subprocess.run(app._gif_command(app.FFMPEG_PATH, source, output,
                                           0.5, 2.5, 320, 10), check=True, timeout=30)
            with Image.open(output) as gif:
                self.assertEqual(gif.size, (320, 180))
                self.assertEqual(gif.n_frames, 20)
                self.assertEqual(gif.info['loop'], 0)
                duration = 0
                for i in range(gif.n_frames):
                    gif.seek(i)
                    duration += gif.info['duration']
                self.assertAlmostEqual(duration, 2000, delta=100)
            subprocess.run(app._gif_command(app.FFMPEG_PATH, source, output,
                                           2, None, 960, 5), check=True, timeout=30)
            with Image.open(output) as gif:
                self.assertEqual(gif.size, (640, 360))
                self.assertEqual(gif.n_frames, 5)
            self.assertEqual(Path(source).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
