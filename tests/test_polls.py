from __future__ import annotations

import pytest

from easy_social.polls import (
    MAX_POLL_OPTIONS,
    MIN_POLL_OPTIONS,
    build_poll_results,
    normalize_poll_options,
)

pytestmark = pytest.mark.unit


def test_normalize_poll_options_accepts_two_to_four_values():
    assert normalize_poll_options(["A", "B"]) == ["A", "B"]
    assert normalize_poll_options(["", "One", "Two", "Three", ""]) == ["One", "Two", "Three"]


def test_normalize_poll_options_rejects_invalid_counts():
    assert normalize_poll_options(["Only one"]) is None
    assert normalize_poll_options(["1", "2", "3", "4", "5"]) is None
    assert normalize_poll_options([" ", ""]) is None


def test_normalize_poll_options_enforces_max_options():
    options = [f"Option {index}" for index in range(MAX_POLL_OPTIONS + 1)]
    assert normalize_poll_options(options) is None


def test_build_poll_results_calculates_percentages(app):
    from easy_social.extensions import db
    from easy_social.models import Poll, PollOption, PollVote, Post, User

    with app.app_context():
        author = User(username="pollhost", email="pollhost@example.com")
        author.set_password("password")
        voter = User(username="voter", email="voter@example.com")
        voter.set_password("password")
        other = User(username="other", email="other@example.com")
        other.set_password("password")
        post = Post(body="Favorite color?", post_type=Post.POST_TYPE_POLL, author=author)
        poll = Poll(post=post)
        red = PollOption(poll=poll, label="Red", position=0)
        blue = PollOption(poll=poll, label="Blue", position=1)
        db.session.add_all([author, voter, other, post, poll, red, blue])
        db.session.flush()
        db.session.add_all(
            [
                PollVote(poll=poll, option=red, user_id=author.id),
                PollVote(poll=poll, option=red, user_id=voter.id),
                PollVote(poll=poll, option=blue, user_id=other.id),
            ]
        )
        db.session.commit()

        results = build_poll_results(poll)
        assert len(results) == MIN_POLL_OPTIONS
        assert results[0].vote_count == 2
        assert results[0].percent == 66.7
        assert results[1].vote_count == 1
        assert results[1].percent == 33.3


def test_build_poll_results_handles_zero_votes(app):
    from easy_social.extensions import db
    from easy_social.models import Poll, PollOption, Post, User

    with app.app_context():
        author = User(username="empty", email="empty@example.com")
        author.set_password("password")
        post = Post(body="Pick one", post_type=Post.POST_TYPE_POLL, author=author)
        poll = Poll(post=post)
        poll.options.extend(
            [
                PollOption(label="A", position=0),
                PollOption(label="B", position=1),
            ]
        )
        db.session.add_all([author, post, poll])
        db.session.commit()

        results = build_poll_results(poll)
        assert all(result.percent == 0.0 for result in results)
        assert all(result.vote_count == 0 for result in results)
