from sqlalchemy.orm import Session
from app.main import app


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_db_yields_and_closes_session():
    from app.database import get_db

    gen = get_db()
    db = next(gen)
    assert isinstance(db, Session)
    db.close()
    gen.close()
