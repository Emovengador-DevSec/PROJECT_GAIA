import sys
from datetime import date
from types import SimpleNamespace

import numpy as np
import pytest
from rasterio.transform import from_origin

from sarlab_pipeline.detection.change import polygons
from sarlab_pipeline.readers.gcov import validate_sequence
from sarlab_pipeline.sources import nisar


def test_search_reads_nisar_file_size_mapping_and_filters_geometry(monkeypatch):
    filename = "NISAR_test.h5"
    props = {"fileID": "NISAR_test", "url": f"https://example.test/{filename}",
             "startTime": "2026-06-01T00:00:00Z", "flightDirection": "ASCENDING",
             "pathNumber": 75, "frameNumber": 171, "mainBandPolarization": ["HH", "HV"],
             "bytes": {filename: {"bytes": 2_000_000_000}, "preview.png": {"bytes": 200}}}
    products = [SimpleNamespace(properties=props),
                SimpleNamespace(properties={**props, "pathNumber": 76}),
                SimpleNamespace(properties={**props, "url": "https://example.test/a_QA_STATS.h5"})]
    monkeypatch.setitem(sys.modules, "asf_search", SimpleNamespace(search=lambda **kwargs: products))
    result = nisar.search("POLYGON EMPTY", date(2026, 6, 1), date(2026, 10, 1), track=75, frame=171)
    assert len(result) == 1
    assert result[0].size_mb == 2000
    assert result[0].polarizations == ("HH", "HV")


def test_search_rejects_reversed_dates_before_request():
    with pytest.raises(ValueError, match="fecha inicial"):
        nisar.search("POLYGON EMPTY", date(2026, 10, 1), date(2026, 6, 1))


def test_cached_catalog_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="inválido"):
        nisar.load_cached_catalog("../../secret", catalog_dir=tmp_path)


def test_sequence_rejects_different_tracks(tmp_path):
    names = ["NISAR_L2_PR_GCOV_005_075_A_171_2005_DHDH_A_20260601T000000_20260601T000030_P05023_N_F_J_001.h5",
             "NISAR_L2_PR_GCOV_005_076_A_171_2005_DHDH_A_20261001T000000_20261001T000030_P05023_N_F_J_001.h5"]
    with pytest.raises(ValueError, match="trayectoria"):
        validate_sequence([tmp_path / name for name in names])


def test_polygons_preserves_component_when_background_is_smaller_than_threshold():
    mask = np.ones((5, 5), dtype=bool)
    mask[0, 0] = False
    result = polygons(mask, from_origin(0, 5, 1, 1), min_pixels=10)
    assert len(result) == 1
