"""API tests. Gemini is replaced by a fake function, so no network is used."""
from fastapi.testclient import TestClient

import app.main
from app.gemini import Contact, ScanResult

client = TestClient(app.main.app)

CONTACT = Contact(
    full_name="John Smith", job_title="", company="Northwind",
    phones=["+1 212 555 0147"], email="j@example.org", website="", address="",
)


def fake_scan_card(image: bytes, mime_type: str) -> ScanResult:
    return ScanResult(contact=CONTACT, model="fake-model", seconds=0.1)


def test_scan_ok(monkeypatch):
    monkeypatch.setattr(app.main, "scan_card", fake_scan_card)
    response = client.post("/api/scan", files={"file": ("card.png", b"\x89PNG...", "image/png")})
    assert response.status_code == 200
    assert response.json()["contact"]["full_name"] == "John Smith"
    assert response.json()["model"] == "fake-model"


def test_scan_wrong_type():
    response = client.post("/api/scan", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415


def test_scan_too_big():
    big = b"0" * (10 * 1024 * 1024 + 1)
    response = client.post("/api/scan", files={"file": ("big.jpg", big, "image/jpeg")})
    assert response.status_code == 413


def test_vcard_download():
    response = client.post("/api/vcard", json=CONTACT.model_dump())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/vcard")
    assert "attachment" in response.headers["content-disposition"]
    assert "FN:John Smith" in response.text


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Card2Contact" in response.text
