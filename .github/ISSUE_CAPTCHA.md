## Background

After Easy Social went live, PM Debbie reported that the registration flow does not include a graphical CAPTCHA. Automated bot accounts are flooding the platform and creating spam content.

## Problem

- `/auth/register` accepts account creation with only username, email, and password.
- Bots can script unlimited registrations without human verification.
- Spam posts and comments degrade feed quality and increase moderation cost.

## Proposed solution

Add a session-backed graphical CAPTCHA to the registration form:

1. Display a distorted image challenge on the register page.
2. Require users to submit the characters shown in the image.
3. Reject registration when the CAPTCHA is missing, expired, or incorrect.
4. Allow users to refresh the CAPTCHA image without reloading the entire form.

## Acceptance criteria

- [ ] Register page shows a CAPTCHA image, text input, and refresh control.
- [ ] `GET /auth/captcha` returns a PNG image and stores a one-time challenge in the session.
- [ ] Registration succeeds only when the submitted CAPTCHA matches the session challenge (case-insensitive).
- [ ] Registration fails with a clear error when CAPTCHA is missing or wrong; no user record is created.
- [ ] Each CAPTCHA challenge is single-use and invalidated after verification attempt.
- [ ] Unit tests cover CAPTCHA generation, hashing/verification, and edge cases.
- [ ] Integration tests cover register success/failure paths with CAPTCHA.
- [ ] End-to-end (Selenium) test completes registration through the UI with CAPTCHA.
- [ ] Existing login/logout flows remain unchanged.

## Out of scope

- CAPTCHA on login (registration only for this issue).
- Third-party CAPTCHA providers (e.g. reCAPTCHA).
