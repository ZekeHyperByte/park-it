"""Tests for password hashing utilities."""


from api.app.utils.password import hash_password, verify_password


def test_hash_password():
    """Test password hashing produces a valid bcrypt hash."""
    password = "admin123"
    hashed = hash_password(password)

    assert hashed.startswith("$2b$")
    assert len(hashed) > 50


def test_verify_password_correct():
    """Test verifying correct password."""
    password = "admin123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_wrong():
    """Test verifying wrong password."""
    password = "admin123"
    hashed = hash_password(password)

    assert verify_password("wrongpassword", hashed) is False


def test_verify_password_different_passwords():
    """Test that different passwords produce different hashes."""
    hash1 = hash_password("password1")
    hash2 = hash_password("password2")

    assert hash1 != hash2


def test_verify_password_unicode():
    """Test unicode password handling."""
    password = "пароль123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("other", hashed) is False
