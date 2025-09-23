import logging
from json import load, dump
from pathlib import Path
from datetime import datetime
from collections import Counter
from itertools import accumulate
from typing import Literal

from fsrs import State, Scheduler
from fsrs_wrapper import FsrsWrapper
from complex_plot import plot_known_words_

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class SrsDataWrapper:
    def __init__(
        self, json_path: Path, optimize: bool = False, ignore_optimization: bool = False
    ) -> None:
        with open(json_path, "r", encoding="utf-8") as file:
            self.raw_data: dict = load(file)

        self.words: list = self.raw_data["cards_vocabulary_jp_en"]
        # {'vid': int, 'spelling': int, 'reading': int, 'reviews': list[dict]}

        # Sort all reviews chronologically in a list
        self.sorted_reviews: list[dict] = []
        vid_word_dict = {}

        for word in self.words:
            vid_word_dict[word["vid"]] = word
            for review in word["reviews"]:
                review["vid"] = word["vid"]
                review["spelling"] = word["spelling"]
                review["reading"] = word["reading"]
                self.sorted_reviews.append(review)

        self.vid_word_dict = vid_word_dict
        self.sorted_reviews = sorted(self.sorted_reviews, key=lambda r: r["timestamp"])

        # FSRS
        fsrs = FsrsWrapper()

        # Optimization
        params_file = Path("optimal_parameters.json")
        if optimize:
            fsrs.optimize_from_words(self.words)
            with open(params_file, "w") as file:
                dump(fsrs.scheduler.parameters, file)
        elif params_file.exists() and not ignore_optimization:
            created = datetime.fromtimestamp(params_file.stat().st_mtime)
            logging.info(f"Using optimal parameters created on {created.isoformat()}")
            with open(params_file, "r") as file:
                optimal_parameters = load(file)
            fsrs.scheduler = Scheduler(optimal_parameters, enable_fuzzing=False)

        fsrs.add_words(self.words)
        self.fsrs = fsrs

    def get_hardest_words(self, top: int = 10) -> list:
        """Get the words with the highest FSRS difficulty."""
        dsc_diff_deck = sorted(
            self.fsrs.deck.values(), key=lambda c: c.difficulty, reverse=True
        )

        results = []
        for i in range(top):
            results.append(self.vid_word_dict[dsc_diff_deck[i].card_id])

        return results

    def get_total_review_count(self) -> int:
        return sum([len(w["reviews"]) for w in self.words])

    def get_reviewed_word_count(self) -> int:
        return len(self.words)

    def get_oldest_dues(self, top: int = 10) -> int:
        asc_due_deck = sorted(self.fsrs.deck.values(), key=lambda c: c.due)

        results = []
        for i in range(top):
            results.append(self.vid_word_dict[asc_due_deck[i].card_id])

        return results

    def get_fsrs_known_words(self) -> int:
        return sum(1 for card in self.fsrs.deck.values() if card.state == State.Review)

    def get_firt_learned_words(self, top: int = 10) -> list[dict]:
        added_words: set = set()
        results: list[dict] = []
        i = 0
        while len(added_words) != top and i < len(self.sorted_reviews):
            w = self.sorted_reviews[i]
            if w["spelling"] not in added_words:
                added_words.add(w["spelling"])
                results.append(self.vid_word_dict[w["vid"]])
            i += 1

        return results

    def plot_review_timeline(
        self, by: Literal["month", "day", "hour"] = "month", cumulative: bool = False
    ):
        """Plot a line graph of review counts over time."""

        if not self.sorted_reviews:
            raise ValueError("No reviews to plot")

        if by not in {"day", "hour", "month"}:
            raise ValueError('Parameter "by" must be "month", "day" or "hour"')

        # build grouping keys (datetime truncated to day or hour)
        keys = []
        for r in self.sorted_reviews:
            ts = r.get("timestamp")
            if ts is None:
                continue
            dt = datetime.fromtimestamp(int(ts))
            if by == "month":
                dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif by == "day":
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # hour
                dt = dt.replace(minute=0, second=0, microsecond=0)
            keys.append(dt)

        counts = Counter(keys)
        if not counts:
            raise ValueError("No valid timestamps found in reviews")

        # sort by time
        sorted_times = sorted(counts.keys())
        x = sorted_times
        y = [counts[t] for t in x]

        if cumulative:
            y = list(accumulate(y))

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(x, y, marker="o", linestyle="-")
        ax.set_xlabel("Time")
        ax.set_ylabel("Cumulative reviews" if cumulative else "Reviews")
        ax.set_title("Review timeline")

        # nice date formatting
        if by == "day":
            locator = mdates.AutoDateLocator()
            formatter = mdates.DateFormatter("%Y-%m-%d")
        else:
            locator = mdates.AutoDateLocator()
            formatter = mdates.DateFormatter("%Y-%m-%d %H:%M")

        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate()

        return fig

    def plot_known_words(self) -> None:
        plot_known_words_(self.fsrs.review_logs, scheduler=self.fsrs.scheduler)

    # def get_fsrs_due_cards(self) -> list[dict]:
    # NOT possible: the JSON data does not indicate if a word is blacklisted or not


a = SrsDataWrapper("../reviews.json")
