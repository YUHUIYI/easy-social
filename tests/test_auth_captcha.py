from __future__ import annotations

import pytest

from easy_social.extensions import db
from easy_social.models import User

pytestmark = pytest.mark.integration


def test_register_page_includes_captcha(client):
    response = client.get("/auth/register")
    assert response.status_code == 200
    assert b"Verification code" in response.data
    assert b'name="captcha"' in response.data
    assert b"/auth/captcha" in response.data


def test_captcha_image_endpoint_returns_png(client):
    response = client.get("/auth/captcha")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")
    assert response.headers.get("Cache-Control", "").startswith("no-store")


def test_register_rejects_missing_captcha(client, app):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "username": "botuser",
            "email": "bot@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"verification code" in response.data.lower()
    with app.app_context():
        assert User.query.filter_by(username="botuser").first() is None


def test_register_rejects_wrong_captcha(client, app):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "username": "botuser",
            "email": "bot@example.com",
            "password": "password123",
            "captcha": "WRONG",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"verification code" in response.data.lower()
    with app.app_context():
        assert User.query.filter_by(username="botuser").first() is None


def test_register_succeeds_with_valid_captcha(client, app):
    client.get("/auth/register")
    with client.session_transaction() as session:
        captcha = session["captcha_plaintext"]

    response = client.post(
        "/auth/register",
        data={
            "username": "human",
            "email": "human@example.com",
            "password": "password123",
            "captcha": captcha,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Feed" in response.data
    with app.app_context():
        assert User.query.filter_by(username="human").one().email == "human@example.com"


def test_captcha_is_single_use(client, app):
    client.get("/auth/register")
    with client.session_transaction() as session:
        captcha = session["captcha_plaintext"]

    first = client.post(
        "/auth/register",
        data={
            "username": "first",
            "email": "first@example.com",
            "password": "password123",
            "captcha": captcha,
        },
        follow_redirects=True,
    )
    assert first.status_code == 200
    assert b"Feed" in first.data

    client.post("/auth/logout", follow_redirects=True)
    client.get("/auth/register")

    second = client.post(
        "/auth/register",
        data={
            "username": "second",
            "email": "second@example.com",
            "password": "password123",
            "captcha": captcha,
        },
        follow_redirects=True,
    )
    assert b"verification code" in second.data.lower()
    with app.app_context():
        assert User.query.filter_by(username="second").first() is None
