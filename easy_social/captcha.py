from __future__ import annotations

import hashlib
import random
import secrets
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CAPTCHA_SESSION_HASH_KEY = "captcha_hash"
CAPTCHA_SESSION_PLAINTEXT_KEY = "captcha_plaintext"
CAPTCHA_LENGTH = 5
_CAPTCHA_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_code(length: int = CAPTCHA_LENGTH) -> str:
    return "".join(secrets.choice(_CAPTCHA_CHARS) for _ in range(length))


def hash_answer(answer: str, secret_key: str) -> str:
    normalized = answer.strip().upper()
    payload = f"{secret_key}:{normalized}".encode()
    return hashlib.sha256(payload).hexdigest()


def store_challenge(session, answer: str, secret_key: str, *, testing: bool = False) -> None:
    session[CAPTCHA_SESSION_HASH_KEY] = hash_answer(answer, secret_key)
    if testing:
        session[CAPTCHA_SESSION_PLAINTEXT_KEY] = answer


def clear_challenge(session) -> None:
    session.pop(CAPTCHA_SESSION_HASH_KEY, None)
    session.pop(CAPTCHA_SESSION_PLAINTEXT_KEY, None)


def get_plaintext_for_tests(session) -> str | None:
    value = session.get(CAPTCHA_SESSION_PLAINTEXT_KEY)
    return value if isinstance(value, str) else None


def verify_answer(session, user_input: str, secret_key: str) -> bool:
    expected_hash = session.get(CAPTCHA_SESSION_HASH_KEY)
    clear_challenge(session)
    if not expected_hash or not user_input.strip():
        return False
    return hash_answer(user_input, secret_key) == expected_hash


def render_image(code: str, *, width: int = 180, height: int = 60) -> bytes:
    image = Image.new("RGB", (width, height), (247, 247, 244))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    for _ in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(180, 190, 200), width=1)

    for _ in range(120):
        draw.point(
            (random.randint(0, width - 1), random.randint(0, height - 1)),
            fill=(random.randint(120, 200), random.randint(120, 200), random.randint(120, 200)),
        )

    spacing = width // (len(code) + 1)
    for index, char in enumerate(code):
        x = spacing * (index + 1) - 6 + random.randint(-3, 3)
        y = random.randint(12, 22)
        draw.text((x, y), char, font=font, fill=(17, 35, 43))

    image = image.filter(ImageFilter.SMOOTH)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_challenge(session, secret_key: str, *, testing: bool = False) -> tuple[bytes, str]:
    answer = generate_code()
    store_challenge(session, answer, secret_key, testing=testing)
    return render_image(answer), answer
