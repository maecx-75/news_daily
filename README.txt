Diese Version enthält eine GitHub-Action für 90 Sekunden.

Was automatisch passiert:
- Alle 5 Minuten versucht GitHub Actions die 90-Sekunden-Seite zu prüfen.
- Wenn ein neuer 90-Sekunden-Eintrag gefunden wird, werden in headlines.json automatisch aktualisiert:
  - topmeldung90
  - news90_link
  - news90_title

Was nicht automatisch passiert:
- Das Vorschaubild der 90-Sekunden-Kachel bleibt manuell.
  Dafür müsstest du news90.png selbst austauschen.

Wichtig:
- Nach dem Hochladen musst du in GitHub den Tab "Actions" öffnen und Actions aktivieren, falls GitHub danach fragt.
- Die Prüfung läuft frühestens alle 5 Minuten, aber GitHub kann geplante Läufe manchmal verzögern.
