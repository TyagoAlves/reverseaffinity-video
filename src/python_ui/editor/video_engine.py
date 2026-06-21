import copy
import uuid


class Clip:
    def __init__(self, clip_id, filepath, start_time=0.0, duration=0.0,
                 in_point=0.0, out_point=0.0, track_id=-1,
                 enabled=True, name=""):
        self.id = clip_id
        self.filepath = filepath
        self.start_time = start_time
        self.duration = duration
        self.in_point = in_point
        self.out_point = out_point
        self.track_id = track_id
        self.enabled = enabled
        self.name = name

    @property
    def end_time(self):
        return self.start_time + self.duration

    @property
    def source_duration(self):
        if self.out_point > self.in_point:
            return self.out_point - self.in_point
        return self.duration

    def copy(self):
        return copy.deepcopy(self)

    def __repr__(self):
        return (f"Clip(id={self.id}, name='{self.name}', "
                f"start={self.start_time}, dur={self.duration})")


class Track:
    def __init__(self, track_id, name="", enabled=True, track_type="video"):
        self.id = track_id
        self.name = name
        self.enabled = enabled
        self.clips = []
        self.type = track_type if track_type in ("video", "audio") else "video"
        self.visible = True
        self.locked = False
        self.muted = False
        self.solo = False
        self.blend_mode = "normal"

    def blend_mode_label(self):
        labels = {
            "normal": "Normal", "multiply": "Multiply", "screen": "Screen",
            "overlay": "Overlay", "darken": "Darken", "lighten": "Lighten",
            "difference": "Diff", "add": "Add", "subtract": "Subtract",
        }
        return labels.get(self.blend_mode, self.blend_mode)

    BLEND_MODES = ["normal", "multiply", "screen", "overlay", "darken",
                   "lighten", "difference", "add", "subtract"]

    def cycle_blend_mode(self):
        idx = self.BLEND_MODES.index(self.blend_mode) if self.blend_mode in self.BLEND_MODES else -1
        self.blend_mode = self.BLEND_MODES[(idx + 1) % len(self.BLEND_MODES)]

    def add_clip(self, clip):
        clip.track_id = self.id
        self.clips.append(clip)
        self.clips.sort(key=lambda c: c.start_time)

    def remove_clip(self, clip_id):
        for i, c in enumerate(self.clips):
            if c.id == clip_id:
                del self.clips[i]
                return True
        return False

    def clip_at(self, time):
        for c in self.clips:
            if c.enabled and c.start_time <= time < c.end_time:
                return c
        return None

    def clips_between(self, start, end):
        result = []
        for c in self.clips:
            if c.enabled and c.start_time < end and c.end_time > start:
                result.append(c)
        return result

    @property
    def duration(self):
        if not self.clips:
            return 0.0
        return max(c.end_time for c in self.clips)

    def copy(self):
        return copy.deepcopy(self)

    def __repr__(self):
        return (f"Track(id={self.id}, name='{self.name}', "
                f"type='{self.type}', clips={len(self.clips)})")


class Timeline:
    def __init__(self):
        self.tracks = []
        self.next_clip_id = 1
        self.next_track_id = 1

    def add_track(self, name, track_type="video"):
        track_id = self.next_track_id
        self.next_track_id += 1
        self.tracks.append(Track(track_id, name=name, track_type=track_type))
        return track_id

    def remove_track(self, track_id):
        for i, t in enumerate(self.tracks):
            if t.id == track_id:
                del self.tracks[i]
                return True
        return False

    def add_clip(self, track_id, filepath, start_time, duration, name=""):
        track = self._find_track(track_id)
        if track is None:
            return None
        clip_id = self.next_clip_id
        self.next_clip_id += 1
        in_point = 0.0
        out_point = duration
        clip = Clip(clip_id, filepath, start_time, duration,
                    in_point, out_point, track_id, True, name)
        track.add_clip(clip)
        return clip_id

    def remove_clip(self, clip_id):
        for track in self.tracks:
            if track.remove_clip(clip_id):
                return True
        return False

    def split_clip(self, clip_id, split_time):
        clip = self.find_clip(clip_id)
        if clip is None:
            return None
        if split_time <= clip.start_time or split_time >= clip.end_time:
            return None
        track = self._find_track(clip.track_id)
        if track is None:
            return None
        new_id = self.next_clip_id
        self.next_clip_id += 1
        right_duration = clip.end_time - split_time
        clip.duration = split_time - clip.start_time
        clip.out_point = clip.in_point + clip.duration
        new_clip = Clip(
            new_id, clip.filepath, split_time, right_duration,
            clip.in_point + clip.duration, clip.in_point + clip.duration + right_duration,
            clip.track_id, clip.enabled, clip.name
        )
        track.add_clip(new_clip)
        return new_id

    def clips_at(self, time):
        result = []
        for track in self.tracks:
            c = track.clip_at(time)
            if c is not None:
                result.append(c)
        return result

    def duration(self):
        if not self.tracks:
            return 0.0
        return max(t.duration for t in self.tracks)

    def find_clip(self, clip_id):
        for track in self.tracks:
            for clip in track.clips:
                if clip.id == clip_id:
                    return clip
        return None

    def get_track(self, track_id):
        return self._find_track(track_id)

    def clear(self):
        self.tracks.clear()
        self.next_clip_id = 1
        self.next_track_id = 1

    def copy(self):
        return copy.deepcopy(self)

    def _find_track(self, track_id):
        for t in self.tracks:
            if t.id == track_id:
                return t
        return None


class VideoMetadata:
    def __init__(self, filepath="", duration=0.0, width=0, height=0,
                 fps=30.0, codec="", audio_codec=""):
        self.filepath = filepath
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.audio_codec = audio_codec

    def __repr__(self):
        return (f"VideoMetadata(file='{self.filepath}', "
                f"{self.width}x{self.height}, {self.fps}fps)")


class TransportState:
    def __init__(self):
        self.playing = False
        self.current_time = 0.0
        self.zoom = 1.0
        self.volume = 1.0
        self.loop = False
        self.snap = True

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def toggle_play(self):
        self.playing = not self.playing

    def seek(self, time):
        self.current_time = max(0.0, time)

    def stop(self):
        self.playing = False
        self.current_time = 0.0

    def reset(self):
        self.playing = False
        self.current_time = 0.0
        self.zoom = 1.0
        self.volume = 1.0
        self.loop = False
        self.snap = True

    def __repr__(self):
        return (f"TransportState(playing={self.playing}, "
                f"time={self.current_time:.2f}, vol={self.volume:.2f})")


class VideoProject:
    def __init__(self, filepath=""):
        self.timeline = Timeline()
        self.transport = TransportState()
        self.media_files = []
        self.filepath = filepath

    def add_media(self, metadata):
        self.media_files.append(metadata)

    def remove_media(self, filepath):
        for i, m in enumerate(self.media_files):
            if m.filepath == filepath:
                del self.media_files[i]
                return True
        return False

    def find_media(self, filepath):
        for m in self.media_files:
            if m.filepath == filepath:
                return m
        return None

    def copy(self):
        return copy.deepcopy(self)

    def __repr__(self):
        return (f"VideoProject(tracks={len(self.timeline.tracks)}, "
                f"media={len(self.media_files)}, file='{self.filepath}')")
