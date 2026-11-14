# Card2Contact

Web service that recognizes contact details on a business card photo and exports them as a vCard (`.vcf`).
It runs on Google Cloud: the server on **Cloud Run**, recognition by **Gemini on Vertex AI**.

Live: <https://card2contact-61425642502.europe-central2.run.app>

Lab 2, "Cloud Computing", Taras Shevchenko National University of Kyiv.

## How it works

```
Browser ──photo──▶ Cloud Run (FastAPI) ──photo + JSON schema──▶ Vertex AI (Gemini)
        ◀─contact─                     ◀────────JSON─────────
```

1. The user uploads a photo of a business card.
2. The server checks the file (type, size ≤ 10 MB) and sends it to Gemini together with a prompt and a JSON schema.
3. Gemini reads the card (OCR) and returns the fields: name, job title, company, phones, email, website, address.
4. The user checks and edits the fields and downloads a `.vcf` file that any phone can import.

If a model is busy (HTTP 429/500/503/504), the next model from the list is used:
`gemini-3.8-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`.

## Google Cloud services

| Service | Role in the project |
| --- | --- |
| Cloud Run | runs the container, public HTTPS URL, scales from 0 to 2 instances |
| Vertex AI | Gemini models in our own project |
| IAM service account | `card2contact-run` with only `roles/aiplatform.user`; replaces an API key |
| Cloud Build | builds the image from the `Dockerfile` during deploy |
| Artifact Registry | stores the built image |

The application has **no secrets**: on Cloud Run it gets short-lived tokens for its service account automatically,
and locally it uses the developer's `gcloud` login (Application Default Credentials).

## Project structure

| Path | Purpose |
| --- | --- |
| `app/gemini.py` | Vertex AI call: prompt, JSON schema (`Contact`), model fallback |
| `app/vcard.py` | Contact → vCard 3.0 text |
| `app/main.py` | FastAPI: `POST /api/scan`, `POST /api/vcard`, web page |
| `app/cli.py` | Command-line check without the web part |
| `static/` | Web page (HTML, CSS, JavaScript) |
| `samples/` | Synthetic business cards (fictional people) and `expected.json` with correct answers |
| `tools/evaluate.py` | Runs all samples through Gemini and compares with the correct answers |
| `tests/` | Unit and API tests (offline, Gemini is replaced by a fake) |
| `Dockerfile`, `.gcloudignore` | Container image and the files uploaded for it |
| `deploy.ps1` | One-command deploy to Cloud Run |

## Deploy to Google Cloud (PowerShell)

Requirements: [gcloud CLI](https://cloud.google.com/sdk/docs/install), a Google Cloud project with billing enabled.

```powershell
gcloud auth login
.\deploy.ps1 -Project <your-project-id>
```

The script enables the APIs, creates the service account, builds the image in Cloud Build and deploys it.
At the end it prints the `Service URL`.

## Run locally (Windows, PowerShell)

Requirements: Python 3.11+, gcloud CLI, the same Google Cloud project.

```powershell
gcloud auth application-default login
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then put your project ID into .env
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000> (web page) or <http://127.0.0.1:8000/docs> (Swagger UI).

Other commands:

```powershell
python -m app.cli samples\card_uk.png   # recognize one card in the terminal
python -m pytest                        # run tests (no network)
python -m tools.evaluate                # accuracy on all sample cards (calls Vertex AI)
```

## REST API

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/api/scan` | `multipart/form-data`, field `file` (JPEG/PNG/WebP/HEIC, ≤ 10 MB) | JSON: `contact`, `model`, `seconds` |
| POST | `/api/vcard` | JSON contact | `contact.vcf` file |

Errors: `415` unsupported file type, `413` file too large, `400` empty file, `502` Gemini error.

## Results on sample cards (Vertex AI)

| Card | Correct fields | Model | Time, s |
| --- | --- | --- | --- |
| card_uk.png | 7/7 | gemini-3.8-flash | 4.5 |
| card_en.png | 7/7 | gemini-3.8-flash | 12.06 |
| card_dark.png | 7/7 | gemini-3.8-flash | 5.18 |
| card_photo.jpg (rotated, blurred photo) | 7/7 | gemini-3.8-flash | 4.17 |
| card_handwritten.png (only 3 fields) | 7/7 | gemini-3.8-flash | 6.01 |
| card_vertical.png (bilingual) | 7/7 | gemini-3.8-flash | 6.13 |

Time is the total wait for the answer. The main model answered every request; the fallback models were not needed.
