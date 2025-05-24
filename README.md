# 2PPTX – PDF-zu-PPTX-Konverter für WorshipTools Presenter

🧭 Motivation

WorshipTools Presenter unterstützt aktuell keine PDF-Dateien. Da wir jedoch häufig Präsentationen im PDF-Format erhalten, stellte das ein erhebliches Problem im Ablauf dar. Manuelles Konvertieren war unpraktisch und zeitaufwendig.

2PPTX wurde als Lösung für genau dieses Problem entwickelt. Das Tool wandelt PDF-Dateien automatisch in kompatible PowerPoint-Präsentationen (.pptx) um – optimiert für den Einsatz in Presenter.

✨ Funktionen
	•	🖤 Schwarzer Hintergrund jeder Folie (passend zur dunklen Oberfläche von Presenter und keine störendes weiß an der Leinwand)
	•	🖼️ Automatische Bildskalierung auf Full-HD-Auflösung (1920x1080)
	•	📁 Jede PDF-Seite wird zu einer PPTX-Folie
	•	🖥️ Webbasierte Benutzeroberfläche – keine Kommandozeile notwendig
	•	🐳 Docker-basiert – läuft containerisiert und isoliert

🚀 Nutzung

Das Tool startet einen lokalen Webserver, der über den Browser aufgerufen wird.

# 1. Container starten
```
   docker run -p 9090:5000 rwiebe/2pptx
```

# 2. Web-UI aufrufen

```
   localhsot:9090
```
# 3. PDF hochladen

Lade deine PDF-Datei hoch und erhalte eine fertige .pptx, optimiert für WorshipTools.

# 📦 Installation lokal (Alternativ zur Docker-Nutzung)

```
git clone https://github.com/rwiebe/2PPTX.git
cd 2PPTX
npm install
node server.js
```
Web-UI aufrufen

```
   localhsot:9090
```

# 📄 Lizenz

MIT-Lizenz – frei für private und kommerzielle Nutzung, Änderungen willkommen.

# 🤝 Beiträge willkommen

Wenn du Verbesserungen oder Fehler findest, freuen wir uns über Issues und Pull Requests. Dieses Projekt entstand aus einem realen Bedarf in der Gemeindetechnik – vielleicht hilft es auch dir!
