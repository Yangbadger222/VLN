import json
from threading import Thread
from urllib.request import urlopen

from navida_deploy.http_service import create_server


def test_http_service_health_endpoint_reports_ok():
    server = create_server(("127.0.0.1", 0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/health", timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["status"] == "ok"
    finally:
        server.shutdown()
        thread.join()
