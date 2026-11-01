"""Check an actual HTTP server; stdlib only, usable before installing packages."""
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def check(base):
    for attempt in range(30):
        try:
            with urlopen(base + "/health", timeout=10) as r:
                health = json.load(r)
            assert health["status"] == "ok" and health["orders"] == 60000
            break
        except (HTTPError, URLError, TimeoutError):
            if attempt == 29:
                raise
            time.sleep(2)
    with urlopen(base + "/api/analytics?city=Lima", timeout=30) as r:
        data = json.load(r)
    assert 0 < data["summary"]["orders"] < 60000
    assert data["summary"]["revenue"] > 0
    with urlopen(base, timeout=10) as r:
        assert "Andes Analytics" in r.read().decode()
    print(json.dumps({"url": base, "health": health, "filtered_orders": data["summary"]["orders"]}))


if __name__ == "__main__":
    check(sys.argv[1].rstrip("/"))
