"""Exercise the actual Gunicorn container, not Flask's test client."""
import io
import urllib.request
import uuid

import fitz
from PIL import Image
from pptx import Presentation

image = io.BytesIO()
Image.new("RGB", (800, 600), "orange").save(image, format="PNG")
with fitz.open() as document:
    document.new_page()
    pdf = document.tobytes()
boundary = uuid.uuid4().hex
body = bytearray()
for filename, content in (("image.png", image.getvalue()), ("page.pdf", pdf)):
    body.extend((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
        f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    ).encode())
    body.extend(content)
    body.extend(b"\r\n")
body.extend(f"--{boundary}--\r\n".encode())
request = urllib.request.Request("http://127.0.0.1:9090/upload", data=bytes(body),
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
with urllib.request.urlopen(request, timeout=120) as response:
    assert response.status == 200
    presentation = Presentation(io.BytesIO(response.read()))
    assert len(presentation.slides) == 2
print("HTTP image + PDF conversion passed")

# Unique noisy images defeat deduplication and exercise the media budget.
import random
import urllib.error

body = bytearray()
for index in range(8):
    stream = io.BytesIO()
    Image.frombytes("RGB", (1920, 1080),
                    random.Random(index).randbytes(1920 * 1080 * 3)).save(stream, "PNG")
    body.extend((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
        f"filename=\"{index}.png\"\r\nContent-Type: image/png\r\n\r\n"
    ).encode())
    body.extend(stream.getvalue())
    body.extend(b"\r\n")
body.extend(f"--{boundary}--\r\n".encode())
request = urllib.request.Request("http://127.0.0.1:9090/upload", data=bytes(body),
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
try:
    urllib.request.urlopen(request, timeout=120)
except urllib.error.HTTPError as error:
    assert error.code == 400
    assert "Speicherbudget" in error.read().decode()
else:
    raise AssertionError("Oversized media must be rejected")
with urllib.request.urlopen("http://127.0.0.1:9090/healthz", timeout=10) as response:
    assert response.status == 200
print("Media budget stress test passed; service remains responsive")
