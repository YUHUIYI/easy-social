## Summary

- Add session-backed graphical CAPTCHA to the registration flow to block automated bot signups and reduce spam content.
- Introduce `GET /auth/captcha` (PNG image), verification on `POST /auth/register`, and a refresh control on the register page.
- Add Pillow dependency plus unit, integration, and Selenium end-to-end test coverage.

## Background

After Easy Social went live, PM Debbie reported that registration had no CAPTCHA, allowing bots to flood the platform with spam posts and comments.

## Changes

- **`easy_social/captcha.py`**: generate distorted PNG challenges, hash answers with `SECRET_KEY`, single-use session verification.
- **`easy_social/auth.py`**: captcha image route; register rejects missing/incorrect codes before creating users.
- **Register UI**: image, input field, refresh button; styles and JS for captcha refresh.
- **Tests**: `tests/test_captcha.py` (unit), `tests/test_auth_captcha.py` (integration), updated Selenium helpers and UI tests.

## Test plan

- [x] `poetry run pytest -m unit`
- [x] `poetry run pytest -m integration`
- [x] `poetry run pytest -m ui`

## Closes

<!-- Link the GitHub issue after it is created, e.g. Closes #123 -->
