from __future__ import annotations

import csv
import re
from pathlib import Path


def extract_goods(text: str) -> dict[str, float]:
    """
    Extract every good price from worldmarket.price_pool.

    We first isolate the price_pool block, then capture every pair
    of good_name=price within it.

    Example:
        coal=2.33002
        iron=3.53003

    Returns:
        {"coal": 2.33002, "iron": 3.53003, ...}
    """

    price_pool_match = re.search(
        r'price_pool=\s*\{(.*?)\n\s*\}',
        text,
        re.DOTALL,
    )

    if not price_pool_match:
        raise ValueError("Could not find worldmarket.price_pool.")

    price_pool = price_pool_match.group(1)

    goods: dict[str, float] = {}

    for good, price in re.findall(
        r'(\w+)=([-+]?(?:\d+(?:\.\d*)?|\.\d+))',
        price_pool,
    ):
        goods[good] = float(price)

    if not goods:
        raise ValueError("No goods found in price_pool.")

    return goods


def append_observations(
    output_file: Path,
    game_date: str,
    goods: dict[str, float],
) -> None:
    """
    Append one row per good to goods_prices.csv.

    CSV format:

        date,good,price
        1836-01-02,coal,2.33002
        1836-01-02,iron,3.53003
    """

    file_exists = output_file.exists()

    with output_file.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["date", "good", "price"])

        for good in sorted(goods):
            writer.writerow([
                game_date,
                good,
                f"{goods[good]:.5f}",
            ])
