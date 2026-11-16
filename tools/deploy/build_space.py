"""Assemble a Hugging Face Docker Space (deploy/space/) from the code and deploy/data/.

Run tools/deploy/collect_runtime_data.py first. The result is a folder ready to be pushed
to https://huggingface.co/spaces/<user>/<space>. Secrets never go in this folder: the
Cesium token and server keys are set as Space secrets.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "deploy"

# (source, destination) relative to the repository / Space root.
TREES = [
    ("apps/web/src", "apps/web/src"),
    ("apps/web/public", "apps/web/public"),
    ("services/api/app", "services/api/app"),
    ("services/pipeline/src", "services/pipeline/src"),
    ("config", "config"),
    ("deploy/data", "deploy/data"),
]
FILES = [
    "Dockerfile", ".dockerignore", "pyproject.toml", "uv.lock", "LICENSE",
    "apps/web/package.json", "apps/web/package-lock.json", "apps/web/index.html",
    "apps/web/tsconfig.json", "apps/web/vite.config.ts",
]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", ".env.*", "*.h5", "*.hdf5", ".mcp.json", "node_modules")
BINARY = ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.mp4", "*.webm",
          "*.wav", "*.mp3", "*.pdf", "*.glb", "*.ktx2", "*.woff2", "*.ico")

README = """---
title: GAIA RIKCHAY
emoji: 🌎
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: {license}
short_description: NASA NISAR radar turned into nature-based action for the Andes
---

# GAIA RIKCHAY · PROJECT GAIA

NASA Space Apps Challenge 2026 · *Dancing with the SARs*.

GAIA RIKCHAY turns real NASA-ISRO NISAR radar data into clear answers about land change in
Ayacucho (Peru): where vegetation was lost, why, and which native plants and community work
(minka) can heal each zone. NISAR is shown separately from complementary sources
(NASA FIRMS, USGS, OPERA, SoilGrids, Open-Meteo, iNaturalist).

NISAR products are provisional. This is a monitoring aid, not an official alert.

Source code: {repo}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEPLOY / "space")
    parser.add_argument("--repo", default="(GitHub link)", help="Public code repository URL for the README.")
    parser.add_argument("--license", default="mit")
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(DEPLOY.resolve()) or out == DEPLOY.resolve():
        parser.error("El destino debe ser una carpeta dentro de deploy/.")
    if not (DEPLOY / "data").is_dir():
        parser.error("Falta deploy/data/: ejecuta antes tools/deploy/collect_runtime_data.py.")

    # Keep an existing Space clone's .git so updates are a normal commit + push.
    git = out / ".git"
    keep = out.parent / f".{out.name}-git"
    if git.exists():
        shutil.move(git, keep)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    if keep.exists():
        shutil.move(keep, git)

    for src, dst in TREES:
        shutil.copytree(ROOT / src, out / dst, ignore=SKIP)
    for name in FILES:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)

    (out / "README.md").write_text(README.format(repo=args.repo, license=args.license), encoding="utf-8")
    # Binary files and anything over 5 MB go through Git LFS / Xet (Hugging Face rejects big plain files).
    large = sorted(p.relative_to(out).as_posix() for p in out.rglob("*")
                   if p.is_file() and ".git" not in p.parts and p.stat().st_size > 5_000_000
                   and not any(p.match(b) for b in BINARY))
    lines = [f"{pattern} filter=lfs diff=lfs merge=lfs -text" for pattern in BINARY]
    lines += [f"{path.replace(' ', '[[:space:]]')} filter=lfs diff=lfs merge=lfs -text" for path in large]
    (out / ".gitattributes").write_text("\n".join(lines) + "\n", encoding="utf-8")

    files = [p for p in out.rglob("*") if p.is_file() and ".git" not in p.parts]
    size = sum(p.stat().st_size for p in files)
    print(f"{len(files)} archivos · {size / 1_000_000:.1f} MB · {len(large)} archivos grandes no binarios en LFS · {out}")


if __name__ == "__main__":
    main()
