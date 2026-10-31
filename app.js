const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });

function getWeekLabel() {
  const now = new Date();
  const isoDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  const dayOfWeek = isoDate.getUTCDay() || 7;
  isoDate.setUTCDate(isoDate.getUTCDate() + 4 - dayOfWeek);
  const yearStart = new Date(Date.UTC(isoDate.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil((((isoDate - yearStart) / 86400000) + 1) / 7);
  const start = new Date(now);
  const day = (now.getDay() + 6) % 7;
  start.setDate(now.getDate() - day);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const format = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" });
  return `KW ${weekNumber} · ${format.format(start)} – ${format.format(end)}`;
}

function getNextWeekLabel() {
  const today = new Date();
  const mondayOffset = (today.getDay() + 6) % 7;
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - mondayOffset + 7);
  const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 6);
  const format = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit" });
  return `${format.format(start)} – ${format.format(end)}`;
}

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })
    .format(new Date(year, month - 1, day));
}

function makeOfferCard(offer) {
  const card = document.createElement("article");
  card.className = "offer-card";

  const top = document.createElement("div");
  top.className = "offer-top";
  const retailer = document.createElement("div");
  retailer.className = "retailer";
  const mark = document.createElement("span");
  mark.className = "retailer-mark";
  mark.setAttribute("aria-hidden", "true");
  mark.textContent = (offer.retailer || "?").trim().charAt(0).toUpperCase();
  const retailerName = document.createElement("span");
  retailerName.textContent = offer.retailer;
  retailer.append(mark, retailerName);
  top.append(retailer);
  if (offer.badge) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = offer.badge;
    top.append(badge);
  }
  const bottom = document.createElement("div");
  bottom.className = "offer-bottom";
  const detail = document.createElement("div");
  const product = document.createElement("div");
  product.className = "offer-product";
  product.textContent = offer.product || "Monster Energy Ultra White";
  const price = document.createElement("div");
  price.className = "offer-price";
  price.textContent = euro.format(offer.price);
  const unit = document.createElement("div");
  unit.className = "offer-unit";
  unit.textContent = [offer.size, offer.regionValidity || offer.location].filter(Boolean).join(" · ");
  const validity = document.createElement("div");
  validity.className = "offer-validity";
  const from = formatDate(offer.validFrom);
  const until = formatDate(offer.validUntil);
  validity.textContent = from && until ? `Gültig: ${from}–${until}` : from ? `Gültig ab ${from}` : until ? `Gültig bis ${until}` : "Gültigkeitszeitraum nicht angegeben";
  detail.append(product, price, unit, validity);
  bottom.append(detail);
  const sourceUrl = safeSourceUrl(offer.url);
  if (sourceUrl) {
    const link = document.createElement("a");
    link.className = "offer-link";
    link.href = sourceUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", `Quelle für das Angebot bei ${offer.retailer} öffnen`);
    link.textContent = "Quelle öffnen ↗";
    bottom.append(link);
  }
  card.append(top, bottom);
  return card;
}

function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
  } catch {
    return "";
  }
}

async function loadOffers() {
  document.querySelector("#week-label").textContent = getWeekLabel();
  document.querySelector("#next-week-label").textContent = getNextWeekLabel();
  const grid = document.querySelector("#offers-grid");
  const upcomingGrid = document.querySelector("#upcoming-grid");
  try {
    const response = await fetch("angebote.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Angebotsdatei nicht verfügbar");
    const data = await response.json();
    const today = localDateString();
    const nextWeekEndDate = new Date();
    const mondayOffset = (nextWeekEndDate.getDay() + 6) % 7;
    nextWeekEndDate.setDate(nextWeekEndDate.getDate() - mondayOffset + 13);
    const nextWeekEnd = localDateString(nextWeekEndDate);
    const offers = (Array.isArray(data) ? data : data.offers || []).filter((offer) =>
      Number.isFinite(Number(offer.price)) && Number(offer.price) > 0 &&
      (!offer.validFrom || offer.validFrom <= nextWeekEnd) && (!offer.validUntil || offer.validUntil >= today)
    );
    const currentOffers = offers.filter((offer) => !offer.validFrom || offer.validFrom <= today);
    const upcomingOffers = offers.filter((offer) => offer.validFrom && offer.validFrom > today);
    renderOfferGroup(grid, currentOffers, "Aktuell sind keine Angebote eingetragen.", "Neue Deals erscheinen hier, sobald Preis, Zeitraum und Quelle geprüft wurden.");
    renderOfferGroup(upcomingGrid, upcomingOffers, "Für nächste Woche sind noch keine Angebote gefunden.", "Die Vorschau wird nach der nächsten Prospektprüfung aktualisiert.");
  } catch (error) {
    renderOfferGroup(grid, [], "Angebote gerade nicht erreichbar.", "Bitte lade die Seite später noch einmal.");
    renderOfferGroup(upcomingGrid, [], "Vorschau gerade nicht erreichbar.", "Bitte lade die Seite später noch einmal.");
  }
}

function renderOfferGroup(grid, offers, emptyTitle, emptyText) {
  grid.replaceChildren();
  if (offers.length) {
    offers.forEach((offer) => grid.append(makeOfferCard(offer)));
    return;
  }
  const empty = document.createElement("div");
  empty.className = "empty-card";
  empty.innerHTML = `<div class="empty-symbol" aria-hidden="true">✳</div><strong>${emptyTitle}</strong>${emptyText}`;
  grid.append(empty);
}

loadOffers();

