# Deploye den Fork in dein mittwald-Testprojekt

Diese Anleitung verwendet das Container Hosting deines mStudio-Projekts.
GitHub Actions baut ein AMD64-Image, prüft dessen Start mit schreibgeschütztem
Dateisystem und veröffentlicht es in `ghcr.io/tjorvez/open-webui`.
Der Deploy verwendet den Digest des getesteten Images.

Chat, Dokument-Embeddings und Spracherkennung verwenden ausschließlich mittwald
AI Hosting. Ollama und direkte Provider-Verbindungen von Nutzern sind deaktiviert.
Für den ersten Deploy bleiben die Standard-Abhängigkeiten für Dokumentverarbeitung
und Chroma enthalten. Lokale Modellgewichte werden nicht ins Image geladen.

## Bereite das mStudio-Projekt vor

1. Verwende ein Testprojekt mit aktiviertem Container Hosting und mindestens
   4 GB verfügbarem RAM. Der Container ist auf 2 CPUs und 4 GB RAM begrenzt.
2. Erstelle einen mStudio-API-Token mit Zugriff auf dieses Projekt.
3. Ermittle die UUID des `default`-Stacks über
   `GET https://api.mittwald.de/v2/projects/{projectId}/stacks/`.
   `MITTWALD_STACK_ID` ist diese UUID, keine Projektkennung wie `p-123456`.
4. Erstelle im Bereich **AI Hosting** einen API-Key. Prüfe, dass dein Tarif
   die Modelle `Qwen3-Embedding-8B` und `whisper-large-v3-turbo` bereitstellt.
5. Reserviere eine HTTPS-Subdomain für die Anwendung.

Der Workflow ersetzt die Stack-Definition. Die Vorprüfung bricht ab, wenn
der Zielstack andere Services oder Volumes enthält. Wenn du bestehende
Container im selben Projekt behalten willst, ergänze zuerst deren vollständige
Definitionen in `stack.json` und prüfe sie vor dem Deploy.

## Hinterlege die GitHub-Konfiguration

Aktiviere GitHub Actions im Fork. Erstelle unter **Settings → Environments**
das Environment `mittwald-testing`.

Hinterlege dort diese Secrets:

| Secret | Inhalt |
| --- | --- |
| `MITTWALD_API_TOKEN` | mStudio-API-Token für das Testprojekt |
| `MITTWALD_AI_API_KEY` | API-Key für mittwald AI Hosting |
| `WEBUI_SECRET_KEY` | Dauerhafter zufälliger Schlüssel, mindestens 32 Zeichen |
| `WEBUI_ADMIN_EMAIL` | E-Mail des ersten Administrators |
| `WEBUI_ADMIN_PASSWORD` | Passwort des ersten Administrators, mindestens 12 Zeichen |

Erzeuge den dauerhaften Schlüssel lokal mit `openssl rand -hex 32`.
Behalte ihn bei allen Updates bei.

Hinterlege dort diese Variablen:

| Variable | Inhalt |
| --- | --- |
| `MITTWALD_STACK_ID` | UUID des Zielstacks |
| `WEBUI_URL` | Öffentliche URL, z. B. `https://chat-test.example.de` |

Der Build erhält `packages: write` für den eingebauten `GITHUB_TOKEN`.
Ein eigener GitHub-Token wird für die Veröffentlichung nicht benötigt.

Die Repository-Variable `MITTWALD_DEPLOY_ENABLED` bleibt zunächst unset.
Wenn du sie später auf `true` setzt, deployt jeder erfolgreiche Push auf `main`
automatisch. Diese Variable gehört auf Repository-Ebene, da der Workflow sie
vor dem Start des Environment-Jobs auswertet.

## Veröffentliche das erste Image

1. Committe und pushe die gewünschten Änderungen nach `main`.
2. Öffne **Actions → Build and deploy mittwald testing**.
3. Warte auf den erfolgreichen Build samt Container-Starttest.
4. Öffne das Package `open-webui` unter deinem GitHub-Profil.
5. Bei einem privaten Package hinterlege im mStudio unter
   **Container → Registries → ghcr.io** deinen GitHub-Benutzernamen und einen
   Token mit `read:packages`, der Zugriff auf dieses Package hat.
   Bei einem öffentlichen Package sind keine Registry-Zugangsdaten erforderlich.

Das Image bekommt `git-<vollständige Commit-SHA>` und den Branch- bzw. Tag-Namen.
Der getestete Digest steht in der Zusammenfassung des Workflows.
Die Upstream-Jobs für Docker Hub und Helm wurden aus dem Build entfernt.
Die Upstream-Release- und PyPI-Jobs laufen nur im Originalrepository.

## Starte den ersten Deploy

1. Starte denselben Workflow über **Run workflow** auf `main`.
2. Aktiviere das Eingabefeld **Deploy this main commit to mittwald testing**.
3. Prüfe im mStudio, dass der Container `open-webui` läuft.
4. Weise deine Subdomain dem Container auf Port `8080` zu und aktiviere HTTPS.
5. Öffne die URL aus `WEBUI_URL` und melde dich mit dem Admin-Account an.
6. Prüfe die Modellliste und sende einen Testchat. Teste anschließend ein
   Dokument mit einer Rückfrage zum Inhalt, damit auch Embeddings geprüft werden.

Der Admin wird nur angelegt, solange die Datenbank keine Nutzer enthält.
Ein später geändertes Secret setzt kein bestehendes Admin-Passwort zurück.
Öffentliche Registrierung bleibt ausgeschaltet. Lege Testnutzer im Adminbereich an.

## Aktualisiere die Anwendung

Pushe einen neuen Commit auf `main` und starte den Workflow erneut mit aktiviertem
Deploy-Feld. Mit `MITTWALD_DEPLOY_ENABLED=true` erfolgt der Deploy automatisch.
`dev` und Release-Tags veröffentlichen Images, deployen aber nicht ins Testprojekt.

Die Umgebungsvariablen sind für die Deployment-Konfiguration maßgeblich.
`ENABLE_PERSISTENT_CONFIG=false` verhindert, dass ältere Einstellungen aus der
Datenbank die Provider-Konfiguration überschreiben. Änderungen an allgemeinen
Admin-Einstellungen müssen daher in `stack.json` erfolgen; Änderungen im
Adminbereich an diesen Einstellungen werden nicht dauerhaft übernommen.
Accounts, Chats, Workspace-Inhalte und Uploads bleiben im Datenvolume gespeichert.

Sichere vor Updates `open-webui-data`, vorzugsweise während der Container gestoppt
ist. Behalte die Volume-Namen bei. Für einen Rollback nach einer Datenbankmigration
brauchst du das vorherige Image und die dazugehörige Datensicherung.
Das Volume `open-webui-runtime` enthält generierte Assets und Laufzeit-Caches.

## Prüfe die Konfiguration lokal

Prüfe Shell-Syntax ohne Zugangsdaten:

```bash
bash -n backend/start-mittwald.sh deploy/mittwald/smoke-test.sh
```

Wenn Docker läuft, baue und prüfe das Image lokal:

```bash
docker build --build-arg PRELOAD_MODELS=false -t open-webui-mittwald:test .
bash deploy/mittwald/smoke-test.sh open-webui-mittwald:test
```

Der Starttest verwendet Dummy-Zugangsdaten und ein isoliertes Netzwerk.
Er prüft Backend-Start, Migrationen, Admin-Anlage und die Frontend-Auslieferung.
Die echten mittwald-Zugangsdaten und die Domain-Verbindung prüfst du nach dem Deploy.
Schreibe gerenderte Stack-Dateien mit Secrets niemals ins Repository.

## Quellen

- [mittwald Container-Deployment mit GitHub Actions](https://developer.mittwald.de/docs/v2/guides/deployment/container-actions/)
- [mittwald Deploy-Action und Stack-Format](https://github.com/mittwald/deploy-container-action)
- [mittwald Container-API und Stack-ID](https://developer.mittwald.de/docs/v2/api/howtos/create-container/)
- [mittwald AI-API und Modelle](https://developer.mittwald.de/docs/v2/platform/aihosting/api-endpoints/supported-endpoints/)
