"""Arranca API y web compilada desde un único servidor, con modo local explícito."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="GAIA Alerta · servidor local de la demo")
    parser.add_argument("--offline", action="store_true", help="Usar la última caché de observaciones")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not (root / "apps/web/dist/index.html").is_file():
        parser.error("Compila primero la web con npm --prefix apps/web run build.")
    if not 1024 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1024 y 65535.")
    os.environ["SARLAB_ROOT"] = str(root)
    if args.offline:
        os.environ["SARLAB_OFFLINE"] = "1"
    print(f"GAIA Alerta disponible en http://127.0.0.1:{args.port}")
    sys.path.insert(0, str(root / "services" / "api"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
