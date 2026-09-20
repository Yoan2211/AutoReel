from math import hypot

from .model import Track


class SubjectTracker:
    def __init__(self, lost_hold_us: int):
        self.lost_hold_us = lost_hold_us
        self.tracks = []
        self.next_id = 1

    def reset(self):
        self.tracks = []

    def update(self, source_us, detections):
        unmatched = set(range(len(detections)))
        for track in self.tracks:
            tx, ty = track.detection.center
            candidates = [(hypot(tx-detections[i].center[0], ty-detections[i].center[1]), i)
                          for i in unmatched if detections[i].kind == track.detection.kind]
            if candidates and min(candidates)[0] <= 0.25:
                _, index = min(candidates); track.detection = detections[index]
                track.last_seen_us = source_us; track.missed = 0; unmatched.remove(index)
            else:
                track.missed += 1
        for index in unmatched:
            self.tracks.append(Track(self.next_id, detections[index], source_us)); self.next_id += 1
        self.tracks = [track for track in self.tracks
                       if source_us - track.last_seen_us <= self.lost_hold_us]
        return [(track.id, track.detection, source_us != track.last_seen_us) for track in self.tracks]
