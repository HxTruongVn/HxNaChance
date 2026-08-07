"""Unit test cho Document/PipelineStep (workshops/photo/document.py) —
Giai đoạn 11. Thuần logic, không phụ thuộc GPU/weights — dùng mảng
numpy giả lập ảnh, không đọc file thật.
"""
import numpy as np
import pytest

from workshops.photo.document import Document, MAX_HISTORY


def _fake_image(value: int = 0):
    return np.full((4, 4, 3), value, dtype=np.uint8)


def test_new_document_starts_at_original():
    doc = Document(source_path="fake.jpg", original_image=_fake_image(1))
    assert doc.cursor == -1
    assert doc.can_undo() is False
    assert doc.can_redo() is False
    assert np.array_equal(doc.current_image, _fake_image(1))


def test_apply_advances_cursor_and_image():
    doc = Document(source_path="fake.jpg", original_image=_fake_image(0))
    doc.apply("upscale", {"outscale": 2.0}, _fake_image(1))
    doc.apply("face_restore", {"fidelity": 0.7}, _fake_image(2))

    assert doc.cursor == 1
    assert doc.step_labels() == ["upscale", "face_restore"]
    assert np.array_equal(doc.current_image, _fake_image(2))
    assert doc.can_undo() is True
    assert doc.can_redo() is False


def test_undo_redo_roundtrip():
    doc = Document(source_path="fake.jpg", original_image=_fake_image(0))
    doc.apply("upscale", {}, _fake_image(1))
    doc.apply("face_restore", {}, _fake_image(2))

    assert doc.undo() is True
    assert np.array_equal(doc.current_image, _fake_image(1))
    assert doc.can_redo() is True

    assert doc.undo() is True
    assert np.array_equal(doc.current_image, _fake_image(0))  # ảnh gốc
    assert doc.can_undo() is False
    assert doc.undo() is False  # không lùi được nữa

    assert doc.redo() is True
    assert np.array_equal(doc.current_image, _fake_image(1))


def test_apply_after_undo_cuts_redo_branch():
    doc = Document(source_path="fake.jpg", original_image=_fake_image(0))
    doc.apply("upscale", {}, _fake_image(1))
    doc.apply("face_restore", {}, _fake_image(2))
    doc.undo()  # đang ở bước "upscale", "face_restore" còn có thể redo

    doc.apply("skin_smooth", {}, _fake_image(9))  # chạy bước mới từ giữa lịch sử

    assert doc.step_labels() == ["upscale", "skin_smooth"]  # "face_restore" bị cắt
    assert doc.can_redo() is False


def test_history_limit_drops_oldest_step():
    doc = Document(source_path="fake.jpg", original_image=_fake_image(0))
    for i in range(MAX_HISTORY + 3):
        doc.apply(f"step_{i}", {}, _fake_image(i))

    assert len(doc.steps) == MAX_HISTORY
    # 3 bước đầu tiên đã bị rơi khỏi lịch sử
    assert doc.step_labels()[0] == "step_3"
    assert doc.step_labels()[-1] == f"step_{MAX_HISTORY + 2}"
