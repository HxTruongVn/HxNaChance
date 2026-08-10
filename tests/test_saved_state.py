import numpy as np

from workshops.photo.document import Document


def img(value):
    return np.full((4, 4, 3), value, dtype=np.uint8)


def test_save_state_preserves_current_cursor_and_history(tmp_path):
    doc = Document("input.jpg", img(0))
    doc.apply("step1", {"x": 1}, img(1))
    doc.apply("step2", {"x": 2}, img(2))
    doc.undo()  # Save step1 as the current output while keeping step2 for redo.

    path = tmp_path / "work.nachance-state"
    doc.save_state(path, workshop_id="photo", workshop_state={"preset": "13x18"})

    restored, manifest = Document.load_state(path)
    assert restored.cursor == 0
    assert len(restored.steps) == 2
    assert restored.can_redo()
    assert np.array_equal(restored.current_image, img(1))
    assert manifest["workshop_id"] == "photo"
    assert manifest["workshop_state"]["preset"] == "13x18"
