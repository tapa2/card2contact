"""Run every sample card through Gemini and compare with samples/expected.json.

Usage: python -m tools.evaluate
Prints a Markdown table (for the report) and the list of wrong fields.
"""
import json
import mimetypes
import re
import time
from pathlib import Path

from google.genai import errors

from app.gemini import scan_card

SAMPLES = Path(__file__).parent.parent / "samples"
FIELDS = ["full_name", "job_title", "company", "phones", "email", "website", "address"]


def normalize(text: str) -> str:
    """Compare text ignoring case, spaces, punctuation and 'https://www.'."""
    text = re.sub(r"[\W_]", "", text.casefold())  # keep only letters and digits
    return re.sub(r"^(https?)?(www)?", "", text)


def phone_key(phone: str) -> str:
    """Last 9 digits: '+380 67 123 45 67' and '067 123 45 67' are the same number."""
    return re.sub(r"\D", "", phone)[-9:]


def field_ok(name: str, expected, got) -> bool:
    if name == "phones":
        return {phone_key(p) for p in expected} == {phone_key(p) for p in got}
    return any(normalize(option) == normalize(got) for option in expected.split("|"))


def main() -> None:
    expected_all = json.loads((SAMPLES / "expected.json").read_text(encoding="utf-8"))
    rows, mistakes, total_ok = [], [], 0

    for file_name, expected in expected_all.items():
        if file_name.startswith("_"):
            continue
        path = SAMPLES / file_name
        mime_type, _ = mimetypes.guess_type(path.name)
        try:
            result = scan_card(path.read_bytes(), mime_type)
        except errors.APIError as error:  # every model was busy
            rows.append(f"| {file_name} | error {error.code} | - | - |")
            continue
        got = result.contact.model_dump()

        ok = 0
        for name in FIELDS:
            if field_ok(name, expected[name], got[name]):
                ok += 1
            else:
                mistakes.append(f"{file_name}: {name}: expected {expected[name]!r}, got {got[name]!r}")
        total_ok += ok
        rows.append(f"| {file_name} | {ok}/{len(FIELDS)} | {result.model} | {result.seconds} |")
        time.sleep(4)  # stay well below the Vertex AI requests-per-minute quota

    print("| Card | Correct fields | Model | Time, s |")
    print("| --- | --- | --- | --- |")
    print("\n".join(rows))
    print(f"\nTotal: {total_ok}/{len(rows) * len(FIELDS)} fields correct")
    print("\nMistakes:" if mistakes else "\nNo mistakes.")
    for line in mistakes:
        print("  " + line)


if __name__ == "__main__":
    main()
