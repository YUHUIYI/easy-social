from __future__ import annotations

import pytest

from easy_social.models import PollVote, Post, User

from conftest import logout, register

pytestmark = pytest.mark.integration


def _create_poll(client, question: str, options: list[str]):
    data = {
        "post_type": "poll",
        "body": question,
    }
    for index, label in enumerate(options, start=1):
        data[f"poll_option_{index}"] = label
    return client.post("/posts", data=data, follow_redirects=True)


def test_create_poll_post_persists_options(client, app):
    register(client, "alice")
    response = _create_poll(client, "Best season?", ["Spring", "Summer", "Fall"])

    assert response.status_code == 200
    assert b"Best season?" in response.data
    assert b"poll" in response.data or b"Spring" in response.data

    with app.app_context():
        post = Post.query.filter_by(body="Best season?").one()
        assert post.post_type == Post.POST_TYPE_POLL
        assert post.poll is not None
        labels = [option.label for option in post.poll.options]
        assert labels == ["Spring", "Summer", "Fall"]


def test_create_poll_requires_two_to_four_options(client, app):
    register(client, "alice")
    response = _create_poll(client, "Invalid poll", ["Only one"])

    assert b"between 2 and 4" in response.data
    with app.app_context():
        assert Post.query.filter_by(body="Invalid poll").count() == 0


def test_vote_updates_percentages(client, app):
    register(client, "alice")
    _create_poll(client, "Pick a pet", ["Cats", "Dogs"])
    logout(client)
    register(client, "bob")
    client.post("/users/alice/follow", follow_redirects=True)

    with app.app_context():
        post = Post.query.filter_by(body="Pick a pet").one()
        post_id = post.id
        options = {option.label: option.id for option in post.poll.options}

    before_vote = client.get("/")
    assert b"poll-vote-form" in before_vote.data

    client.post(
        f"/posts/{post_id}/poll/vote",
        data={"poll_option_id": options["Cats"]},
        follow_redirects=True,
    )
    after_vote = client.get("/")
    assert b"100.0%" in after_vote.data or b"100%" in after_vote.data
    assert b"Cats" in after_vote.data

    logout(client)
    register(client, "casey")
    client.post("/users/alice/follow", follow_redirects=True)
    client.post(
        f"/posts/{post_id}/poll/vote",
        data={"poll_option_id": options["Dogs"]},
        follow_redirects=True,
    )
    split_view = client.get("/")
    assert b"50.0%" in split_view.data or b"50%" in split_view.data


def test_user_can_change_poll_vote(client, app):
    register(client, "alice")
    _create_poll(client, "Snack?", ["Chips", "Fruit"])
    logout(client)
    register(client, "bob")

    with app.app_context():
        post_id = Post.query.filter_by(body="Snack?").one().id
        option_ids = {option.label: option.id for option in Post.query.one().poll.options}

    client.post(
        f"/posts/{post_id}/poll/vote",
        data={"poll_option_id": option_ids["Chips"]},
        follow_redirects=True,
    )
    client.post(
        f"/posts/{post_id}/poll/vote",
        data={"poll_option_id": option_ids["Fruit"]},
        follow_redirects=True,
    )

    with app.app_context():
        vote = PollVote.query.filter_by(user_id=User.query.filter_by(username="bob").one().id).one()
        assert vote.poll_option_id == option_ids["Fruit"]


def test_poll_author_sees_results_without_voting(client, app):
    register(client, "alice")
    _create_poll(client, "Lunch?", ["Pizza", "Salad"])

    response = client.get("/")
    assert b"poll-results" in response.data
    assert b'name="poll_option_id"' not in response.data
