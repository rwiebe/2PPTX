# app.py
import io
import os
from flask import Flask, request, render_template, send_file, jsonify
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.dml.color import RGBColor
from PIL import Image, ImageOps # ImageOps für EXIF-Orientierung hinzufügen
import fitz  # PyMuPDF
import traceback # Für detaillierteres Error-Logging
import gc  # Garbage Collector

# --- Konstanten ---
SLIDE_WIDTH_EMU = 9144000 # 10 inches
SLIDE_HEIGHT_EMU = 5143500 # 5.625 inches
MAX_IMG_WIDTH_PX = 1920
MAX_IMG_HEIGHT_PX = 1080

# --- Flask App Initialisierung ---
app = Flask(__name__)
# Erhöhe das Limit für potenziell viele Dateien aus Ordnern
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # Max Upload 200 MB

# --- NEUE Hilfsfunktion: Bild verarbeiten (Größe, Orientierung) ---
def process_image_stream(image_stream):
    """
    Öffnet ein Bild aus einem Stream, korrigiert die Orientierung basierend auf EXIF,
    ändert die Größe, falls es 1920x1080 überschreitet (unter Beibehaltung des Seitenverhältnisses),
    und gibt einen neuen Stream mit dem verarbeiteten Bild (als PNG) zurück.
    """
    try:
        img = Image.open(image_stream)

        # 1. EXIF-Orientierung korrigieren
        #    ImageOps.exif_transpose liest EXIF und wendet Rotation/Spiegelung an
        img = ImageOps.exif_transpose(img)
        print(f"EXIF-Orientierung angewendet (falls vorhanden).")

        # 2. Größe ändern, wenn nötig
        current_width, current_height = img.size
        print(f"Originalgröße: {current_width}x{current_height}")

        if current_width > MAX_IMG_WIDTH_PX or current_height > MAX_IMG_HEIGHT_PX:
            # Seitenverhältnis beibehalten, auf Maximalgröße reduzieren
            # thumbnail ändert das Bild Objekt 'in-place'
            img.thumbnail((MAX_IMG_WIDTH_PX, MAX_IMG_HEIGHT_PX), Image.Resampling.LANCZOS)
            new_width, new_height = img.size
            print(f"Größe geändert auf: {new_width}x{new_height}")
        else:
            print("Keine Größenänderung erforderlich.")

        # 3. Verarbeitetes Bild in einen neuen Stream speichern (PNG für verlustfreie Zwischenspeicherung)
        output_stream = io.BytesIO()
        img.save(output_stream, format='PNG')
        output_stream.seek(0) # Wichtig: Stream zurücksetzen
        img.close() # Original PIL Image schließen
        return output_stream

    except Exception as e:
        print(f"Fehler beim Verarbeiten des Bild-Streams:")
        traceback.print_exc()
        # Im Fehlerfall versuchen, den Originalstream zurückzugeben (oder None)
        image_stream.seek(0) # Zurücksetzen für den Fall, dass es doch noch geht
        return image_stream # Oder return None und später darauf prüfen


# --- ANGEPASSTE Hilfsfunktion: Bild zentriert auf Folie hinzufügen ---
def add_image_centered(slide, image_stream):
    """Fügt ein Bild aus einem Stream zentriert auf einer Folie hinzu."""
    try:
        # Wichtig: Stream Position sicherstellen
        image_stream.seek(0)
        img = Image.open(image_stream)
        img_width_px, img_height_px = img.size
        # Hier img.close() weglassen, da der Stream weiter benötigt wird

        image_stream.seek(0) # Stream für add_picture zurücksetzen

        # Skalierungsfaktor für Folie berechnen
        scale_w = float(SLIDE_WIDTH_EMU) / img_width_px
        scale_h = float(SLIDE_HEIGHT_EMU) / img_height_px
        scale = min(scale_w, scale_h)

        pic_width_emu = int(img_width_px * scale)
        pic_height_emu = int(img_height_px * scale)
        left = int((SLIDE_WIDTH_EMU - pic_width_emu) / 2)
        top = int((SLIDE_HEIGHT_EMU - pic_height_emu) / 2)

        slide.shapes.add_picture(image_stream, left, top, width=pic_width_emu, height=pic_height_emu)
        print(f"Verarbeitetes Bild hinzugefügt: Pos=(L:{left}, T:{top}), Größe=(W:{pic_width_emu}, H:{pic_height_emu}), OrigPx=(W:{img_width_px}, H:{img_height_px})")

    except Exception as e:
        print(f"Fehler beim Hinzufügen des verarbeiteten Bildes zur Folie:")
        traceback.print_exc()
        # Fehler-Textbox als Fallback
        try:
            textbox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
            tf = textbox.text_frame
            tf.text = f"Fehler beim Laden/Platzieren eines Bildes:\n{e}"
            tf.paragraphs[0].font.color.rgb = RGBColor(255, 0, 0)
            tf.word_wrap = True
        except Exception:
            pass # Wenn selbst das fehlschlägt

# --- ANGEPASSTE Route: /upload ---
@app.route('/upload', methods=['POST'])
def upload_files():
    processed_image_streams = []
    try:
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({"error": "Keine Dateien ausgewählt"}), 400

        for file in files:
            try:
                filename = file.filename.lower()
                print(f"Verarbeite Datei: {file.filename}")
                original_stream = io.BytesIO()
                file.save(original_stream)
                original_stream.seek(0)

                if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')):
                    processed_stream = process_image_stream(original_stream)
                    if processed_stream:
                        processed_image_streams.append(processed_stream)
                
                elif filename.endswith('.pdf'):
                    pdf_document = fitz.open(stream=original_stream, filetype="pdf")
                    try:
                        for page_num in range(len(pdf_document)):
                            page = pdf_document.load_page(page_num)
                            pix = page.get_pixmap(dpi=150)
                            img_bytes = pix.tobytes("png")
                            pdf_page_stream = io.BytesIO(img_bytes)
                            processed_stream = process_image_stream(pdf_page_stream)
                            if processed_stream:
                                processed_image_streams.append(processed_stream)
                            pdf_page_stream.close()
                            del pix  # Explizit Pixmap freigeben
                    finally:
                        pdf_document.close()
                
                original_stream.close()
                gc.collect()  # Garbage Collection erzwingen
            
            except Exception as e:
                print(f"Fehler bei Datei {file.filename}: {str(e)}")
                continue

        if not processed_image_streams:
            return jsonify({"error": "Keine gültigen Bilder gefunden"}), 400

        # Präsentation erstellen
        pptx_io = create_presentation(processed_image_streams)
        
        # Aufräumen
        for stream in processed_image_streams:
            stream.close()
        processed_image_streams.clear()
        gc.collect()

        return send_file(
            pptx_io,
            as_attachment=True,
            download_name='presentation.pptx',
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )

    except Exception as e:
        # Aufräumen im Fehlerfall
        for stream in processed_image_streams:
            try:
                stream.close()
            except:
                pass
        processed_image_streams.clear()
        gc.collect()
        return jsonify({"error": f"Verarbeitungsfehler: {str(e)}"}), 500

# Neue Hilfsfunktion zum Erstellen der Präsentation
def create_presentation(image_streams):
    prs = Presentation()
    prs.slide_width = Emu(SLIDE_WIDTH_EMU)
    prs.slide_height = Emu(SLIDE_HEIGHT_EMU)

    for img_stream in image_streams:
        slide_layout = prs.slide_layouts[5]
        slide = prs.slides.add_slide(slide_layout)
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0, 0, 0)
        add_image_centered(slide, img_stream)

    pptx_io = io.BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    
    # Referenzen aufräumen
    del prs
    gc.collect()
    
    return pptx_io

# --- Rest des Codes (index Route, if __name__ == '__main__') bleibt gleich ---
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # app.run(debug=True, host='0.0.0.0', port=5000) # Für Debugging
    app.run(debug=False, host='0.0.0.0', port=5000)

