from fsrs import Scheduler, Card, Rating, ReviewLog, Optimizer
from datetime import datetime, timezone
import logging


class FsrsWrapper:
    def __init__(self):
        self.deck: dict[Card] = {}  # vid: Card
        self.review_logs: dict[ReviewLog] = {}  # vid: ReviewLog
        self.scheduler = Scheduler()
        self.grade_dict: dict = {
            "fail": Rating.Again,
            "nothing": Rating.Again,
            "something": Rating.Again,
            "hard": Rating.Hard,
            "okay": Rating.Good,
            "easy": Rating.Easy,
        }

    def add_word(self, jpdb_word: dict) -> None:
        # {'vid': int, 'spelling': int, 'reading': int, 'reviews': list[dict]}
        vid: int = jpdb_word["vid"]
        if vid not in self.deck:
            self.deck[vid] = Card(card_id=vid)

        # Empty card
        card: Card = self.deck[vid]
        reviewed: bool = False

        for review in jpdb_word["reviews"]:
            # {'timestamp': int, 'grade': str, 'from_anki': bool}

            grade = review["grade"]
            if grade not in self.grade_dict:
                continue

            reviewed = True
            card, review_log = self.scheduler.review_card(
                card,
                rating=self.grade_dict[grade],
                review_datetime=datetime.fromtimestamp(
                    review["timestamp"], tz=timezone.utc
                ),
            )

        # Replace the empty card with the reviewed one:
        if reviewed:
            self.deck[vid] = card
            self.review_logs[vid] = review_log

    def optimize_from_words(self, jpdb_words: list[dict]) -> Scheduler:
        """Optimize the scheduler from the words' review history."""
        for word in jpdb_words:
            self.add_word(word)

        review_logs: list = list(self.review_logs.values())
        optimizer = Optimizer(review_logs)
        optimal_parameters = optimizer.compute_optimal_parameters()
        self.scheduler = Scheduler(optimal_parameters)
        logging.info(f"Scheduler optimized from {len(jpdb_words)} words.")

    def add_words(self, jpdb_words: list[dict]) -> None:
        for word in jpdb_words:
            self.add_word(word)


scheduler = Scheduler()
card = scheduler.review_card
