"""
Rate limiting setup — shared instance avoids circular imports.
Uses slowapi (FOSS), the standard FastAPI rate-limiting library.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
