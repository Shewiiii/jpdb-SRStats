# MADE WITH GPT-5

from collections import Counter
from datetime import datetime, timedelta, timezone, date
from typing import Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from fsrs.scheduler import Scheduler
from fsrs.card import Card, State
from fsrs.review_log import Rating

TZ_UTC = timezone.utc


def _as_dt(x, tz):
    dt = x if hasattr(x, "tzinfo") else None
    if dt is None:
        dt = (
            x.get("review_datetime")
            if isinstance(x, dict)
            else getattr(x, "review_datetime", None)
        )
    if dt is None or dt.tzinfo is None:
        raise ValueError("All review datetimes must be timezone-aware.")
    return dt.astimezone(tz)


def _as_rating(x):
    r = (
        x
        if isinstance(x, Rating)
        else (x.get("rating") if isinstance(x, dict) else getattr(x, "rating", None))
    )
    if isinstance(r, Rating):
        return r
    if isinstance(r, int):
        return Rating(r)
    if isinstance(r, str):
        name = r.strip().lower()
        for k in Rating.__members__:
            if k.lower() == name:
                return Rating[k]
    raise ValueError(f"Unsupported rating value: {r!r}")


def _mark_days_review(
    counter: Counter, start: datetime, end: datetime, tz, now: datetime
):
    """
    Mark day d as 'known' if EOD(d) is in [start, end).
    Today samples at min(EOD(today), now). End is exclusive.
    """
    if start >= end:
        return
    day = start.date()
    while True:
        eod = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tz)
        sample = eod if eod.date() < now.date() else min(eod, now)
        if sample >= end:
            break
        if sample >= start:
            counter[day] += 1
        day += timedelta(days=1)
        if day > end.date():
            break


def _half_year_start(d: date) -> date:
    return date(d.year, 1, 1) if d.month <= 6 else date(d.year, 7, 1)


def _next_half_year_start(d: date) -> date:
    return date(d.year, 7, 1) if d.month <= 6 else date(d.year + 1, 1, 1)


def plot_known_words_(
    review_logs: dict,
    scheduler: Optional[Scheduler] = None,
    show_6m_bars: bool = True,
    bar_alpha: float = 0.25,
):
    """
    Known := card is in State.Review (Learning/Relearning are not known).
    Daily counts sampled at end-of-day.
    Also plots a Relearning line (state = Relearning).
    Bars (optional, default True) are per 6 months and show how many cards entered
    Review for the first time in that half-year (non-negative).
    """
    tz = TZ_UTC
    now = datetime.now(tz)
    sched = scheduler or Scheduler(enable_fuzzing=False)

    known_day_counts = Counter()
    relearning_day_counts = Counter()
    start_candidates = []
    first_review_at = {}  # card_id -> datetime of first time entering Review

    for vid, raw_logs in review_logs.items():
        logs = sorted(raw_logs, key=lambda x: _as_dt(x, tz))
        if not logs:
            continue

        c = Card()
        start_candidates.append(_as_dt(logs[0], tz).date())

        for i, log in enumerate(logs):
            when = _as_dt(log, tz)
            rating = _as_rating(log)
            c, _ = sched.review_card(card=c, rating=rating, review_datetime=when)

            # First time entering Review
            if c.state == State.Review and vid not in first_review_at:
                first_review_at[vid] = when

            # State persists until next review (or now)
            next_when = (
                _as_dt(logs[i + 1], tz)
                if i + 1 < len(logs)
                else now + timedelta(seconds=1)
            )
            interval_end = min(next_when, now + timedelta(seconds=1))

            # Known line: state == Review
            if c.state == State.Review and interval_end > when:
                _mark_days_review(known_day_counts, when, interval_end, tz, now)

            # Relearning line: state == Relearning
            if c.state == State.Relearning and interval_end > when:
                _mark_days_review(relearning_day_counts, when, interval_end, tz, now)

    if not start_candidates:
        print("No logs found to plot.")
        return

    start_day = min(start_candidates)
    end_day = now.date()

    # Daily series
    days = []
    known_counts = []
    relearn_counts = []
    d = start_day
    while d <= end_day:
        days.append(d)
        known_counts.append(known_day_counts.get(d, 0))
        relearn_counts.append(relearning_day_counts.get(d, 0))
        d += timedelta(days=1)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.step(
        days,
        known_counts,
        where="post",
        label="Known",
        linewidth=2,
        color="#2a9d8f",
    )
    ax.step(
        days,
        relearn_counts,
        where="post",
        label="Relearning",
        linewidth=2,
        color="#1f77b4",
    )

    # 6-month bars: count first-time entries per half-year bucket
    if show_6m_bars and first_review_at:
        monthly_bar_color = "#264653"
        bar_starts, bar_heights, bar_widths = [], [], []
        cur = _half_year_start(start_day)
        while cur <= end_day:
            nxt = _next_half_year_start(cur)
            bucket_start = cur
            bucket_end = min(nxt - timedelta(days=1), end_day)  # inclusive
            # count first entries in this bucket
            cnt = sum(
                1
                for dt in first_review_at.values()
                if bucket_start <= dt.date() <= bucket_end
            )
            if cnt > 0:
                bar_starts.append(bucket_start)
                bar_heights.append(cnt)
                bar_widths.append((bucket_end - bucket_start).days + 1)
            cur = nxt

        if bar_starts:
            ax.bar(
                bar_starts,
                bar_heights,
                width=bar_widths,
                align="edge",
                alpha=bar_alpha,
                color=monthly_bar_color,
                label="Learned per 6 months",
                zorder=0,
            )

    ax.set_title("Known words over time")
    ax.set_ylabel("Count")
    ax.set_xlabel("Date")
    ax.grid(True, alpha=0.3)
    ax.legend()

    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    plt.tight_layout()
    plt.show()
