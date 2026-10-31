"""Refresh nearby public retailer offers without paid APIs or credentials."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OFFERS_FILE = ROOT / "angebote.json"
SOURCES = [
    {
        "retailer": "REWE, Rosenberger Str. 104",
        "region": "Sulzbach-Rosenberg, dieser Markt",
        "url": "https://www.rewe.de/angebote/sulzbach-rosenberg/461687/rewe-rosenberger-str-104/",
        "kind": "rewe",
    },
    {
        "retailer": "Kaufland, Krötenseestraße 1",
        "region": "Sulzbach-Rosenberg, diese Filiale",
        "url": "https://filiale.kaufland.de/service/filiale/sulzbach-rosenberg-2400.html",
        "kind": "standard",
    },
    {
        "retailer": "E center Kunert, Rosenberger Straße 40",
        "region": "Sulzbach-Rosenberg, dieser Markt",
        "url": "https://www.edeka.de/maerkte/022706/",
        "kind": "standard",
    },
    {
        "retailer": "Netto Marken-Discount, Rosenberger Straße 40",
        "region": "Sulzbach-Rosenberg, diese Filiale",
        "url": "https://www.netto-online.de/filialen/sulzbach-rosenberg/rosenberger-strasse-40/2806/",
        "kind": "netto",
    },
    {
        "retailer": "Netto Marken-Discount, Hauptstraße 38",
        "region": "Sulzbach-Rosenberg, diese Filiale",
        "url": "https://www.netto-online.de/filialen/sulzbach-rosenberg/hauptstr-38/8349",
        "kind": "netto",
    },
    {
        "retailer": "ALDI SÜD",
        "region": "ALDI-SÜD-Aktionsseite; Verfügbarkeit im lokalen Markt prüfen",
        "url": "https://www.aldi-sued.de/angebote",
        "kind": "aldi",
    },
    {
        "retailer": "PENNY",
        "region": "PENNY-Angebotsseite; Teilnahme des lokalen Markts nicht separat bestätigt",
        "url": "https://www.penny.de/angebote/",
        "kind": "weekly",
    },
    {
        "retailer": "Lidl, Karolinenstraße 26",
        "region": "Prospektübersicht Sulzbach-Rosenberg; Lidl-Markt vor Ort",
        "url": "https://www.kaufda.de/Sulzbach-Rosenberg/Lidl/p-r74",
        "kind": "kaufda",
    },
]


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


def get_page_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "UltraWhiteDealsBot/1.0 (weekly public offer check)"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} für {url}")
        raw = response.read()
    parser = VisibleText()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return " ".join(parser.parts)


def parse_date(value: str, year_hint: int) -> date:
    parts = [int(part) for part in re.findall(r"\d+", value)]
    if len(parts) == 3:
        day, month, year = parts
        if year < 100:
            year += 2000
        return date(year, month, day)
    if len(parts) == 2:
        return date(year_hint, parts[1], parts[0])
    raise ValueError(f"Datum nicht erkannt: {value}")


def parse_validity(text: str, today: date, kind: str) -> tuple[date, date]:
    if kind in {"weekly", "aldi"}:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=5)
    if kind == "kaufda":
        date_ranges = re.findall(
            r"(?:Mo\.\s*)?(\d{1,2}\.\d{1,2}\.)\s*-\s*(?:Sa\.\s*)?(\d{1,2}\.\d{1,2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        for start_text, end_text in date_ranges:
            start = parse_date(start_text, today.year)
            end = parse_date(end_text, today.year)
            if start.month > end.month:
                start = start.replace(year=start.year - 1)
            if start <= today <= end:
                return start, end
        raise RuntimeError("Kein aktuell gültiger Lidl-Prospekt auf kaufDA erkannt")
    if kind == "rewe":
        match = re.search(
            r"Diese Woche\s*(\d{1,2}\.\d{1,2}\.)\s*bis\s*(\d{1,2}\.\d{1,2}\.)",
            text,
            flags=re.IGNORECASE,
        )
    elif kind == "netto":
        matches = re.findall(
            r"Filial-Angebote\s+ab Montag,?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})",
            text,
            flags=re.IGNORECASE,
        )
        starts = [parse_date(value, today.year) for value in matches]
        starts = [start for start in starts if start <= today]
        if not starts:
            raise RuntimeError("Aktueller Netto-Prospektzeitraum nicht erkannt")
        start = max(starts)
        end = start + timedelta(days=5)
        if today > end:
            raise RuntimeError("Netto-Prospekt auf der Seite ist nicht mehr aktuell")
        return start, end
    else:
        match = re.search(
            r"Gültig vom\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+bis(?: zum)?\s+(\d{1,2}\.\d{1,2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            match = re.search(
                r"gültig von Montag,?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})\s*[-–]\s*Samstag,?\s*(\d{1,2}\.\d{1,2}\.\d{2,4})",
                text,
                flags=re.IGNORECASE,
            )
    if not match:
        raise RuntimeError("Gültigkeitszeitraum nicht erkannt")
    start = parse_date(match.group(1), today.year)
    end = parse_date(match.group(2), start.year)
    if end < start and start.month == 12 and end.month == 1:
        end = end.replace(year=end.year + 1)
    if end < start or (end - start).days > 14:
        raise RuntimeError("Erkannter Angebotszeitraum ist unplausibel")
    return start, end


def get_offer_price(section: str) -> float | None:
    patterns = [
        r"(?:Knaller|Aktion)\s*(\d{1,2}[,.]\d{2})\s*€",
        r"(?:Angebotspreis|Festpreis von)\s*(\d{1,2}[,.]\d{2})\s*€?",
        r"\bnur\s*(\d{1,2}[,.]\d{2})\b",
        r"(?:UVP|statt)\s*\d{1,2}[,.]\d{2}\s+(\d{1,2}[,.]\d{2})\s*\*?",
        r"-\d{1,2}\s*%\s*(\d{1,2}[,.]\d{2})\b",
        r"\bab\s*(\d{1,2}[,.]\d{2})\s*€",
    ]
    for pattern in patterns:
        match = re.search(pattern, section, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def parse_monster_candidates(
    text: str, source: dict, valid_from: date, valid_until: date, today: date
) -> list[dict]:
    offers: list[dict] = []
    pattern = re.compile(r"Monster\s+Energy(?:\s+Drink)?", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        section = text[max(0, match.start() - 100) : match.start() + 300]
        price = get_offer_price(section)
        if price is None or price <= 0 or price > 10:
            continue
        has_500ml = bool(re.search(r"0[,\.]5\s*-?\s*l|500\s*ml", section, re.IGNORECASE))
        unit_price = re.search(r"1\s*l\s*=\s*([\d]+[,.][\d]{2})", section, re.IGNORECASE)
        inferred_500ml = bool(
            source["kind"] == "kaufda"
            and unit_price
            and abs(float(unit_price.group(1).replace(",", ".")) * 0.5 - price) <= 0.03
        )
        if not has_500ml and not inferred_500ml:
            continue

        offer_start, offer_end = valid_from, valid_until
        if source["kind"] == "aldi":
            preceding = text[max(0, match.start() - 700) : match.start()]
            start_labels = re.findall(
                r"Angebote ab (?:Montag|Donnerstag|Freitag|Samstag)\s+(\d{1,2}\.\d{1,2}\.?)",
                preceding,
                flags=re.IGNORECASE,
            )
            if not start_labels:
                continue
            offer_start = parse_date(start_labels[-1], valid_from.year)
            offer_end = offer_start + timedelta(days=5 - offer_start.weekday())
            if not offer_start <= today <= offer_end:
                continue

        is_exact = bool(re.search(r"Ultra\s+White", section, re.IGNORECASE))
        is_variety = bool(re.search(r"versch(?:iedene)?\.?\s+Sorten", section, re.IGNORECASE))
        offers.append(
            {
                "retailer": source["retailer"],
                "product": "Monster Energy Ultra White" if is_exact else "Monster Energy, verschiedene Sorten" if is_variety else "Monster Energy (Sorte nicht angegeben)",
                "price": price,
                "size": "0,5 l Dose" if has_500ml else "0,5 l Dose (aus Grundpreis abgeleitet)",
                "regionValidity": source["region"],
                "verification": "confirmed" if is_exact else "unverified",
                "badge": "ULTRA WHITE BESTÄTIGT" if is_exact else "SORTENANGEBOT NICHT BESTÄTIGT",
                "url": source["url"],
                "validFrom": offer_start.isoformat(),
                "validUntil": offer_end.isoformat(),
            }
        )
    # Repeated title/alt text can expose the same product card more than once.
    unique: dict[tuple[str, float, str], dict] = {}
    for offer in offers:
        key = (offer["retailer"], offer["price"], offer["product"])
        unique[key] = offer
    return list(unique.values())


def load_previous() -> dict:
    try:
        return json.loads(OFFERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"updatedAt": None, "offers": []}


def main() -> int:
    today = datetime.now(ZoneInfo("Europe/Berlin")).date()
    previous = load_previous()
    found: list[dict] = []
    successful: set[str] = set()
    failed: set[str] = set()

    for source in SOURCES:
        try:
            text = get_page_text(source["url"])
            start, end = parse_validity(text, today, source["kind"])
            offers = parse_monster_candidates(text, source, start, end, today)
            found.extend(o for o in offers if o["validFrom"] <= today.isoformat() <= o["validUntil"])
            successful.add(source["retailer"])
            print(f"{source['retailer']}: Quelle geprüft, {len(offers)} Treffer.")
        except (URLError, TimeoutError, RuntimeError, ValueError) as exc:
            failed.add(source["retailer"])
            print(f"{source['retailer']}: Quelle nicht auswertbar ({exc}).", file=sys.stderr)

    if not successful:
        raise RuntimeError("Keine Angebotsquelle konnte ausgewertet werden; Datei bleibt unverändert")

    # Keep still-valid old deals for sources that failed this run; replace data
    # only for sources that were actually read successfully.
    for offer in previous.get("offers", []):
        retailer = offer.get("retailer", "")
        if retailer in failed and offer.get("validUntil", "") >= today.isoformat():
            found.append(offer)

    data = {"updatedAt": today.isoformat(), "offers": found}
    OFFERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Insgesamt {len(found)} aktuell gültige Monster-Angebote gespeichert.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (URLError, TimeoutError, RuntimeError, ValueError) as exc:
        print(f"Suche abgebrochen; angebote.json bleibt unverändert: {exc}", file=sys.stderr)
        raise SystemExit(1)

