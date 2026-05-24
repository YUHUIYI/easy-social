# Poll Post Database Design

## Overview

Poll posts extend the existing `post` table with a dedicated poll graph. Each poll post has exactly one `poll` record, up to four `poll_option` rows, and zero or more `poll_vote` rows (one vote per user per poll).

## Entity Relationship

```text
user ──< post ──||── poll ──< poll_option ──< poll_vote >── user
                  │
                  └──< comment
```

- `post` (1) ── (0..1) `poll`: only poll-type posts have a poll.
- `poll` (1) ── (2..4) `poll_option`: enforced in application logic.
- `poll` (1) ── (0..N) `poll_vote`: each user may cast at most one vote per poll.

## Tables

### `post` (extended)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Post identifier |
| `body` | TEXT | NOT NULL | Text body or poll question |
| `post_type` | VARCHAR(20) | NOT NULL, default `standard`, indexed | `standard` or `poll` |
| `media_filename` | VARCHAR(255) | NULL | Media path for standard posts |
| `media_type` | VARCHAR(20) | NULL | `image` or `video` |
| `created_at` | DATETIME (TZ) | NOT NULL, indexed | Creation time |
| `author_id` | INTEGER | FK → `user.id`, NOT NULL, indexed | Author |
| `repost_of_id` | INTEGER | FK → `post.id`, NULL, indexed | Repost target |

**Check constraints**

- `ck_post_type`: `post_type IN ('standard', 'poll')`
- `ck_post_has_content`: poll posts may use question text only; standard posts still require body, media, or repost

### `poll`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Poll identifier |
| `post_id` | INTEGER | FK → `post.id` ON DELETE CASCADE, UNIQUE, NOT NULL, indexed | Owning post |

### `poll_option`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Option identifier |
| `poll_id` | INTEGER | FK → `poll.id` ON DELETE CASCADE, NOT NULL, indexed | Parent poll |
| `label` | VARCHAR(200) | NOT NULL | Option text |
| `position` | INTEGER | NOT NULL | Display order `0..3` |

**Constraints**

- `uq_poll_option_position`: unique (`poll_id`, `position`)
- `ck_poll_option_position`: `position >= 0 AND position < 4`

### `poll_vote`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK | Vote identifier |
| `poll_id` | INTEGER | FK → `poll.id` ON DELETE CASCADE, NOT NULL, indexed | Poll being voted on |
| `poll_option_id` | INTEGER | FK → `poll_option.id` ON DELETE CASCADE, NOT NULL, indexed | Selected option |
| `user_id` | INTEGER | FK → `user.id`, NOT NULL, indexed | Voter |
| `created_at` | DATETIME (TZ) | NOT NULL | Vote time |

**Constraints**

- `uq_poll_vote_once`: unique (`poll_id`, `user_id`) — one vote per user per poll

## Behaviour

1. **Create poll post**: `POST /posts` with `post_type=poll`, question in `body`, and `poll_option_1` … `poll_option_4` (2–4 non-empty options).
2. **Vote**: `POST /posts/<post_id>/poll/vote` with `poll_option_id`. Changing vote updates the existing row.
3. **Results**: Percentages are computed as `option_votes / total_votes * 100` (one decimal). Before any votes, all options show `0%`.
4. **Display**: Users who have not voted see radio choices; voters and poll authors see live result bars.

## Indexes

- `post.post_type` — filter poll posts
- `poll.post_id` (unique) — join post → poll
- `poll_option.poll_id` — load options
- `poll_vote.poll_id`, `poll_vote.user_id` — tally and “already voted” checks
