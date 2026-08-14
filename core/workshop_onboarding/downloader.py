from __future__ import annotations

import hashlib
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlparse

from .resource_gate import ResourceGateRecord, ResourceGateState, ResourceTestGate


class ResourceDownloadError(RuntimeError):
    """A resource could not be downloaded or safely staged."""


@dataclass(frozen=True)
class DownloadResult:
    resource_id: str
    record: ResourceGateRecord | None
    downloaded: bool
    reused: bool
    errors: tuple[str, ...] = ()


Fetcher = Callable[[str, Path, int], None]


class CoreResourceDownloader:
    """Download external resources into Core's intake quarantine.

    This class deliberately never writes to ``canonical``. A resource becomes
    canonical only when ResourceTestGate.approve() is called after testing.
    """

    def __init__(
        self,
        gate: ResourceTestGate,
        *,
        max_bytes: int = 8 * 1024 * 1024 * 1024,
        timeout_seconds: int = 120,
        fetcher: Fetcher | None = None,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self.gate = gate
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.fetcher = fetcher or self._fetch_http

    @staticmethod
    def _safe_filename(resource_id: str, filename: str | None) -> str:
        candidate = Path(filename or resource_id.rsplit("::", 1)[-1]).name
        candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
        if not candidate:
            raise ResourceDownloadError(f"cannot derive safe filename for {resource_id}")
        return candidate

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ResourceDownloadError(f"unsupported resource URL: {url}")

    def _fetch_http(self, url: str, destination: Path, max_bytes: int) -> None:
        self._validate_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": "HxNaChance-Core/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise ResourceDownloadError(f"resource exceeds limit: {url}")
                written = 0
                with destination.open("wb") as stream:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > max_bytes:
                            raise ResourceDownloadError(f"resource exceeds limit: {url}")
                        stream.write(chunk)
        except ResourceDownloadError:
            raise
        except Exception as exc:
            raise ResourceDownloadError(f"download failed for {url}: {exc}") from exc

    def _existing_record(self, resource_id: str) -> DownloadResult | None:
        record = self.gate.get(resource_id)
        if record is None:
            return None
        path = Path(record.source_path)
        if not path.is_file() or not record.sha256:
            return None
        actual = self.gate.sha256_file(path)
        if actual != record.sha256:
            if record.state is ResourceGateState.APPROVED:
                raise ResourceDownloadError(f"canonical resource was modified: {resource_id}")
            return None
        return DownloadResult(resource_id, record, downloaded=False, reused=True)

    def download(
        self,
        resource_id: str,
        sources: Iterable[str | dict],
        *,
        expected_sha256: str | None = None,
        filename: str | None = None,
    ) -> DownloadResult:
        """Stage a resource in intake, trying sources in order.

        ``expected_sha256`` is optional. When present it is verified by the
        ResourceTestGate; when absent Core records the discovered checksum.
        """
        reused = self._existing_record(resource_id)
        if reused is not None:
            return reused

        urls: list[str] = []
        for source in sources:
            url = source.get("url") if isinstance(source, dict) else source
            if url:
                urls.append(str(url))
        if not urls:
            raise ResourceDownloadError(f"no source URL for {resource_id}")

        safe_name = self._safe_filename(resource_id, filename)
        work_dir = self.gate.intake_dir / "_downloads"
        work_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []
        for index, url in enumerate(urls):
            part = work_dir / f"{resource_id.replace('::', '__')}.{index}.{safe_name}.part"
            try:
                if part.exists():
                    part.unlink()
                self.fetcher(url, part, self.max_bytes)
                if not part.is_file() or part.stat().st_size == 0:
                    raise ResourceDownloadError("download produced no file")
                # Gate intake copies the completed file and computes its hash.
                record = self.gate.intake(part, resource_id, expected_sha256=expected_sha256)
                part.unlink(missing_ok=True)
                if record.state is ResourceGateState.FAILED:
                    raise ResourceDownloadError(f"checksum verification failed: {record.error or 'verification failed'}")
                return DownloadResult(resource_id, record, downloaded=True, reused=False)
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                part.unlink(missing_ok=True)
        raise ResourceDownloadError(f"all sources failed for {resource_id}: {'; '.join(errors)}")

    def download_many(self, resources: Iterable[dict]) -> list[DownloadResult]:
        results: list[DownloadResult] = []
        for item in resources:
            resource_id = str(item.get("resource_id") or item.get("id") or "").strip()
            if not resource_id:
                raise ResourceDownloadError("resource item is missing resource_id")
            sources = item.get("sources") or item.get("source_urls") or []
            results.append(self.download(
                resource_id,
                sources,
                expected_sha256=item.get("sha256") or item.get("expected_sha256"),
                filename=item.get("filename"),
            ))
        return results
