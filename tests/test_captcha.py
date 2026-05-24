from __future__ import annotations

import pytest

from easy_social.captcha import (
    CAPTCHA_LENGTH,
    create_challenge,
    generate_code,
    hash_answer,
    render_image,
    store_challenge,
    verify_answer,
)

pytestmark = pytest.mark.unit


def test_generate_code_uses_expected_charset_and_length():
    code = generate_code()
    assert len(code) == CAPTCHA_LENGTH
    assert code.isalnum()
    assert "0" not in code
    assert "O" not in code


def test_hash_answer_is_case_insensitive():
    secret = "test-secret"
    assert hash_answer("ab12c", secret) == hash_answer("AB12C", secret)


def test_verify_answer_accepts_matching_input():
    secret = "test-secret"
    session: dict = {}
    store_challenge(session, "XY234", secret)
    assert verify_answer(session, "xy234", secret) is True
    assert "captcha_hash" not in session


def test_verify_answer_rejects_wrong_or_missing_input():
    secret = "test-secret"
    session: dict = {}
    store_challenge(session, "XY234", secret)
    assert verify_answer(session, "WRONG", secret) is False

    session = {}
    assert verify_answer(session, "XY234", secret) is False


def test_create_challenge_testing_mode_exposes_plaintext_in_session():
    session: dict = {}
    image_bytes, answer = create_challenge(session, "secret", testing=True)
    assert len(answer) == CAPTCHA_LENGTH
    assert image_bytes.startswith(b"\x89PNG")
    assert session["captcha_plaintext"] == answer


def test_render_image_returns_png_bytes():
    png = render_image("ABC12")
    assert png.startswith(b"\x89PNG")
    assert len(png) > 100
