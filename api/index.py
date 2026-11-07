"""Vercel entrypoint. Vercel's Python runtime looks for a top-level ASGI
`app` in whatever file a request is routed to (see vercel.json) - this
file just re-exports the real app from the project root so there's only
one copy of the application code to maintain.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402,F401
