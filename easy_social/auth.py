from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .captcha import create_challenge, get_plaintext_for_tests, render_image, verify_answer
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _issue_captcha() -> str | None:
    create_challenge(
        session,
        current_app.config["SECRET_KEY"],
        testing=current_app.config.get("TESTING", False),
    )
    if current_app.config.get("TESTING"):
        return get_plaintext_for_tests(session)
    return None


@bp.get("/captcha")
def captcha_image():
    testing = current_app.config.get("TESTING", False)
    plaintext = get_plaintext_for_tests(session)
    if plaintext:
        image_bytes = render_image(plaintext)
    else:
        image_bytes, _ = create_challenge(
            session,
            current_app.config["SECRET_KEY"],
            testing=False,
        )
    response = current_app.response_class(image_bytes, mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    captcha_test_answer = None
    if request.method == "GET" and current_app.config.get("TESTING", False):
        captcha_test_answer = _issue_captcha()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        captcha_input = request.form.get("captcha", "")

        error = None
        if not verify_answer(session, captcha_input, current_app.config["SECRET_KEY"]):
            error = "Incorrect or expired verification code. Please try again."
        elif not username or not email or not password:
            error = "Username, email, and password are required."
        elif len(username) > 40:
            error = "Username must be 40 characters or fewer."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif User.query.filter_by(email=email).first():
            error = "That email is already registered."

        if error:
            flash(error, "error")
            captcha_test_answer = _issue_captcha()
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("social.feed"))

    return render_template(
        "auth/register.html",
        captcha_test_answer=captcha_test_answer,
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("social.feed"))

    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (User.username == username_or_email)
            | (User.email == username_or_email.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("social.feed"))

        flash("Invalid username/email or password.", "error")

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
