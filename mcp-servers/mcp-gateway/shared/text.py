"""Bounded text and best-effort credential masking."""
import re

def clean_text(value, limit=30_000):
    text = str(value or '')[:limit]
    # Best-effort common-token masking, not a guarantee against arbitrary secrets.
    return re.sub(r'(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]{15,})', '[REDACTED]', text)
