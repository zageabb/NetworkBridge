from unittest.mock import patch

from fastapi.testclient import TestClient

from networkbridge.api import app
from networkbridge.services import check_services


def test_service_probe_results_do_not_expose_hostnames():
    with patch("networkbridge.services.socket.create_connection") as connect:
        connect.return_value.__enter__.return_value = None
        results = check_services()
    assert len(results) == 4
    assert all(item["state"] == "reachable" for item in results)
    assert all("host" not in item for item in results)
    assert connect.call_count == 4
    for call in connect.call_args_list:
        assert call.args[0][0] == "127.0.0.1"


def test_service_probe_unreachable():
    with patch("networkbridge.services.socket.create_connection", side_effect=OSError):
        assert all(item["state"] == "unreachable" for item in check_services())


def test_services_api():
    with patch("networkbridge.api.check_services", return_value=[]):
        response = TestClient(app).get("/api/services")
    assert response.status_code == 200
    assert response.json()["services"] == []
