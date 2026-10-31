"""Refresh the homepage's offers from the public REWE store page.

This first no-cost source is limited to REWE Rosenberger Str. 104 in
Sulzbach-Rosenberg. The scraper fails closed if the page cannot be read or its
validity dates cannot be understood, so a temporary source change won't erase
the last published data.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OFFERS_FILE = ROOT / "angebote.json"
SOURCE_URL = "https://www.rewe.de/angebote/sulzbach-rosenberg/461687/rewe-rosenberger-str-104/"
STORE = "REWE, Rosenberger Str. 104"
REGION = "Sulzbach-Rosenberg, nur dieser Markt"


class VisibleText(HTMLParser):
    """Collect readable page text while ignoring scripts and styling."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if self.skip_depth == 0:
            for key, value in attrs:
                if key.lower() in {"alt", "aria-label", "title"} and value:
                    self.parts.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            cleaned = " ".join(data.split())
            if cleaned:
                self.parts.append(cleaned)


def get_page_text() -> str:
    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "UltraWhiteDealsBot/1.0 (+weekly public offer check)"},
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"REWE-Seite antwortete mit HTTP {response.status}")
        raw = response.read()
    parser = VisibleText()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(parser.parts)


def parse_validity(text: str, today: date) -> tuple[date, date]:
    # The REWE market page presents its flyer dates as e.g. "26.10. bis 01.11.".
    match = re.search(
        r"Diese Woche\s*(\d{1,2})\.(\d{1,2})\.\s*bis\s*(\d{1,2})\.(\d{1,2})\.",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise RuntimeError("Gültigkeitszeitraum auf der REWE-Seite nicht erkannt")
    day1, month1, day2, month2 = map(int, match.groups())
    year1 = today.year
    if month1 > today.month + 6:
        year1 -= 1
    start = date(year1, month1, day1)
    year2 = year1 + (1 if month2 < month1 else 0)
    end = date(year2, month2, day2)
    if end < start or (end - start).days > 14:
        raise RuntimeError("Erkannter REWE-Zeitraum ist unplausibel")
    return start, end


def parse_monster_candidates(text: str, valid_from: date, valid_until: date) -> list[dict]:
    offers: list[dict] = []
    # Restrict each candidate to a short section after the product name so a
    # price from a later product card is not accidentally attached to Monster.
    pattern = re.compile(r"Monster\s+Energy(?:\s+Drink)?", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        section = text[match.start() : match.start() + 240]
        # Prefer the sticker price after REWE's promotion label. This avoids
        # mistaking the per-litre comparison price or deposit for the can price.
        price_match = re.search(
            r"(?:Knaller|Aktion)\s*(\d{1,2}[,.]\d{2})\s*€",
            section,
            flags=re.IGNORECASE,
        )
        if not price_match or not re.search(r"0[,\.]5\s*-?\s*l|500\s*ml", section, re.IGNORECASE):
            continue

        is_exact = bool(re.search(r"Ultra\s+White", section, re.IGNORECASE))
        is_variety_offer = bool(re.search(r"versch(?:iedene)?\.?\s+Sorten", section, re.IGNORECASE))
        if not is_exact and not is_variety_offer:
            continue

        price = float(price_match.group(1).replace(",", "."))
        offer = {
            "retailer": STORE,
            "product": "Monster Energy Ultra White" if is_exact else "Monster Energy, verschiedene Sorten",
            "price": price,
            "size": "0,5 l Dose",
            "regionValidity": REGION,
            "verification": "confirmed" if is_exact else "unverified",
            "badge": "ULTRA WHITE BESTÄTIGT" if is_exact else "SORTENANGEBOT",
            "url": SOURCE_URL,
            "validFrom": valid_from.isoformat(),
            "validUntil": valid_until.isoformat(),
        }
        if offer not in offers:
            offers.append(offer)
    return offers


def main() -> int:
    today = datetime.now(ZoneInfo("Europe/Berlin")).date()
    text = get_page_text()
    valid_from, valid_until = parse_validity(text, today)
    offers = parse_monster_candidates(text, valid_from, valid_until)
    offers = [o for o in offers if o["validFrom"] <= today.isoformat() <= o["validUntil"]]

    data = {"updatedAt": today.isoformat(), "offers": offers}
    OFFERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REWE: {len(offers)} passendes Monster-Angebot gefunden; aktualisiert am {today.isoformat()}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (URLError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Angebotssuche abgebrochen; angebote.json bleibt unverändert: {exc}", file=sys.stderr)
        raise SystemExit(1)
