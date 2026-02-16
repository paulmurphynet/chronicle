"""FileSystem implementation of EvidenceStore. Spec Section 4.1."""

from pathlib import Path

EVIDENCE_DIR = "evidence"


def _path_under_root(root: Path, *parts: str) -> Path:
    """Resolve root/parts and ensure it stays under root (prevents path traversal)."""
    root_resolved = root.resolve()
    path = root_resolved.joinpath(*parts).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError:
        raise ValueError("Path escapes project root") from None
    return path


def _extension_from_media_type(media_type: str) -> str:
    """Return a file extension for common MIME types."""
    mapping = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/html": ".html",
        "image/jpeg": ".jpg",
        "image/png": ".png",
    }
    return mapping.get(media_type.split(";")[0].strip(), "")


class FileSystemEvidenceStore:
    """EvidenceStore that writes to project_dir/evidence/."""

    def __init__(self, project_dir: Path | str) -> None:
        self._root = Path(project_dir)
        self._evidence_dir = self._root / EVIDENCE_DIR

    def store(self, evidence_uid: str, file_bytes: bytes, media_type: str) -> str:
        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        ext = _extension_from_media_type(media_type)
        name = evidence_uid + ext
        path = self._evidence_dir / name
        path.write_bytes(file_bytes)
        return f"{EVIDENCE_DIR}/{name}"

    def retrieve(self, uri: str) -> bytes:
        path = _path_under_root(self._root, *Path(uri).parts)
        try:
            path.relative_to(self._evidence_dir.resolve())
        except ValueError:
            raise ValueError("Evidence URI must be under evidence/") from None
        return path.read_bytes()

    def exists(self, uri: str) -> bool:
        path = _path_under_root(self._root, *Path(uri).parts)
        try:
            path.relative_to(self._evidence_dir.resolve())
        except ValueError:
            return False
        return path.is_file()

    def delete(self, uri: str) -> None:
        path = _path_under_root(self._root, *Path(uri).parts)
        try:
            path.relative_to(self._evidence_dir.resolve())
        except ValueError:
            raise ValueError("Evidence URI must be under evidence/") from None
        if path.is_file():
            path.unlink()
