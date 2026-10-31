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
        "retailer": "Kaufland, Krötenseestraße 1",
        "region": "Sulzbach-Rosenberg, diese Filiale",
        "url": "https://filiale.kaufland.de/service/filiale/sulzbach-rosenberg-2400.html",
        "kind": "standard",
    },
    {
        "retailer": "Kaufland, Am Bergsteig 1 (Amberg)",
        "region": "Amberg, diese Filiale",
        "url": "https://filiale.kaufland.de/service/filiale/amberg-4750.html",
        "kind": "standard",
    },
    {
        "retailer": "Monster-Angebote bei Netto (kaufDA)",
        "region": "kaufDA-Händlerangebot; Teilnahme und Preis im lokalen Netto-Markt prüfen",
        "url": "https://www.kaufda.de/Angebote/Monster-Energy",
        "kind": "kaufda_netto",
    },
    {
        "retailer": "Monster-Angebote in Amberg (kaufDA)",
        "region": "kaufDA-Angebotsübersicht Amberg; Filialteilnahme und regionale Preisabweichungen prüfen",
        "url": "https://www.kaufda.de/Amberg-Oberpf/Angebote/Energydrink",
        "kind": "kaufda_area",
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
    if kind in {"kaufda_area", "kaufda_netto"}:
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
            if 0 <= (end - start).days <= 14 and start <= today <= end:
                return start, end
        raise RuntimeError("Kein aktuell gültiger Angebotszeitraum in der Angebotsübersicht erkannt")
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
        r"(?<![\d,.])(\d{1,2}[,.]\d{2})\s*€",
    ]
    for pattern in patterns:
        match = re.search(pattern, section, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def retailer_from_context(section: str) -> str | None:
    retailers = [
        (r"Netto Marken-Discount", "Netto Marken-Discount"),
        (r"Netto mit dem Scottie", "Netto"),
        (r"E\s*center", "E center"),
        (r"ALDI\s*SÜD", "ALDI SÜD"),
        (r"Getränke Hoffmann", "Getränke Hoffmann"),
        (r"REWE", "REWE"),
        (r"Kaufland", "Kaufland"),
        (r"Penny", "PENNY"),
        (r"Lidl", "Lidl"),
        (r"EDEKA", "EDEKA"),
        (r"diska", "diska"),
        (r"GLOBUS", "GLOBUS"),
        (r"Norma", "Norma"),
        (r"Müller", "Müller"),
        (r"nahkauf", "nahkauf"),
    ]
    matches = []
    for pattern, retailer in retailers:
        match = re.search(pattern, section, flags=re.IGNORECASE)
        if match:
            matches.append((match.start(), retailer))
    return min(matches)[1] if matches else None


def unit_price_per_liter(section: str) -> float | None:
    patterns = [
        r"1\s*l\s*=\s*([\d]+[,.][\d]{2})",
        r"\(\s*([\d]+[,.][\d]{2})\s*/\s*l\s*\)",
        r"\b([\d]+[,.][\d]{2})\s*/\s*l\b",
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
    pattern = re.compile(r"\bMonster\b", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        section = text[max(0, match.start() - 160) : match.start() + 260]
        if not re.search(r"Energy|Energydrink", section, flags=re.IGNORECASE):
            continue
        after_product = text[match.start() : match.start() + 260]
        if source["kind"] == "kaufda_netto":
            netto_card = re.search(
                r"Energy Drink von Monster für\s*([0-9][,.][0-9]{2})\s*€\s*bei\s+(Netto Marken-Discount)\s*im Angebot",
                section,
                flags=re.IGNORECASE,
            )
            if not netto_card:
                continue
            price = float(netto_card.group(1).replace(",", "."))
            retailer = netto_card.group(2)
        else:
            price = get_offer_price(after_product)
            retailer = retailer_from_context(after_product) if source["kind"] == "kaufda_area" else source["retailer"]
        if price is None or price <= 0 or price > 10:
            continue
        has_500ml = bool(re.search(r"0[,\.]5\s*-?\s*l|500\s*ml", section, re.IGNORECASE))
        unit_price = unit_price_per_liter(after_product)
        inferred_500ml = bool(
            unit_price is not None
            and abs(unit_price * 0.5 - price) <= 0.03
        )
        if not has_500ml and not inferred_500ml:
            continue

        if not retailer:
            continue
        is_exact = bool(re.search(r"Ultra\s+White", section, re.IGNORECASE))
        is_variety = bool(re.search(r"versch(?:iedene)?\.?\s+Sorten", section, re.IGNORECASE))
        offers.append(
            {
                "retailer": retailer,
                "product": "Monster Energy Ultra White" if is_exact else "Monster Energy, verschiedene Sorten" if is_variety else "Monster Energy (Sorte nicht angegeben)",
                "price": price,
                "size": "0,5 l Dose" if has_500ml else "0,5 l Dose (aus Grundpreis abgeleitet)",
                "regionValidity": f"{source['region']}; Händler: {retailer}",
                "verification": "confirmed" if is_exact else "unverified",
                "badge": "ULTRA WHITE BESTÄTIGT" if is_exact else "SORTENANGEBOT NICHT BESTÄTIGT",
                "url": source["url"],
                "validFrom": valid_from.isoformat(),
                "validUntil": valid_until.isoformat(),
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

