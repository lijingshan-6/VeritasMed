"""Offline tests never load local secrets or use production checkpoints."""
import os
import sys
import tempfile

import pytest

_test_data = tempfile.TemporaryDirectory(prefix="veritasmed-tests-")
os.environ["MEDRAG_DATA_DIR"] = _test_data.name
os.environ["PYTHON_DOTENV_DISABLED"] = "1"


def pytest_sessionfinish(session, exitstatus):
    graph = sys.modules.get("medrag.agent.graph")
    if graph is not None:
        graph._conn.close()
    _test_data.cleanup()


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch):
    for key in ("OPENHUB_API_KEY", "OPENHUB_BASE_URL", "OPENHUB_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
