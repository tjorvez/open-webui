# Lege den Fork als Container im mStudio an

GitHub Actions baut und testet das AMD64-Image deines Forks und veröffentlicht es
in GHCR. Du legst den Container im mStudio an und lädst neue Images manuell.
Verwende dafür `ghcr.io/tjorvez/open-webui:main`.

Chat, Dokument-Embeddings und Spracherkennung verwenden mittwald AI Hosting.
Ollama und direkte Provider-Verbindungen von Nutzern sind deaktiviert.
Das Image enthält die Abhängigkeiten für Dokumentverarbeitung und Chroma,
aber keine vorab geladenen lokalen Modellgewichte.

## Veröffentliche das erste Image

1. Aktiviere GitHub Actions im Fork.
2. Committe und pushe die gewünschten Änderungen nach `main`.
3. Öffne **Actions → Build mittwald container image**.
4. Warte auf den erfolgreichen Build samt Container-Starttest.

Der Workflow verwendet den eingebauten `GITHUB_TOKEN` zum Veröffentlichen.
Der Frontend-Build erhält mit `NODE_BUILD_HEAP_MB=8192` ein Node-Heap-Limit von
8 GB auf dem GitHub-Runner. Das beeinflusst nicht den RAM-Bedarf des laufenden Containers.
Du brauchst dafür keine mittwald-Secrets, keine Stack-ID und kein GitHub-Environment.
Wenn du die zuvor beschriebenen Deploy-Secrets oder das Environment
`mittwald-testing` bereits angelegt hast, kannst du sie aus GitHub entfernen.

Das Image erhält `main` und `git-<vollständige Commit-SHA>` als Tags.
Pushes auf `dev` oder `v*`-Tags veröffentlichen ebenfalls Images.
Den Image-Digest findest du in der Zusammenfassung des Workflows.

## Verbinde die Registry

Öffne im mStudio dein Projekt und den Bereich **Container → Registries**.
Wenn das GitHub-Package privat ist, hinterlege für `ghcr.io` deinen
GitHub-Benutzernamen und einen Token mit `read:packages` und Zugriff auf das Package.
Ein öffentliches Package lässt sich ohne Registry-Zugangsdaten laden.

## Lege den Container an

Erstelle im Containerbereich deines mStudio-Projekts einen Container mit diesen Werten:

| Einstellung | Wert |
| --- | --- |
| Name | `open-webui` |
| Image | `ghcr.io/tjorvez/open-webui:main` |
| Startbefehl | `bash /app/backend/start-mittwald.sh` |
| Port | `8080/tcp` |
| CPU | 2 CPUs als Startwert |
| RAM | 4 GB als Startwert |

Der Startbefehl muss den Standardbefehl des Images ersetzen.
Falls das mStudio getrennte Felder für Befehl und Argumente anbietet, verwende
`bash` als Befehl und `/app/backend/start-mittwald.sh` als Argument.
Das Startskript hält generierte Assets außerhalb des schreibgeschützten Image-Dateisystems.

Lege zwei dauerhafte Volumes an und verbinde sie mit dem Container:

| Volume | Pfad im Container |
| --- | --- |
| `open-webui-data` | `/app/backend/data` |
| `open-webui-runtime` | `/tmp` |

Das Datenvolume enthält Accounts, Chats, Workspace-Inhalte und Uploads.
Das Runtime-Volume enthält generierte Assets und Laufzeit-Caches.
Behalte beide Zuordnungen bei jedem Update bei.

## Trage die Umgebungsvariablen ein

Verwende [container.env.example](container.env.example) als Vorlage für die
Umgebungsvariablen im mStudio. Ersetze vor dem ersten Start:

- `WEBUI_URL` und `CORS_ALLOW_ORIGIN` durch dieselbe HTTPS-URL ohne abschließenden Slash.
- `WEBUI_SECRET_KEY` durch einen dauerhaften zufälligen Schlüssel.
- `WEBUI_ADMIN_EMAIL` und `WEBUI_ADMIN_PASSWORD` durch deine Admin-Zugangsdaten.
- Die vier API-Key-Felder durch denselben mittwald-AI-Hosting-Key.

Erzeuge den dauerhaften Schlüssel mit:

```bash
openssl rand -hex 32
```

Trage die Werte direkt im mStudio ein. Die Vorlage enthält Platzhalter;
sie wird weder von GitHub hochgeladen noch automatisch in den Container importiert.
Hinterlege echte Zugangsdaten ausschließlich im mStudio.

Der API-Endpunkt ist `https://llm.aihosting.mittwald.de/v1`.
Prüfe, dass dein AI-Hosting-Zugang `Qwen3-Embedding-8B` für Dokument-Embeddings und
`whisper-large-v3-turbo` für Spracherkennung bereitstellt.

`ENABLE_PERSISTENT_CONFIG=false` macht die Container-Umgebungsvariablen für
allgemeine Einstellungen maßgeblich. So überschreibt keine ältere Provider-Konfiguration
in der Datenbank die mittwald-Anbindung. Ändere diese Einstellungen in den
Container-Umgebungsvariablen; Änderungen daran im Adminbereich werden nicht dauerhaft
übernommen. Accounts, Chats und Workspace-Inhalte bleiben gespeichert.

## Starte und prüfe die Anwendung

1. Starte den Container im mStudio.
2. Weise deine Subdomain dem Container auf Port `8080` zu und aktiviere HTTPS.
3. Öffne die URL aus `WEBUI_URL` und melde dich mit dem Admin-Account an.
4. Prüfe die Modellliste und sende einen Testchat.
5. Lade ein Testdokument hoch und stelle eine Frage zum Inhalt.

Der Admin wird nur angelegt, solange die Datenbank keine Nutzer enthält.
Eine spätere Änderung von `WEBUI_ADMIN_PASSWORD` setzt kein bestehendes Passwort zurück.
Öffentliche Registrierung bleibt ausgeschaltet. Lege Testnutzer im Adminbereich an.

## Lade eine neue Version manuell

1. Pushe deine Änderungen nach `main` und warte auf den erfolgreichen GitHub-Build.
2. Sichere das Datenvolume vor dem Update, vorzugsweise bei gestopptem Container.
3. Wähle im mStudio die Aktion zum erneuten Laden des Images und Neuerstellen des Containers.
4. Prüfe den Containerstatus und sende einen Testchat.

Ein gewöhnlicher Neustart lädt nicht zwingend ein neues Image. Die Aktion muss
`ghcr.io/tjorvez/open-webui:main` erneut aus der Registry ziehen.
Aktiviere keinen automatischen Update-Zeitplan für diesen Container.

Alternativ kannst du mit der mittwald-CLI manuell aktualisieren:

```bash
mw container recreate --pull CONTAINER_ID
```

Ersetze `CONTAINER_ID` durch die Kennung deines Containers und verwende den
CLI-Kontext deines Testprojekts. Für eine festgelegte Testversion kannst du im
mStudio das Image auf `ghcr.io/tjorvez/open-webui:git-<vollständige Commit-SHA>` setzen.
Ein erneutes Laden dieses Tags bleibt bei derselben Version.

Nach einer Datenbankmigration braucht ein Rollback das vorherige Image und die
passende Datensicherung. Lösche beim Update keine Volumes.

## Prüfe das Image lokal

Prüfe Shell-Syntax ohne Zugangsdaten:

```bash
bash -n backend/start-mittwald.sh deploy/mittwald/smoke-test.sh
```

Wenn Docker läuft, baue und prüfe das Image:

```bash
docker build --build-arg PRELOAD_MODELS=false -t open-webui-mittwald:test .
bash deploy/mittwald/smoke-test.sh open-webui-mittwald:test
```

GitHub führt denselben Starttest vor der Veröffentlichung durch.
Er verwendet Dummy-Zugangsdaten und ein isoliertes Netzwerk und prüft Backend-Start,
Migrationen, Admin-Anmeldung und Frontend-Auslieferung. Die echte mittwald-Verbindung
und die Domain prüfst du nach dem Anlegen des Containers.

## Quellen

- [mittwald Container anlegen, Registry und manuelle Updates](https://developer.mittwald.de/docs/v2/platform/workloads/containers/)
- [mittwald AI-API und Modelle](https://developer.mittwald.de/docs/v2/platform/aihosting/api-endpoints/supported-endpoints/)
