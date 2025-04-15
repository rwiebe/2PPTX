# Dockerfile

# 1. Basisimage auswählen (Python 3.9 als Beispiel)
FROM python:3.9-slim

# 2. Systemabhängigkeiten installieren (PyMuPDF benötigt evtl. build tools)
#    Debian/Ubuntu basiert:
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Arbeitsverzeichnis im Container setzen
WORKDIR /app

# 4. requirements.txt kopieren und Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Restlichen Anwendungscode kopieren
COPY . .

# 6. Port freigeben, auf dem Flask läuft (muss mit app.run übereinstimmen)
EXPOSE 5000

# 7. Befehl zum Starten der Anwendung definieren
#    Verwendet Flask's eingebauten Server (gut für Entwicklung, für Produktion Gunicorn o.ä. erwägen)
#    Host 0.0.0.0 ist wichtig, damit die App von außerhalb des Containers erreichbar ist.
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]

# Alternativ für Produktion mit Gunicorn (müsste zu requirements.txt hinzugefügt werden):
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
