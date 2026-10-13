from pathlib import Path
from pprint import pprint

from src.image_text_extractor import extract_text_from_image
from src.receipt_parser import extract_receipt_data


INPUT_DIRECTORY = Path("data/input")

RECEIPT_FILES = [
    *[f"pag_bol_{index}.jpeg" for index in range(1, 6)],
    *[f"pix_bol_{index}.jpeg" for index in range(1, 4)],
    *[f"pix_tra_{index}.jpeg" for index in range(1, 6)],
]


def main() -> None:
    for filename in RECEIPT_FILES:
        file_path = INPUT_DIRECTORY / filename

        print(f"\n{'=' * 70}")
        print(f"FILE: {filename}")
        print("=" * 70)

        try:
            text = extract_text_from_image(str(file_path))
            receipt_data = extract_receipt_data(
                text,
                source_type="image",
            )

            pprint(receipt_data, sort_dicts=False)

        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
