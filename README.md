# Monster Ultra White Deals

Die statische Homepage zeigt Angebote aus `angebote.json`. Die Datei wird wöchentlich durch GitHub Actions aktualisiert; danach veröffentlicht GitHub Pages die Änderung automatisch.

## Abdeckung

Der kostenlose Suchlauf prüft die öffentlichen Prospektseiten für Sulzbach-Rosenberg und Amberg: REWE und E center Kunert in Sulzbach-Rosenberg, Kaufland in Sulzbach-Rosenberg und Amberg, E center Kunert, zwei EDEKA-Wiesmeth-Märkte und diska in Amberg sowie mehrere Netto-Filialen in Sulzbach-Rosenberg und Amberg. Für ALDI SÜD und Lidl werden Prospektübersichten von kaufDA für beide Orte gelesen. Diese Übersicht belegt nicht immer, dass ein konkreter Markt an einem Angebot teilnimmt; die Homepage weist diese Einschränkung deshalb im Feld zur regionalen Gültigkeit aus. PENNY ist nicht als Filiale vor Ort aufgenommen, weil im näheren Suchgebiet keine lokale Filiale belastbar bestätigt wurde.

Die Suche erfasst nur öffentlich auslesbare Angebotsseiten. Sie deckt daher nicht garantiert jeden einzelnen Markt und nicht jedes Angebot ab. Ein Treffer gilt als **bestätigt**, wenn die Quelle ausdrücklich Monster Ultra White nennt. „Monster Energy“, „verschiedene Sorten“ oder ein Prospektpreis ohne eindeutige Sortenangabe werden als **nicht sortenrein bestätigt** angezeigt. Es werden nur Treffer mit 500-ml-Größe übernommen; bei kaufDA kann die Größe aus dem Grundpreis abgeleitet werden. Wenn eine Quelle ausfällt, bleiben noch gültige frühere Treffer dieser Quelle erhalten. Wenn keine Quelle erfolgreich geprüft werden kann, bleibt `angebote.json` unverändert.

## Automatisierung aktivieren

Der Workflow `.github/workflows/weekly-offers.yml` läuft montags um 08:13 Uhr (Europe/Berlin) und kann im GitHub-Tab **Actions** manuell über **Run workflow** gestartet werden. Damit der Job `angebote.json` committen kann, unter **Settings → Actions → General → Workflow permissions** den Schreibzugriff für `GITHUB_TOKEN` erlauben. Die anschließende Änderung löst den Pages-Workflow aus.

## Angebotsdaten

`angebote.json` enthält `updatedAt` und eine Liste `offers` mit Händler, Produkt, Preis, Größe, Gültigkeit, regionaler Aussage, Prüfstatus und Quellenlink. Datum im ISO-Format `JJJJ-MM-TT`; `verification` ist `confirmed` oder `unverified`. Der Browser blendet abgelaufene Angebote aus.

Für lokale Vorschau `index.html` mit einem lokalen HTTP-Server öffnen, etwa VS-Code Live Server. `index.html` und `angebote.json` müssen unter derselben Adresse liegen.

GitHub Pages veröffentlicht die Website bei Änderungen am Branch `main`. Zugangsdaten oder API-Schlüssel werden für diese Variante nicht benötigt und dürfen nicht in Frontend-Dateien abgelegt werden.

