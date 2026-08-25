"""Text extraction helpers for staged file intake, kept intentionally narrow to the MVP file types."""
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".pdf", ".docx"}
MAX_EXTRACTED_CHARS = 50_000


class UnsupportedFileTypeError(ValueError):
    pass


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def extract_text(path: Path, filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type: {suffix or 'unknown'}")

    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    else:
        text = _extract_plain_text(path)

    if text is None:
        return None
    return text[:MAX_EXTRACTED_CHARS]


def _extract_plain_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _extract_pdf(path: Path) -> str | None:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return None


def _extract_docx(path: Path) -> str | None:
    from docx import Document

    try:
        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception:
        return None
