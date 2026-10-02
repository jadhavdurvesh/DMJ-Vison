from vision_system.vision.tracker import BoundingBox, Detection, IoUTracker, iou


def test_iou_for_identical_boxes_is_one():
    box = BoundingBox(0, 0, 10, 10)
    assert iou(box, box) == 1.0


def test_tracker_keeps_id_for_overlapping_detection():
    tracker = IoUTracker(iou_threshold=0.2, max_missed_frames=2)
    first = tracker.update([Detection(BoundingBox(0, 0, 10, 10), 0.9)])
    second = tracker.update([Detection(BoundingBox(1, 1, 11, 11), 0.85)])
    assert len(first) == len(second) == 1
    assert first[0].id == second[0].id
    assert second[0].missed_frames == 0
    assert second[0].age == 2


def test_tracker_expires_missing_track():
    tracker = IoUTracker(iou_threshold=0.2, max_missed_frames=1)
    first = tracker.update([Detection(BoundingBox(0, 0, 10, 10), 0.9)])
    tracker.update([])
    remaining = tracker.update([])
    assert first[0].id not in {track.id for track in remaining}


def test_tracker_creates_distinct_ids_for_non_overlapping_people():
    tracker = IoUTracker(iou_threshold=0.5)
    tracks = tracker.update([
        Detection(BoundingBox(0, 0, 10, 10), 0.9),
        Detection(BoundingBox(30, 30, 40, 40), 0.8),
    ])
    assert len(tracks) == 2
    assert len({track.id for track in tracks}) == 2
