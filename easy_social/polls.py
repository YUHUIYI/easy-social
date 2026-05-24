from __future__ import annotations

from dataclasses import dataclass

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
    counts = {option.id: option.votes.count() for option in options}
    total = sum(counts.values())
    results: list[PollOptionResult] = []
    for option in options:
        vote_count = counts[option.id]
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
    for post_id, poll in poll_posts.items():
        results_by_post[post_id] = build_poll_results(poll)
        voted_option_id = user_vote_option_id(poll, user_id)
        if voted_option_id is not None:
            user_votes_by_post[post_id] = voted_option_id
    return results_by_post, user_votes_by_post
