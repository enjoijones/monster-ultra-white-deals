# Monster Ultra White Deals

Die statische Homepage zeigt Angebote aus `angebote.json`. GitHub Actions aktualisiert die Datei wöchentlich; GitHub Pages veröffentlicht die Änderung anschließend.

## Suchgebiet und Quellen

Der Suchlauf prüft die lokalen Energydrink-Angebotsübersichten von kaufDA für Sulzbach-Rosenberg und Amberg sowie die Angebotsseite von Kaufland für Sulzbach-Rosenberg und Amberg. kaufDA liefert Händler- und Preisangaben im regionalen Zusammenhang. Die Übersicht weist aber selbst auf mögliche regionale Preisabweichungen hin; die Teilnahme der einzelnen Filiale wird daher auf der Homepage nicht als garantiert dargestellt. Die zuvor direkt abgefragten REWE-, EDEKA- und Netto-Seiten blockieren GitHub Actions teilweise mit HTTP 403 und werden nicht mehr einzeln abgefragt.

Ein Angebot gilt als **bestätigt**, wenn die Quelle ausdrücklich Monster Ultra White nennt. Allgemeine Monster-Angebote ohne Sortenangabe werden als `unverified` angezeigt. Es werden nur 500-ml-Angebote übernommen; die Dosen-Größe darf aus dem angezeigten Literpreis abgeleitet werden. Wenn eine Quelle ausfällt, bleiben noch gültige frühere Treffer dieser Quelle erhalten. Wenn keine Quelle erfolgreich geprüft wird, bleibt `angebote.json` unverändert.

## Automatisierung

Der Workflow `.github/workflows/weekly-offers.yml` läuft montags um 08:13 Uhr (Europe/Berlin). Ein manueller Start ist im GitHub-Tab **Actions** über **Wöchentliche Angebotssuche → Run workflow** möglich. Damit der Job `angebote.json` committen kann, muss unter **Settings → Actions → General → Workflow permissions** Schreibzugriff für `GITHUB_TOKEN` erlaubt sein. Die Änderung an `angebote.json` löst danach die Pages-Veröffentlichung aus.

## Angebotsdaten und lokale Vorschau

`angebote.json` enthält `updatedAt` und `offers` mit Händler, Produkt, Preis, Größe, Gültigkeit, Regionalhinweis, Prüfstatus und Quellenlink. Datumsangaben stehen im Format `JJJJ-MM-TT`; `verification` ist `confirmed` oder `unverified`. Abgelaufene Angebote werden im Browser ausgeblendet.

Für eine lokale Vorschau `index.html` mit einem lokalen HTTP-Server öffnen, etwa VS-Code Live Server. `index.html` und `angebote.json` müssen unter derselben Adresse liegen. Zugangsdaten oder API-Schlüssel werden für diese Variante nicht benötigt.

