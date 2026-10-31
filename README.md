# Ultra White Deals

Eine statische Homepage für Monster Ultra White Angebote. Das Frontend liest `angebote.json` und zeigt nur Angebote an, deren Preis gültig ist und deren Gültigkeitszeitraum heute einschließt.

## Datenquelle und Aktualisierung

Die bisherige ChatGPT-Automation ist nicht mit dieser Website verbunden und kann `angebote.json` nicht selbst aktualisieren. Die Datei muss derzeit manuell oder durch einen separat eingerichteten Backend-/CI-Job aktualisiert und mit der Website veröffentlicht werden. Die Seite führt selbst keine Prospektsuche aus.

## Angebot eintragen

`angebote.json` enthält ein Objekt mit `updatedAt` und einer Liste `offers`. Beispiel:

```json
{
  "updatedAt": "2026-10-31",
  "offers": [
    {
      "retailer": "Beispielmarkt",
      "product": "Monster Energy Ultra White",
      "price": 0.99,
      "size": "0,5 l Dose",
      "location": "Filialen deutschlandweit",
      "regionValidity": "Sulzbach-Rosenberg, teilnehmende Filialen",
      "verification": "confirmed",
      "badge": "ANGEBOT",
      "url": "https://example.com/angebot",
      "validFrom": "2026-10-29",
      "validUntil": "2026-11-04"
    }
  ]
}
```

Pflichtfelder: `retailer` und `price` (Euro als Zahl). `product`, `size`, `regionValidity` (Filial-/Regionalgültigkeit), `location` (älteres Ersatzfeld), `badge`, `url`, `validFrom` und `validUntil` sind optional. Datumsangaben bitte im Format `JJJJ-MM-TT` eintragen. `verification` ist `confirmed`, wenn Ultra White ausdrücklich belegt ist. Bei Sammelangeboten wie „verschiedene Sorten“ bitte `unverified` verwenden oder das Feld weglassen; die Seite kennzeichnet das dann als nicht sortenrein bestätigt. `url` sollte direkt zur Angebotsquelle führen. Die Seite blendet Angebote außerhalb ihres Gültigkeitszeitraums automatisch aus.

Für die gewünschte automatische Suche wird zusätzlich ein geplanter Backend-Job benötigt, der Prospekte prüft, die Quelle und den Prüfstatus speichert und `angebote.json` veröffentlicht. Dafür muss die Ausführungsumgebung der Website (zum Beispiel GitHub Pages mit GitHub Actions oder ein Webhost mit Cronjobs) feststehen. Zugangsdaten gehören ausschließlich in die Secrets dieser Umgebung, nie in `app.js` oder sonstigen Browsercode.

## Lokal ansehen

Da der Browser die JSON-Datei über HTTP laden muss, die Seite mit einem einfachen lokalen Webserver öffnen, zum Beispiel mit der VS-Code-Erweiterung „Live Server“. `index.html` und `angebote.json` müssen dabei im selben Ordner liegen.

## Auf GitHub Pages veröffentlichen

Der Workflow `.github/workflows/pages.yml` veröffentlicht die Homepage automatisch, sobald Änderungen in den Branch `main` übertragen werden. Er kann auch im GitHub-Tab **Actions** manuell gestartet werden.

1. Ein neues Repository auf GitHub anlegen und den Branch `main` verwenden.
2. Alle Projektdateien einschließlich des Ordners `.github/workflows` in dieses Repository hochladen.
3. Im Repository **Settings → Pages** öffnen und als Quelle **GitHub Actions** auswählen.
4. Im Tab **Actions** prüfen, ob „Homepage auf GitHub Pages veröffentlichen“ erfolgreich durchgelaufen ist. Die veröffentlichte Adresse wird beim Workflow-Lauf angezeigt.

Dieser Workflow veröffentlicht die Website bei Änderungen. Er sucht noch nicht selbst nach Angeboten. Dafür braucht es einen separaten wöchentlichen Job mit Prospektquellen und einem Verfahren, das Preis, Produkt und regionale Gültigkeit prüft, bevor `angebote.json` aktualisiert wird.
