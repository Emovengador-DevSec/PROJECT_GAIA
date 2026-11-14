import asf_search as asf
import pytest
from asf_search.exceptions import ASFAuthenticationError

from sarlab_pipeline.sources import nisar


def _granule(url="https://nisar.asf.earthdatacloud.nasa.gov/NISAR/test.h5"):
    return nisar.Granule("test", url, "2026-06-19", "ASCENDING", 75, len(nisar.HDF5_SIGNATURE) / 1e6)


@pytest.mark.parametrize("accepted", [True, False])
def test_sdk_rejection_requires_protected_hdf_signature(monkeypatch, tmp_path, accepted):
    events = []

    class Response:
        status_code = 206 if accepted else 401

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            events.append("closed")

        def iter_content(self, chunk_size):
            assert chunk_size == 8
            yield b"\x89HDF\r\n\x1a\n"

    class Session:
        def __init__(self):
            self.headers = {}

        def auth_with_token(self, _token):
            raise ASFAuthenticationError("test rejection")

        def get(self, url, **kwargs):
            assert url == _granule().url
            assert self.headers["Authorization"] == "Bearer test-only"
            assert kwargs["headers"] == {"Range": "bytes=0-7"}
            return Response()

    def save(_urls, dest, **_kwargs):
        assert events == ["closed"]
        (tmp_path / "test.h5").write_bytes(nisar.HDF5_SIGNATURE)

    monkeypatch.setattr(nisar, "earthdata_token", lambda: "test-only")
    monkeypatch.setattr(asf, "ASFSession", Session)
    monkeypatch.setattr(asf, "download_urls", save)
    if accepted:
        assert nisar.download([_granule()], tmp_path) == [tmp_path / "test.h5"]
    else:
        with pytest.raises(RuntimeError, match="no autorizó"):
            nisar.download([_granule()], tmp_path)
        assert not (tmp_path / "test.h5").exists()


def test_download_rejects_untrusted_host_before_using_credentials(monkeypatch, tmp_path):
    monkeypatch.setattr(nisar, "earthdata_token", lambda: pytest.fail("Token must not be requested"))
    with pytest.raises(ValueError, match="URL oficial"):
        nisar.download([_granule("https://example.invalid/file.h5")], tmp_path)
