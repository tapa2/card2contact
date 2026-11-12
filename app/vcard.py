"""Build a vCard 3.0 file (.vcf) from a recognized contact."""
from app.gemini import Contact


def escape(value: str) -> str:
    """vCard special characters must be escaped with a backslash."""
    return (
        value.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")  # a real line break becomes the two characters \n
    )


def split_name(full_name: str) -> tuple[str, str]:
    """'Олена Коваленко' -> ('Коваленко', 'Олена'): last word is the family name."""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name, ""
    return parts[-1], " ".join(parts[:-1])


def to_vcard(contact: Contact) -> str:
    family, given = split_name(contact.full_name)
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{escape(contact.full_name)}",          # name as shown in the phone
        f"N:{escape(family)};{escape(given)};;;",   # structured name (required field)
    ]
    if contact.company:
        lines.append(f"ORG:{escape(contact.company)}")
    if contact.job_title:
        lines.append(f"TITLE:{escape(contact.job_title)}")
    for phone in contact.phones:
        lines.append(f"TEL;TYPE=WORK,VOICE:{escape(phone)}")
    if contact.email:
        lines.append(f"EMAIL;TYPE=INTERNET:{escape(contact.email)}")
    if contact.website:
        lines.append(f"URL:{escape(contact.website)}")
    if contact.address:
        # ADR has 7 parts: PO box;extended;street;city;region;zip;country.
        # We do not split the address, so the whole text goes into "street".
        lines.append(f"ADR;TYPE=WORK:;;{escape(contact.address)};;;;")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"  # the standard requires CRLF line endings
