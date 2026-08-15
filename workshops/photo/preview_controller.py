"""Photo Workshop preview controller.

Preview is intentionally separate from the production save pipeline.  It keeps
an interaction revision and runs expensive PhotoEngine work off the Tk thread.
The latest revision wins; stale worker results are discarded.
"""
import hashlib
import json
import threading
from collections.abc import Mapping


class PhotoRevisionRegistry:
    """Assign stable revisions to unique Photo states.

    A revision identifies canonical state content, not the number of UI events.
    Therefore A -> B -> A resolves to the original revision for A. Preview
    request generations remain separate so stale worker results can still be
    discarded safely by the UI.
    """

    def __init__(self) -> None:
        self._revisions: dict[str, int] = {}
        self._next_revision = 1

    @staticmethod
    def canonical_state(state):
        def normalize(value):
            if isinstance(value, Mapping):
                return {str(key): normalize(value[key]) for key in sorted(value, key=str)}
            if isinstance(value, (tuple, list)):
                return [normalize(item) for item in value]
            if isinstance(value, float):
                return round(value, 6)
            return value

        return normalize(state)

    @classmethod
    def fingerprint(cls, state) -> str:
        payload = json.dumps(
            cls.canonical_state(state),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def resolve(self, state) -> tuple[int, str, bool]:
        fingerprint = self.fingerprint(state)
        revision = self._revisions.get(fingerprint)
        if revision is not None:
            return revision, fingerprint, False
        revision = self._next_revision
        self._next_revision += 1
        self._revisions[fingerprint] = revision
        return revision, fingerprint, True


class PhotoPreviewController:
    def __init__(self, owner):
        self.owner = owner
        self._revision = 0
        self._worker = None
        self._lock = threading.Lock()

    @property
    def revision(self):
        return self._revision

    def invalidate(self):
        with self._lock:
            self._revision += 1
            return self._revision

    def request(self, image_path, spec, bg_color, options, on_done):
        """Run a preview request; only the newest revision may commit."""
        if not image_path:
            return self.invalidate()

        with self._lock:
            self._revision += 1
            revision = self._revision

        engine = getattr(self.owner, "engine", None)
        if engine is None:
            self.owner.after(0, lambda: on_done(revision, None, "Engine chưa sẵn sàng"))
            return revision

        def worker():
            try:
                result = engine.process(image_path, spec, bg_color, dict(options))
                image = result.get("image") if result.get("success") else None
                error = None if image is not None else "; ".join(result.get("validation_errors", []))
            except Exception as exc:
                image, error = None, str(exc)

            def finish():
                if revision != self._revision:
                    return
                on_done(revision, image, error)

            try:
                self.owner.after(0, finish)
            except Exception:
                pass

        self._worker = threading.Thread(target=worker, name="photo-preview", daemon=True)
        self._worker.start()
        return revision
