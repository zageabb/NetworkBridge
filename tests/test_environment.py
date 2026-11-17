from pathlib import Path

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.environment import environment_report


def test_environment_report(tmp_path: Path):
    release = tmp_path / "os-release"
    release.write_text('NAME="Example"\nPRETTY_NAME="Ubuntu Test"\n')
    report = environment_report(release)
    assert report["operating_system"] == "Ubuntu Test"
    assert report["monitoring_mode"] == "read-only"
    assert set(report) == {
        "operating_system", "kernel", "architecture", "python_version", "monitoring_mode"
    }


def test_environment_api():
    response = TestClient(app).get("/api/environment")
    assert response.status_code == 200
    assert "python_version" in response.json()
