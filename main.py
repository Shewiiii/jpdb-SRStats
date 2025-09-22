import argparse
import logging
from pathlib import Path
import webbrowser
import sys


def json_path_(s: str) -> Path:
    p = Path(s)
    if p.is_file():
        if p.suffix != ".json":
            raise ValueError
        return p
    else:
        raise FileNotFoundError(s)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def main() -> int:
    parser = argparse.ArgumentParser(description="View stats of your SRS from Jpdb.")
    parser.add_argument(
        "-json_path",
        "-json",
        "-read",
        "-r",
        help="Get the stats of the SRS from a JSON data file. You can get it with the -g option.",
        type=json_path_,
    )
    parser.add_argument(
        "-get_json",
        "-g",
        action="store_true",
        help='Open "https://jpdb.io/export/reviews.json" To get the JSON file.',
    )
    # Add options here

    args = parser.parse_args()

    if args.get_json:
        webbrowser.open("https://jpdb.io/export/reviews.json")
        return 1


if __name__ == "__main__":
    main()
