from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.alerts import evaluate
from networkbridge.api import app


def test_resource_thresholds():
    sample = {"memory": {"used_bytes": 90, "total_bytes": 100},
              "disk": {"available_bytes": 5, "total_bytes": 100}}
    result = evaluate(sample)
    assert {item["metric"] for item in result} == {"memory", "disk"}
    assert result[0]["percent"] == 90
    assert evaluate(sample, memory_threshold=95, disk_threshold=96) == []


def test_invalid_threshold():
    try:
        evaluate({"memory": {"used_bytes": 1, "total_bytes": 2},
                  "disk": {"available_bytes": 1, "total_bytes": 2}}, memory_threshold=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")


def test_alerts_api():
    sample = {"memory": {"used_bytes": 90, "total_bytes": 100},
              "disk": {"available_bytes": 50, "total_bytes": 100},
              "sampled_at_unix": 123}
    with patch("networkbridge.api.snapshot", return_value=sample):
        response = TestClient(app).get("/api/alerts")
    assert response.status_code == 200
    assert response.json()["count"] == 1
