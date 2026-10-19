# 2PPTX

2PPTX wandelt PDFs und Bilddateien in PowerPoint-Präsentationen um. Jede
PDF-Seite beziehungsweise jedes Bild wird zu einer eigenen 16:9-Folie. Die
Ausgabe ist insbesondere für den Import in WorshipTools Presenter gedacht.

## Funktionen

- PDF, PNG, JPEG, GIF, BMP und TIFF als Eingabe
- Mehrere Dateien und vollständige Ordner per Drag-and-drop
- Eine Folie pro PDF-Seite oder Bild
- Proportionale Skalierung bis maximal 1920 × 1080 Pixel
- Schwarzer Hintergrund für abweichende Seitenverhältnisse
- Verarbeitung ausschließlich auf dem eigenen Server
- Verständliche Fehlermeldung statt unbemerkter Teilausgabe

## Schnellstart mit Docker

```bash
docker run --rm -p 9090:5000 rwiebe/2pptx
```

Danach ist die Oberfläche unter <http://localhost:9090> erreichbar.

Für einen lokalen Build:

```bash
docker build -t 2pptx:local .
docker run --rm -p 9090:5000 2pptx:local
```

Die mitgelieferte Compose-Konfiguration verwendet das externe Netzwerk
`nginx_proxy_net`. Falls es noch nicht existiert:

```bash
docker network create nginx_proxy_net
docker compose up --build
```

## Lokale Entwicklung

Vorausgesetzt wird Python 3.12 oder neuer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
flask --app app run
```

Die Entwicklungsoberfläche läuft anschließend unter <http://localhost:5000>.

Tests:

```bash
pytest
```

## Konfiguration

Die folgenden Umgebungsvariablen sind optional:

| Variable | Standard | Bedeutung |
| --- | ---: | --- |
| `PORT` | `9090` | Host-Port der Compose-Konfiguration |
| `TZ` | `Europe/Berlin` | Zeitzone des Containers |
| `MAX_UPLOAD_MB` | `100` | Maximale Gesamtgröße eines Uploads |
| `MAX_FILES` | `250` | Maximale Anzahl Dateien je Upload |
| `MAX_PDF_PAGES` | `250` | Maximale Seitenzahl pro PDF |
| `MAX_SLIDES` | `250` | Maximale Folienzahl der Ausgabe |
| `LOG_LEVEL` | `INFO` | Protokollierungsstufe der Anwendung |

Eine Vorlage liegt in `.env.example`. Persönliche `.env`-Dateien werden nicht
versioniert und nicht in das Container-Image kopiert.

## Betrieb

Der Container läuft als unprivilegierter Benutzer und verwendet Gunicorn mit
einem Worker und zwei Threads. Unter `/healthz` steht ein einfacher
Healthcheck zur Verfügung. Die Verarbeitung nutzt temporäre Dateien, damit
große Uploads nicht mehrfach vollständig im Arbeitsspeicher gehalten werden.

Für öffentlich erreichbare Installationen sollte zusätzlich ein Reverse Proxy
mit TLS und einem passenden Request-Limit vorgeschaltet werden.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

## Sicherheits- und Betriebsgrenzen

MAX_MEDIA_MB (Standard: 32) begrenzt die kumulativen aufbereiteten Bilddaten.
Es wird pro Prozess nur eine Konvertierung gleichzeitig angenommen; weitere
Anfragen erhalten HTTP 503 mit Retry-After. Deshalb bei einem Gunicorn-Worker
bleiben. Das Bilddatenbudget begrenzt eingebettete Medien. Die eigentliche Konvertierung
läuft zusätzlich in einem separaten Linux-Prozess mit maximal 320 MiB
Adressraum, 60 Sekunden CPU-Zeit, 90 Sekunden Gesamtlaufzeit und 64 MiB
Dateigröße. Ein Ressourcenlimit oder Parser-Absturz führt zu einer klaren
Fehlerantwort; der Webprozess bleibt davon getrennt. Der CI-Smoke-Test prüft eine normale Konvertierung und einen Upload
mit unterschiedlichen, detailreichen Full-HD-Bildern unter 512 MiB.

Compose veröffentlicht den Host-Port nur auf 127.0.0.1. Ein Reverse Proxy im
externen Netzwerk nginx_proxy_net erreicht app:5000 direkt. Für öffentlichen
Betrieb TLS, Zugriffsschutz und Request-/Rate-Limits am Proxy konfigurieren.
Ein unhealthy-Status allein löst keinen Docker-Neustart aus.

Der Workflow führt pytest, Syntaxchecks, pip-audit, einen Docker-Build,
Compose-Start, Healthcheck und reale HTTP-Konvertierungen aus. Die ursprünglichen
manuellen Angaben im PR ersetzen keinen grünen Lauf am aktuellen Commit.

Der Container-CVE-Scan mit Trivy zeigt alle Schweregrade einschließlich noch
nicht behobener CVEs; HIGH und CRITICAL lassen den Workflow fehlschlagen.
Die Konvertierungsgrenzen setzen Linux/POSIX resource-Limits voraus.
Der Speichergrenzwert gilt für den Konvertierungsprozess, nicht für den gesamten
Container; dessen zusätzliche 512-MiB-Grenze bleibt aktiv.


## Container-Basis

Das Laufzeit-Image verwendet Wolfi mit Python 3.12, libstdc++ und Zeitzonendaten
anstelle von Debian Slim. Die Python-Abhängigkeiten werden in einer separaten
Build-Stufe installiert; ins finale Image kommen nur die virtuelle Umgebung,
Anwendung und Webdateien. Anwendung und Bibliotheken sind für den Benutzer app
nicht schreibbar. Die APK-Paketdatenbank bleibt für vollständige CVE-Scans erhalten.
Der Build benötigt Zugriff auf cgr.dev, packages.wolfi.dev und PyPI. Das Image
verwendet weiterhin glibc und die bisherigen manylinux-Wheels; Python bleibt 3.12.

Pip und ensurepip samt Bootstrap-Wheels werden nach dem Build aus dem finalen
Image entfernt. Laufende Container installieren keine weiteren Python-Pakete;
Änderungen an Abhängigkeiten erfolgen ausschließlich durch einen neuen Build.
Die Betriebssystem-Paketdatenbank wird dabei nicht entfernt oder verändert.
