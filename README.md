# Card2Contact

Web service that recognizes contact details on a business card photo and exports them as a vCard (`.vcf`)
using the Google Gemini API.

Lab 2, "Cloud Computing", Taras Shevchenko National University of Kyiv.

## How it works

```
Browser ──photo──▶ FastAPI server ──photo + JSON schema──▶ Google Gemini (cloud)
        ◀─contact─                ◀────────JSON─────────
```

1. The user uploads a photo of a business card.
2. The server checks the file (type, size ≤ 10 MB) and sends it to Gemini together with a prompt and a JSON schema.
3. Gemini reads the card (OCR) and returns the fields: name, job title, company, phones, email, website, address.
4. The user checks and edits the fields and downloads a `.vcf` file that any phone can import.

If a model is busy (HTTP 429/500/503/504), the next model from the list is used:
`gemini-3.8-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`.

## Project structure

| Path | Purpose |
| --- | --- |
| `app/gemini.py` | Gemini call: prompt, JSON schema (`Contact`), model fallback |
| `app/vcard.py` | Contact → vCard 3.0 text |
| `app/main.py` | FastAPI: `POST /api/scan`, `POST /api/vcard`, web page |
| `app/cli.py` | Command-line check without the web part |
| `static/` | Web page (HTML, CSS, JavaScript) |
| `samples/` | Synthetic business cards (fictional people) and `expected.json` with correct answers |
| `tools/evaluate.py` | Runs all samples through Gemini and compares with the correct answers |
| `tests/` | Unit and API tests (offline, Gemini is replaced by a fake) |

## Run locally (Windows, PowerShell)

Requirements: Python 3.11+ and a free Gemini API key from <https://aistudio.google.com/apikey> (no bank card needed).

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then put your key into .env
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> (web page) or <http://127.0.0.1:8000/docs> (Swagger UI).

Other commands:

```powershell
python -m app.cli samples\card_uk.png   # recognize one card in the terminal
python -m pytest                        # run tests (no network)
python -m tools.evaluate                # accuracy on all sample cards (uses the API)
```

## Run in Docker

The image contains no secrets: the API key is passed when the container starts.

```powershell
docker build -t card2contact .
docker run --rm --env-file .env -p 8090:8080 card2contact
```

Open <http://127.0.0.1:8090>. The container listens on `$PORT` (8080 by default), as Google Cloud Run expects,
so the same image can be deployed there.

## REST API

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/api/scan` | `multipart/form-data`, field `file` (JPEG/PNG/WebP/HEIC, ≤ 10 MB) | JSON: `contact`, `model`, `seconds` |
| POST | `/api/vcard` | JSON contact | `contact.vcf` file |

Errors: `415` unsupported file type, `413` file too large, `400` empty file, `502` Gemini API error.

## Results on sample cards

| Card | Correct fields | Model | Time, s |
| --- | --- | --- | --- |
| card_uk.png | 7/7 | gemini-3.5-flash-lite | 2.1 |
| card_en.png | 7/7 | gemini-3.5-flash-lite | 3.16 |
| card_dark.png | 7/7 | gemini-3.5-flash-lite | 3.18 |
| card_photo.jpg (rotated, blurred photo) | 7/7 | gemini-3.1-flash-lite | 3.48 |
| card_handwritten.png (only 3 fields) | 7/7 | gemini-3.5-flash-lite | 8.19 |
| card_vertical.png (bilingual) | 7/7 | gemini-3.5-flash-lite | 2.77 |

Time is the total wait including attempts on busy models. Results depend on the current load of the free tier.
