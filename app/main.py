"""REST API of the service. Run: uvicorn app.main:app --reload"""
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from google.genai import errors

from app.gemini import Contact, ScanResult, scan_card
from app.vcard import to_vcard

MAX_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ROOT = Path(__file__).parent.parent  # project folder, so paths work from any current directory

app = FastAPI(
    title="Card2Contact",
    description="Business card photo -> contact (JSON) -> vCard, using Google Gemini API.",
)
# Web page files (HTML/CSS/JS) and sample cards for the "try a sample" button.
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/samples", StaticFiles(directory=ROOT / "samples"), name="samples")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.post("/api/scan", response_model=ScanResult)
def scan(file: UploadFile) -> ScanResult:
    """Recognize a business card photo."""
    # 1. Check the file before spending a paid/limited API call on it.
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    image = file.file.read(MAX_SIZE + 1)  # read at most one byte over the limit
    if len(image) > MAX_SIZE:
        raise HTTPException(413, "File is larger than 10 MB")
    if not image:
        raise HTTPException(400, "Empty file")

    # 2. Ask Gemini; turn its errors into clear HTTP answers.
    try:
        return scan_card(image, file.content_type)
    except errors.APIError as error:
        raise HTTPException(502, f"Gemini API error {error.code}: {error.message}")
    except RuntimeError as error:  # e.g. GOOGLE_CLOUD_PROJECT is not set
        raise HTTPException(500, str(error))


@app.post("/api/vcard")
def vcard(contact: Contact) -> Response:
    """Turn a (possibly edited) contact into a downloadable .vcf file."""
    return Response(
        content=to_vcard(contact),
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="contact.vcf"'},
    )
