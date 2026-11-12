"""Recognize business card fields from a photo using the Google Gemini API."""
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

load_dotenv()  # reads GEMINI_API_KEY from the .env file

# Main model first; the next ones are used only if the previous one is overloaded.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"]

# HTTP codes that mean "busy, try another model": 429 = rate limit, 503 = overloaded.
RETRY_CODES = (429, 503)

PROMPT = """You read business cards. Extract the contact details from the photo.
Rules:
- Copy the text exactly as printed; do not translate and do not invent anything.
- If a field is not on the card, return an empty string (an empty list for phones).
- phones: every phone number on the card, in international format if the country is clear.
- website: without "https://".
"""


class Contact(BaseModel):
    """Fields of one contact. This class is also the JSON schema sent to Gemini."""
    full_name: str
    job_title: str
    company: str
    phones: list[str]
    email: str
    website: str
    address: str


class ScanResult(BaseModel):
    contact: Contact
    model: str      # which model actually answered
    seconds: float  # duration of the API call


def scan_card(image: bytes, mime_type: str) -> ScanResult:
    """Send the photo to Gemini and return the recognized contact."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (see .env.example)")

    # attempts=1: the SDK must not retry by itself (it waits up to minutes);
    # we switch to the next model instead. timeout is in milliseconds.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1), timeout=60_000
        ),
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",  # answer must be JSON...
        response_schema=Contact,                # ...exactly in the shape of Contact
        temperature=0,                          # no creativity, same photo -> same answer
    )
    image_part = types.Part.from_bytes(data=image, mime_type=mime_type)

    last_error = None
    for model in MODELS:
        start = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=model, contents=[image_part, PROMPT], config=config
            )
        except errors.APIError as error:
            if error.code in RETRY_CODES:
                last_error = error
                continue  # this model is busy -> try the next one
            raise
        seconds = round(time.perf_counter() - start, 2)
        contact = Contact.model_validate_json(response.text)
        return ScanResult(contact=contact, model=model, seconds=seconds)

    raise last_error  # every model was busy
