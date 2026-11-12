"""Command-line check without the web part: python -m app.cli samples/card_uk.png"""
import mimetypes
import sys
from pathlib import Path

from app.gemini import scan_card


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m app.cli <image file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    mime_type, _ = mimetypes.guess_type(path.name)
    result = scan_card(path.read_bytes(), mime_type or "image/jpeg")

    print(result.contact.model_dump_json(indent=2))
    print(f"model: {result.model}, time: {result.seconds} s")


if __name__ == "__main__":
    main()
