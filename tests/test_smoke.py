import io
import json

from scripts import smoke


def test_smoke_waits_for_container_startup(monkeypatch, capsys):
    responses = iter([
        ConnectionResetError("container not listening yet"),
        io.StringIO(json.dumps({"status": "ok", "orders": 60000})),
        io.StringIO(json.dumps({"summary": {"orders": 15050, "revenue": 100}})),
        io.BytesIO(b"Andes Analytics"),
    ])

    def request(*args, **kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    sleeps = []
    monkeypatch.setattr(smoke, "urlopen", request)
    monkeypatch.setattr(smoke.time, "sleep", sleeps.append)
    smoke.check("http://localhost:8080")
    assert sleeps == [2]
    assert json.loads(capsys.readouterr().out)["filtered_orders"] == 15050
