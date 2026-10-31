# Monster Ultra White Deals

Die statische Homepage zeigt aktuelle Angebote und eine Vorschau auf die nächste Woche aus `angebote.json`. GitHub Actions aktualisiert die Datei wöchentlich; GitHub Pages veröffentlicht die Änderung anschließend.

## Suchgebiet und Quellen

Der Suchlauf prüft die lokalen Energydrink-Angebotsübersichten von kaufDA für Amberg, die kaufDA-Monster-Angebotsseite für laufende und kommende Prospekte sowie die Angebotsseite von Kaufland für Sulzbach-Rosenberg und Amberg. kaufDA liefert Händler- und Preisangaben; bei allgemeinen Händlerangeboten ist die Teilnahme einer konkreten Filiale nicht separat belegt. Die Seiten weisen auf mögliche regionale Preisabweichungen hin, daher wird die lokale Verfügbarkeit nicht garantiert angezeigt. Die zuvor direkt abgefragten REWE-, EDEKA- und Netto-Seiten blockieren GitHub Actions teilweise mit HTTP 403 und werden nicht mehr einzeln abgefragt.

Ein Angebot gilt als **bestätigt**, wenn die Quelle ausdrücklich Monster Ultra White nennt. Allgemeine Monster-Angebote ohne Sortenangabe werden als `unverified` angezeigt. Es werden nur 500-ml-Angebote übernommen; die Dosen-Größe darf aus dem angezeigten Literpreis abgeleitet werden. Der Suchlauf speichert auch Treffer, deren Angebotszeitraum in der nächsten Kalenderwoche beginnt. Die Homepage zeigt diese in einem eigenen Vorschau-Bereich unter den aktuellen Angeboten. Wenn eine Quelle ausfällt, bleiben noch gültige frühere Treffer dieser Quelle erhalten. Wenn keine Quelle erfolgreich geprüft wird, bleibt `angebote.json` unverändert.

## Automatisierung

Der Workflow `.github/workflows/weekly-offers.yml` läuft montags um 08:13 Uhr (Europe/Berlin), nach Änderungen am Suchskript oder Workflow sowie manuell über **Actions → Wöchentliche Angebotssuche → Run workflow**. Damit der Job `angebote.json` committen kann, muss unter **Settings → Actions → General → Workflow permissions** Schreibzugriff für `GITHUB_TOKEN` erlaubt sein. Die Homepage wird direkt nach jedem Suchlauf veröffentlicht.

## Angebotsdaten und lokale Vorschau

`angebote.json` enthält `updatedAt` und `offers` mit Händler, Produkt, Preis, Größe, Gültigkeit, Regionalhinweis, Prüfstatus und Quellenlink. Datumsangaben stehen im Format `JJJJ-MM-TT`; `verification` ist `confirmed` oder `unverified`. Abgelaufene Angebote werden im Browser ausgeblendet.

Für eine lokale Vorschau `index.html` mit einem lokalen HTTP-Server öffnen, etwa VS-Code Live Server. `index.html` und `angebote.json` müssen unter derselben Adresse liegen. Zugangsdaten oder API-Schlüssel werden für diese Variante nicht benötigt.

