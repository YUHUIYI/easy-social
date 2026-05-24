from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func

from .models import Poll, PollOption, PollVote

MAX_POLL_OPTIONS = 4
MIN_POLL_OPTIONS = 2


@dataclass(frozen=True)
class PollOptionResult:
    option_id: int
    label: str
    position: int
    vote_count: int
    percent: float


def normalize_poll_options(raw_options: list[str]) -> list[str] | None:
    options = [value.strip() for value in raw_options if value and value.strip()]
    if not MIN_POLL_OPTIONS <= len(options) <= MAX_POLL_OPTIONS:
        return None
    return options


def build_poll_results(poll: Poll) -> list[PollOptionResult]:
    options = sorted(poll.options, key=lambda option: option.position)
    option_ids = [option.id for option in options]
    vote_count_rows = (
        PollVote.query.with_entities(PollVote.poll_option_id, func.count(PollVote.id))
        .filter(PollVote.poll_option_id.in_(option_ids))
        .group_by(PollVote.poll_option_id)
        .all()
    ) if option_ids else []
    counts = {option_id: vote_count for option_id, vote_count in vote_count_rows}
    total = sum(counts.values())
    results: list[PollOptionResult] = []
    for option in options:
        vote_count = counts.get(option.id, 0)
        percent = round((vote_count / total) * 100, 1) if total else 0.0
        results.append(
            PollOptionResult(
                option_id=option.id,
                label=option.label,
                position=option.position,
                vote_count=vote_count,
                percent=percent,
            )
        )
    return results


def user_vote_option_id(poll: Poll, user_id: int) -> int | None:
    vote = PollVote.query.filter_by(poll_id=poll.id, user_id=user_id).first()
    return vote.poll_option_id if vote else None


def poll_results_for_posts(posts, user_id: int) -> tuple[dict[int, list[PollOptionResult]], dict[int, int]]:
    poll_posts = {
        post.display_post.id: post.display_post.poll
        for post in posts
        if post.display_post.post_type == "poll" and post.display_post.poll
    }
    if not poll_posts:
        return {}, {}

    results_by_post: dict[int, list[PollOptionResult]] = {}
    user_votes_by_post: dict[int, int] = {}
    poll_id_to_post_id = {poll.id: post_id for post_id, poll in poll_posts.items()}
    user_vote_rows = (
        PollVote.query.with_entities(PollVote.poll_id, PollVote.poll_option_id)
        .filter(PollVote.poll_id.in_(poll_id_to_post_id), PollVote.user_id == user_id)
        .all()
    )
    user_vote_option_ids = {
        poll_id_to_post_id[poll_id]: option_id for poll_id, option_id in user_vote_rows
    }

    for post_id, poll in poll_posts.items():
        results_by_post[post_id] = build_poll_results(poll)
        voted_option_id = user_vote_option_ids.get(post_id)
        if voted_option_id is not None:
            user_votes_by_post[post_id] = voted_option_id
    return results_by_post, user_votes_by_post
