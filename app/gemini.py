"""Recognize business card fields from a photo using Gemini on Vertex AI (Google Cloud)."""
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

load_dotenv()  # local runs: reads GOOGLE_CLOUD_PROJECT from the .env file

# Google Cloud project whose Vertex AI is called. There is no API key:
# locally we use the developer's gcloud login, on Cloud Run the service account.
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")  # "global" = Google picks the region

# Main model first; the next ones are used only if the previous one is overloaded.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

# HTTP codes that mean "temporary problem on Google's side, try another model":
# 429 = rate limit, 500 = internal error, 503 = overloaded, 504 = model did not answer in time.
RETRY_CODES = (429, 500, 503, 504)

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
    seconds: float  # total wait time, including attempts on busy models


def scan_card(image: bytes, mime_type: str) -> ScanResult:
    """Send the photo to Gemini and return the recognized contact."""
    if not PROJECT:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set (see .env.example)")

    # attempts=1: the SDK must not retry by itself (it waits up to minutes);
    # we switch to the next model instead.
    # timeout (ms) is also sent to Google as a deadline: if the model is slower,
    # Google answers 504 and we move on. Normal answers take 1-5 s.
    client = genai.Client(
        vertexai=True,  # use Vertex AI in our Google Cloud project, not an API key
        project=PROJECT,
        location=LOCATION,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1), timeout=25_000
        ),
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",  # answer must be JSON...
        response_schema=Contact,                # ...exactly in the shape of Contact
        temperature=0,                          # no creativity, same photo -> same answer
    )
    image_part = types.Part.from_bytes(data=image, mime_type=mime_type)

    last_error = None
    start = time.perf_counter()  # total time the user waits, including busy models
    for model in MODELS:
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
