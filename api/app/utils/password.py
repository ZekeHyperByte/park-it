"""Password hashing utilities using bcrypt directly.

NOTE: We use bcrypt directly instead of passlib due to a compatibility
issue with bcrypt >= 4.0. Passlib's backend detection fails intermittently.
If passlib fixes this, we can swap the implementation here without
changing any calling code.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
