"""Resolve published rasters within the local processed-data directory."""
from pathlib import Path, PurePosixPath, PureWindowsPath


def local_cog(value: str, processed: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Ruta de capa ausente")
    normalized = value.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if ".." in parts or "\0" in normalized:
        raise ValueError("Ruta de capa inválida")
    root = processed.resolve()
    absolute = PurePosixPath(normalized).is_absolute() or PureWindowsPath(value).is_absolute()
    candidate = Path(normalized).resolve() if absolute else (root / normalized).resolve()
    if absolute and not candidate.is_relative_to(root) and "03_processed" in parts:
        candidate = root.joinpath(*parts[parts.index("03_processed") + 1:]).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError("El archivo procesado no está disponible localmente")
    return candidate


def relative_cog(value: str | Path, processed: Path) -> str:
    return local_cog(str(value), processed).relative_to(processed.resolve()).as_posix()
