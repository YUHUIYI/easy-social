from __future__ import annotations

import pytest

from easy_social.polls import (
    MAX_POLL_OPTIONS,
    MIN_POLL_OPTIONS,
    build_poll_results,
    normalize_poll_options,
    poll_results_for_posts,
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


def test_poll_results_for_posts_batches_user_votes(app):
    from sqlalchemy import event
    from sqlalchemy.orm import joinedload

    from easy_social.extensions import db
    from easy_social.models import Poll, PollOption, PollVote, Post, User

    with app.app_context():
        author = User(username="author", email="author@example.com")
        author.set_password("password")
        voter = User(username="voter", email="voter@example.com")
        voter.set_password("password")
        first_post = Post(body="First poll?", post_type=Post.POST_TYPE_POLL, author=author)
        first_poll = Poll(post=first_post)
        first_red = PollOption(poll=first_poll, label="Red", position=0)
        first_blue = PollOption(poll=first_poll, label="Blue", position=1)
        second_post = Post(body="Second poll?", post_type=Post.POST_TYPE_POLL, author=author)
        second_poll = Poll(post=second_post)
        second_cat = PollOption(poll=second_poll, label="Cat", position=0)
        second_dog = PollOption(poll=second_poll, label="Dog", position=1)
        db.session.add_all(
            [
                author,
                voter,
                first_post,
                first_poll,
                first_red,
                first_blue,
                second_post,
                second_poll,
                second_cat,
                second_dog,
                PollVote(poll=first_poll, option=first_red, user=voter),
                PollVote(poll=second_poll, option=second_dog, user=voter),
            ]
        )
        db.session.commit()

        posts = (
            Post.query.options(joinedload(Post.poll).joinedload(Poll.options))
            .order_by(Post.id)
            .all()
        )
        first_post_id = first_post.id
        second_post_id = second_post.id
        first_red_id = first_red.id
        second_dog_id = second_dog.id
        voter_id = voter.id
        statements: list[str] = []

        def before_cursor_execute(*args):
            statement = args[2]
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", before_cursor_execute)
        try:
            _, user_votes = poll_results_for_posts(posts, voter_id)
        finally:
            event.remove(db.engine, "before_cursor_execute", before_cursor_execute)

        assert user_votes == {first_post_id: first_red_id, second_post_id: second_dog_id}
        assert len(statements) == 3
