"""Tests for JWT utilities."""

import time

import pytest

from api.app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
)


def test_create_access_token():
    """Test access token creation."""
    data = {"sub": "1", "role": "admin"}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token():
    """Test refresh token creation."""
    data = {"sub": "1", "role": "admin"}
    token = create_refresh_token(data)

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token():
    """Test token decoding."""
    data = {"sub": "1", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_token(token)

    assert decoded["sub"] == "1"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_token_expiry():
    """Test token has expiry."""
    data = {"sub": "1"}
    token = create_access_token(data)
    exp = get_token_expiry(token)

    # Expiry should be in the future
    from datetime import datetime, timezone
    assert exp > datetime.now(timezone.utc)


def test_decode_invalid_token():
    """Test decoding invalid token raises exception."""
    with pytest.raises(Exception):
        decode_token("invalid.token.here")


def test_access_refresh_different():
    """Test access and refresh tokens are different."""
    data = {"sub": "1"}
    access = create_access_token(data)
    refresh = create_refresh_token(data)

    assert access != refresh

    access_decoded = decode_token(access)
    refresh_decoded = decode_token(refresh)

    assert access_decoded["type"] == "access"
    assert refresh_decoded["type"] == "refresh"
