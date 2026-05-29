"""Tests for booth_bridge.api_client retry classification.

Critical safety property: POST must NEVER retry on conditions where the
request may have reached the server (timeout, reset, broken pipe, HTTP
error). A retried payment POST would double-process.
"""

from __future__ import annotations

import socket
import urllib.error

from booth_bridge.api_client import _is_retryable_get, _is_retryable_post


class _FakeURLError(urllib.error.URLError):
    def __init__(self, reason: BaseException | str) -> None:  # type: ignore[override]
        self.reason = reason


def test_post_retries_only_connection_refused_and_dns() -> None:
    assert _is_retryable_post(ConnectionRefusedError()) is True
    assert _is_retryable_post(socket.gaierror()) is True
    # Wrapped inside URLError (what urllib.request.urlopen actually raises).
    assert _is_retryable_post(_FakeURLError(ConnectionRefusedError())) is True
    assert _is_retryable_post(_FakeURLError(socket.gaierror())) is True


def test_post_does_not_retry_timeouts() -> None:
    # socket.timeout is an alias of TimeoutError on Python 3.10+.
    # Either form must be classified as NOT retryable for POST: the request
    # may have reached the server and been processed.
    assert _is_retryable_post(TimeoutError()) is False
    assert _is_retryable_post(socket.timeout()) is False
    assert _is_retryable_post(_FakeURLError(TimeoutError())) is False
    assert _is_retryable_post(_FakeURLError(socket.timeout())) is False


def test_post_does_not_retry_after_send_errors() -> None:
    # These all imply some bytes may have been transmitted to the server.
    assert _is_retryable_post(ConnectionResetError()) is False
    assert _is_retryable_post(BrokenPipeError()) is False
    assert _is_retryable_post(ConnectionAbortedError()) is False
    assert _is_retryable_post(_FakeURLError(ConnectionResetError())) is False


def test_post_does_not_retry_http_errors() -> None:
    http_err = urllib.error.HTTPError(
        url="http://x", code=500, msg="Internal", hdrs=None, fp=None  # type: ignore[arg-type]
    )
    assert _is_retryable_post(http_err) is False


def test_get_retries_any_transient_socket_error() -> None:
    # GET is idempotent — broader retry policy.
    assert _is_retryable_get(ConnectionRefusedError()) is True
    assert _is_retryable_get(ConnectionResetError()) is True
    assert _is_retryable_get(TimeoutError()) is True
    assert _is_retryable_get(socket.timeout()) is True
    assert _is_retryable_get(socket.gaierror()) is True
    assert _is_retryable_get(_FakeURLError(TimeoutError())) is True


def test_get_does_not_retry_http_errors() -> None:
    http_err = urllib.error.HTTPError(
        url="http://x", code=404, msg="Not Found", hdrs=None, fp=None  # type: ignore[arg-type]
    )
    assert _is_retryable_get(http_err) is False
