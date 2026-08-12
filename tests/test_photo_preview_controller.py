import threading

from workshops.photo.preview_controller import PhotoPreviewController


class _Owner:
    def __init__(self):
        self.engine = None

    def after(self, _delay, callback):
        callback()


def test_preview_revision_discards_stale_result():
    owner = _Owner()
    first_started = threading.Event()
    release_first = threading.Event()
    calls = []

    class Engine:
        def __init__(self):
            self.count = 0

        def process(self, *_args, **_kwargs):
            self.count += 1
            if self.count == 1:
                first_started.set()
                release_first.wait(timeout=2)
                return {"success": True, "image": "OLD"}
            return {"success": True, "image": "NEW"}

    owner.engine = Engine()
    controller = PhotoPreviewController(owner)

    first = controller.request("source.jpg", object(), (255, 255, 255), {},
                               lambda revision, image, error: calls.append((revision, image, error)))
    assert first_started.wait(timeout=2)

    second = controller.request("source.jpg", object(), (255, 255, 255), {},
                                lambda revision, image, error: calls.append((revision, image, error)))
    release_first.set()

    # Give both daemon workers a chance to finish.
    for _ in range(100):
        if calls:
            if any(image == "NEW" for _, image, _ in calls):
                break
        threading.Event().wait(0.01)

    assert second > first
    assert any(revision == second and image == "NEW" for revision, image, _ in calls)
    assert not any(revision == first and image == "OLD" for revision, image, _ in calls)


def test_invalidate_moves_revision_forward():
    controller = PhotoPreviewController(_Owner())
    assert controller.revision == 0
    assert controller.invalidate() == 1
    assert controller.revision == 1
