import os
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("ADMIN_USERNAME", "admin")

from starlette.testclient import TestClient

from app.main import app


def test_scheduler_starts_and_stops_with_app():
    from app import scheduler as sched_module
    with TestClient(app):
        s = sched_module.get_scheduler()
        assert s is not None
        assert s.running is True
    # After context exits lifespan cleanup runs
    assert sched_module.get_scheduler() is None
