"""Unit tests for vCard export. They do not call Gemini, so they run offline."""
from app.gemini import Contact
from app.vcard import escape, split_name, to_vcard


def make_contact(**changes) -> Contact:
    fields = dict(
        full_name="Олена Коваленко",
        job_title="Інженерка",
        company="ТОВ «Хмарні рішення»",
        phones=["+380 67 123 45 67", "+380 44 555 12 34"],
        email="olena@example.com",
        website="example.com.ua",
        address="м. Київ, вул. Хрещатик, 1",
    )
    fields.update(changes)
    return Contact(**fields)


def test_full_card():
    text = to_vcard(make_contact())
    lines = text.split("\r\n")
    assert lines[0] == "BEGIN:VCARD"
    assert lines[1] == "VERSION:3.0"
    assert "FN:Олена Коваленко" in lines
    assert "N:Коваленко;Олена;;;" in lines
    assert "TEL;TYPE=WORK,VOICE:+380 67 123 45 67" in lines
    assert "TEL;TYPE=WORK,VOICE:+380 44 555 12 34" in lines
    assert "ADR;TYPE=WORK:;;м. Київ\, вул. Хрещатик\, 1;;;;" in lines
    assert text.endswith("END:VCARD\r\n")


def test_empty_fields_are_skipped():
    text = to_vcard(make_contact(company="", phones=[], email="", website="", address=""))
    assert "ORG:" not in text
    assert "TEL" not in text
    assert "EMAIL" not in text


def test_escape():
    assert escape("a,b;c") == "a\,b\;c"
    assert escape("line1\nline2") == "line1\nline2"


def test_split_name():
    assert split_name("John A. Smith") == ("Smith", "John A.")
    assert split_name("Madonna") == ("Madonna", "")
