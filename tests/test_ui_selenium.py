from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

from easy_social import create_app
from easy_social.extensions import db
from easy_social.models import Comment, Post, User, followers

selenium = pytest.importorskip("selenium")

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@pytest.fixture(scope="module")
def ui_app():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{temp_path / 'ui.sqlite'}",
                "UPLOAD_FOLDER": str(temp_path / "uploads"),
                "MEDIA_STORAGE_BACKEND": "local",
                "WTF_CSRF_ENABLED": False,
            }
        )
        with app.app_context():
            db.create_all()
        yield app
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


@pytest.fixture(scope="module")
def live_server(ui_app):
    try:
        server = make_server("127.0.0.1", 0, ui_app, threaded=True)
    except SystemExit:
        pytest.skip("Selenium live server could not bind to a local port")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    thread.join(timeout=5)


@pytest.fixture()
def browser():
    browser_name = os.environ.get("SELENIUM_BROWSER", "chrome").lower()
    headless = os.environ.get("SELENIUM_HEADLESS", "1") != "0"

    try:
        if browser_name == "firefox":
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument("-headless")
            driver = webdriver.Firefox(options=options)
        else:
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1280,900")
            driver = webdriver.Chrome(options=options)
    except WebDriverException as exc:
        pytest.skip(f"Selenium browser could not start: {exc.msg}")

    yield driver

    driver.quit()


@pytest.fixture(autouse=True)
def ensure_logged_out(browser, live_server):
    browser.delete_all_cookies()
    browser.get(f"{live_server}/auth/logout")
    yield
    browser.delete_all_cookies()


@pytest.fixture(autouse=True)
def clean_database(ui_app):
    from easy_social.models import Poll, PollOption, PollVote

    with ui_app.app_context():
        db.session.execute(followers.delete())
        db.session.query(PollVote).delete(synchronize_session=False)
        db.session.query(PollOption).delete(synchronize_session=False)
        db.session.query(Poll).delete(synchronize_session=False)
        db.session.query(Comment).delete(synchronize_session=False)
        db.session.query(Post).delete(synchronize_session=False)
        db.session.query(User).delete(synchronize_session=False)
        db.session.commit()


def wait_for_text(browser, text: str):
    WebDriverWait(browser, 5).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))


def wait_for_feed(browser):
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form.composer")))
    wait_for_text(browser, "Feed")


def wait_for_login(browser):
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.NAME, "username_or_email")))
    wait_for_text(browser, "Log in")


def set_field_value(browser, field, value: str):
    browser.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """,
        field,
        value,
    )


def submit_form(browser, form):
    browser.execute_script("arguments[0].requestSubmit ? arguments[0].requestSubmit() : arguments[0].submit();", form)


def register_via_ui(browser, live_server: str, username: str):
    browser.get(f"{live_server}/auth/register")
    form = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form.form-stack"))
    )
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#captcha-image"))
    )
    set_field_value(browser, form.find_element(By.NAME, "username"), username)
    set_field_value(browser, form.find_element(By.NAME, "email"), f"{username}@example.com")
    set_field_value(browser, form.find_element(By.NAME, "password"), "password")
    captcha_field = form.find_element(By.NAME, "captcha")
    captcha_value = captcha_field.get_attribute("value")
    assert captcha_value, "Expected testing CAPTCHA hint on register form"
    set_field_value(browser, captcha_field, captcha_value)
    submit_form(browser, form)
    wait_for_feed(browser)


def logout_via_ui(browser):
    submit_form(browser, browser.find_element(By.CSS_SELECTOR, "header form"))
    wait_for_login(browser)


@pytest.mark.parametrize(
    ("filename", "contents", "expected_tag"),
    [
        ("preview.png", b"fake image data", "img"),
        ("preview.mp4", b"fake video data", "video"),
    ],
)
@pytest.mark.ui
def test_composer_shows_media_preview_before_posting(
    browser, live_server, tmp_path, filename, contents, expected_tag
):
    register_via_ui(browser, live_server, "previewer")
    media_path = tmp_path / filename
    media_path.write_bytes(contents)

    composer = browser.find_element(By.CSS_SELECTOR, "form.composer")
    media_input = composer.find_element(By.NAME, "media")
    browser.execute_script("arguments[0].style.display = 'block';", media_input)
    media_input.send_keys(str(media_path))

    preview = composer.find_element(By.CSS_SELECTOR, "[data-media-preview]")
    WebDriverWait(browser, 5).until(lambda _: preview.is_displayed())
    media = preview.find_element(By.CSS_SELECTOR, ".composer-preview-media")

    assert media.tag_name == expected_tag
    assert media.get_attribute("src").startswith("blob:")
    assert filename in preview.text
    if expected_tag == "video":
        assert media.get_attribute("controls") is not None

    preview.find_element(By.CSS_SELECTOR, "[data-media-preview-clear]").click()
    WebDriverWait(browser, 5).until(lambda _: not preview.is_displayed())
    assert media_input.get_attribute("value") == ""


@pytest.mark.ui
def test_register_rejects_wrong_captcha_in_ui(browser, live_server):
    browser.get(f"{live_server}/auth/register")
    form = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form.form-stack"))
    )
    set_field_value(browser, form.find_element(By.NAME, "username"), "blockedbot")
    set_field_value(browser, form.find_element(By.NAME, "email"), "blockedbot@example.com")
    set_field_value(browser, form.find_element(By.NAME, "password"), "password")
    set_field_value(browser, form.find_element(By.NAME, "captcha"), "WRONG1")
    submit_form(browser, form)
    wait_for_text(browser, "verification code")


@pytest.mark.ui
def test_user_can_register_create_post_and_comment(browser, live_server):
    register_via_ui(browser, live_server, "alice")

    composer = browser.find_element(By.CSS_SELECTOR, "form.composer")
    set_field_value(browser, composer.find_element(By.NAME, "body"), "Hello from Selenium")
    submit_form(browser, composer)
    wait_for_text(browser, "Hello from Selenium")

    comments_link = browser.find_element(By.PARTIAL_LINK_TEXT, "0 comments")
    browser.get(comments_link.get_attribute("href"))
    wait_for_text(browser, "Comments")
    comment_form = browser.find_element(By.CSS_SELECTOR, "form.comment-form")
    set_field_value(browser, comment_form.find_element(By.NAME, "body"), "First UI comment")
    submit_form(browser, comment_form)
    wait_for_text(browser, "First UI comment")


@pytest.mark.ui
def test_user_can_create_poll_and_vote_in_ui(browser, live_server, tmp_path):
    register_via_ui(browser, live_server, "alice")
    composer = browser.find_element(By.CSS_SELECTOR, "form.composer")
    media_path = tmp_path / "poll-preview.png"
    media_path.write_bytes(b"fake image data")
    media_input = composer.find_element(By.NAME, "media")
    browser.execute_script("arguments[0].style.display = 'block';", media_input)
    media_input.send_keys(str(media_path))
    preview = composer.find_element(By.CSS_SELECTOR, "[data-media-preview]")
    WebDriverWait(browser, 5).until(lambda _: preview.is_displayed())

    poll_radio = composer.find_element(By.CSS_SELECTOR, 'input[name="post_type"][value="poll"]')
    browser.execute_script(
        "arguments[0].checked = true;"
        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
        poll_radio,
    )
    WebDriverWait(browser, 5).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-poll-options]"))
    )
    WebDriverWait(browser, 5).until(lambda _: not preview.is_displayed())
    assert media_input.get_attribute("value") == ""
    assert not media_input.is_enabled()

    set_field_value(browser, composer.find_element(By.NAME, "body"), "Favorite IDE?")
    set_field_value(browser, composer.find_element(By.NAME, "poll_option_1"), "VS Code")
    set_field_value(browser, composer.find_element(By.NAME, "poll_option_2"), "PyCharm")
    submit_form(browser, composer)
    wait_for_text(browser, "Favorite IDE?")

    logout_via_ui(browser)
    register_via_ui(browser, live_server, "bob")
    browser.get(f"{live_server}/explore")
    wait_for_text(browser, "@alice")
    submit_form(browser, browser.find_element(By.CSS_SELECTOR, ".user-row form"))
    browser.get(f"{live_server}/")
    wait_for_text(browser, "Favorite IDE?")
    poll_form = browser.find_element(By.CSS_SELECTOR, "form.poll-vote-form")
    first_option = poll_form.find_element(By.CSS_SELECTOR, 'input[name="poll_option_id"]')
    browser.execute_script("arguments[0].checked = true;", first_option)
    submit_form(browser, poll_form)
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".poll-results"))
    )
    wait_for_text(browser, "100.0%")


@pytest.mark.ui
def test_following_user_adds_their_posts_to_feed(browser, live_server):
    register_via_ui(browser, live_server, "bob")
    composer = browser.find_element(By.CSS_SELECTOR, "form.composer")
    set_field_value(browser, composer.find_element(By.NAME, "body"), "Bob browser update")
    submit_form(browser, composer)
    wait_for_text(browser, "Bob browser update")
    logout_via_ui(browser)

    register_via_ui(browser, live_server, "alice")
    feed_posts = browser.find_element(By.CSS_SELECTOR, ".post-list")
    assert "Bob browser update" not in feed_posts.text

    browser.get(f"{live_server}/explore")
    wait_for_text(browser, "@bob")
    submit_form(browser, browser.find_element(By.CSS_SELECTOR, ".user-row form"))
    wait_for_text(browser, "Unfollow")

    browser.get(f"{live_server}/")
    wait_for_text(browser, "Bob browser update")
