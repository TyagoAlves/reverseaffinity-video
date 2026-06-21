import subprocess
import json
import os
import re
import numpy as np


_metadata_cache = {}


def get_metadata(filepath):
    if filepath in _metadata_cache:
        return _metadata_cache[filepath].copy()

    if not os.path.isfile(filepath):
        return None

    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        meta = {'duration': 0.0, 'width': 0, 'height': 0, 'fps': 0.0,
                'codec': '', 'audio_codec': '', 'bitrate': 0}

        fmt = data.get('format', {})
        duration_str = fmt.get('duration', '0')
        meta['duration'] = float(duration_str) if duration_str else 0.0
        bitrate_str = fmt.get('bit_rate', '0')
        meta['bitrate'] = int(bitrate_str) if bitrate_str else 0

        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            if codec_type == 'video' and meta['width'] == 0:
                meta['width'] = stream.get('width', 0)
                meta['height'] = stream.get('height', 0)
                meta['codec'] = stream.get('codec_name', '')
                r_frame_rate = stream.get('r_frame_rate', '0/1')
                parts = r_frame_rate.split('/')
                if len(parts) == 2 and int(parts[1]) != 0:
                    meta['fps'] = float(int(parts[0])) / float(int(parts[1]))
                if meta['duration'] == 0.0:
                    dur = stream.get('duration', '0')
                    meta['duration'] = float(dur) if dur else 0.0
            elif codec_type == 'audio' and meta['audio_codec'] == '':
                meta['audio_codec'] = stream.get('codec_name', '')

        _metadata_cache[filepath] = meta.copy()
        return meta

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError,
            json.JSONDecodeError, FileNotFoundError, OSError):
        return None


def _check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_frame(filepath, time_seconds, width, height):
    if not _check_ffmpeg():
        return None
    if not os.path.isfile(filepath):
        return None

    try:
        cmd = [
            'ffmpeg', '-ss', str(time_seconds),
            '-i', filepath,
            '-vframes', '1',
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-s', f'{width}x{height}',
            '-'
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode != 0 or len(result.stdout) == 0:
            return None

        expected_size = width * height * 3
        raw = result.stdout[:expected_size]
        if len(raw) < expected_size:
            return None

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        return frame

    except (subprocess.TimeoutExpired, OSError):
        return None


def extract_frames_batch(filepath, times, width, height):
    if not times:
        return []

    if not _check_ffmpeg():
        return [None] * len(times)
    if not os.path.isfile(filepath):
        return [None] * len(times)

    frames = []
    for t in times:
        frames.append(extract_frame(filepath, t, width, height))
    return frames


class FrameSequence:
    def __init__(self, filepath, width, height, fps=None):
        self.filepath = filepath
        self.width = width
        self.height = height
        self._proc = None
        self._pipe = None
        self._frame_size = width * height * 3
        self._closed = False

        if fps is None:
            meta = get_metadata(filepath)
            self.fps = meta['fps'] if meta else 30.0
        else:
            self.fps = float(fps)

        if not os.path.isfile(filepath):
            self._closed = True
            return

        if not _check_ffmpeg():
            self._closed = True
            return

        self._open_pipe()

    def _open_pipe(self):
        cmd = [
            'ffmpeg',
            '-i', self.filepath,
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-s', f'{self.width}x{self.height}',
            '-'
        ]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**6
        )
        self._pipe = self._proc.stdout

    def read(self):
        if self._closed or self._pipe is None:
            return None

        raw = self._pipe.read(self._frame_size)
        if not raw or len(raw) < self._frame_size:
            return None

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((self.height, self.width, 3))
        return frame

    def seek(self, time):
        self.close()
        if not _check_ffmpeg():
            self._closed = True
            return

        cmd = [
            'ffmpeg',
            '-ss', str(time),
            '-i', self.filepath,
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb24',
            '-s', f'{self.width}x{self.height}',
            '-'
        ]
        self._proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**6
        )
        self._pipe = self._proc.stdout
        self._closed = False

    def __iter__(self):
        return self

    def __next__(self):
        frame = self.read()
        if frame is None:
            raise StopIteration
        return frame

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._proc = None
        self._pipe = None

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
