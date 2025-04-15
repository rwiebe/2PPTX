# Flask Image Presentation
Dieses Projekt ermöglicht das Hochladen von Bildern und PDFs, deren Verarbeitung und die Erstellung einer PowerPoint-Präsentation.

Projekt Downloaden

```
cd /path/to/2PPTX

docker build -t pptx-converter-app .
docker run -p 9090:5000 --name mein-pptx-converter pptx-converter-app
```

Im Brower 127.0.0.1:9090 öffnen, Das Tool kann Bilder, PDFs in PPTX umwandeln und es kann auch ein Ordner darin enthaltene Bilder konvertieren.