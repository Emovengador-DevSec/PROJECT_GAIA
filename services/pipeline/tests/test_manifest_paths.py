import json
from pathlib import PurePosixPath

import pytest
from fastapi.testclient import TestClient

from sarlab_pipeline.publish import manifest
from sarlab_pipeline.publish.paths import local_cog


def test_foreign_paths_and_migration_remain_within_processed(tmp_path, monkeypatch):
    root = tmp_path / "03_processed"
    file = root / "test/gcov/period/before.tif"
    file.parent.mkdir(parents=True)
    file.write_bytes(b"test")
    relative = file.relative_to(root).as_posix()
    foreign = "C:\\another\\GAIA\\data\\03_processed\\" + relative.replace("/", "\\")
    assert local_cog(foreign, root) == file.resolve()
    assert local_cog("/another/GAIA/data/03_processed/" + relative, root) == file.resolve()
    assert local_cog(relative, root) == file.resolve()
    monkeypatch.setattr(manifest.settings, "PROCESSED", root)
    document = {"cog_path": foreign, "comparison": {"before_cog_path": str(file)}}
    path = file.with_name("manifest_test.json")
    path.write_text(json.dumps(document))
    assert manifest.fix_manifests() == {"updated": 1}
    migrated = json.loads(path.read_text())
    assert migrated["cog_path"] == relative
    assert not PurePosixPath(migrated["comparison"]["before_cog_path"]).is_absolute()
    assert manifest.fix_manifests() == {"updated": 0}
    for unsafe in ("../outside.tif", str(tmp_path / "outside.tif"),
                   "C:/old/data/03_processed/../outside.tif"):
        with pytest.raises(ValueError):
            local_cog(unsafe, root)


def test_api_serves_foreign_manifest_and_rejects_outside_paths(tmp_path, monkeypatch):
    from app import main
    from conftest import make_synthetic_gcov
    from sarlab_pipeline import settings, workflows
    from sarlab_pipeline.config import AOI, Thresholds

    template = "NISAR_L2_PR_GCOV_005_172_A_008_2005_DHDH_A_{d}T024618_{d}T024652_X05007_N_F_J_001.h5"
    before = make_synthetic_gcov(tmp_path / template.format(d="20251122"), seed=1)
    after = make_synthetic_gcov(tmp_path / template.format(d="20260310"), seed=2, clearing=True)
    aoi = AOI(id="test", name="test", role="flagship", status="confirmed",
              bbox=(-70.29, -12.70, -70.18, -12.62), phenomena=["deforestation"])
    monkeypatch.setattr(workflows, "load_aois", lambda: {"test": aoi})
    monkeypatch.setattr(workflows, "load_thresholds", lambda: Thresholds(min_alert_pixels=20))
    monkeypatch.setattr(settings, "PROCESSED", tmp_path / "03_processed")
    monkeypatch.setattr(main, "PROCESSED", settings.PROCESSED)
    result = workflows.change_between("test", before, after)
    path = settings.PROCESSED / result["manifest"]["cog_path"]
    doc = result["manifest"]
    doc["comparison"]["before_cog_path"] = (
        "C:/previous/GAIA/data/03_processed/" + doc["comparison"]["before_cog_path"]
    )
    path.with_name("manifest_hvhv.json").write_text(json.dumps(doc))
    client = TestClient(main.app)
    response = client.get(f"/api/tiles/{doc['id']}/before/0/0/0.png")
    assert response.status_code == 200 and response.content.startswith(b"\x89PNG")
    doc["comparison"]["before_cog_path"] = str(tmp_path / "outside.tif")
    path.with_name("manifest_hvhv.json").write_text(json.dumps(doc))
    assert client.get(f"/api/tiles/{doc['id']}/before/0/0/0.png").status_code == 404
