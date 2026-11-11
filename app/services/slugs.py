"""Slug generation utility."""
import re
import unicodedata


def generate_slug(text: str) -> str:
    """Convert *text* to a URL-safe, hyphenated, lowercase slug."""
    # Normalize unicode characters to their ASCII equivalents where possible
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    text = text.lower()
    # Replace any non-alphanumeric character sequences with a single hyphen
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Strip leading/trailing hyphens
    text = text.strip("-")
    return text
