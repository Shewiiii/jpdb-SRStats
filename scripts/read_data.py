from json import load
from pathlib import Path

from fsrs import State
from fsrs_wrapper import FsrsWrapper


class SrsDataWrapper:
    def __init__(self, json_path: Path) -> None:
        with open(json_path, "r", encoding="utf-8") as file:
            self.raw_data: dict = load(file)

        self.words: list = self.raw_data["cards_vocabulary_jp_en"]
        # {'vid': int, 'spelling': int, 'reading': int, 'reviews': list[dict]}

        vid_word_dict = {}
        for word in self.words:
            vid_word_dict[word["vid"]] = word
        self.vid_word_dict = vid_word_dict

        # FSRS
        fsrs = FsrsWrapper()
        fsrs.optimize_from_words(self.words)
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

    # def get_fsrs_due_cards(self) -> list[dict]:
    # NOT possible: the JSON data does not indicate if a word is blacklisted or not