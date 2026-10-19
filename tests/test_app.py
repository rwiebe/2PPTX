import io

import fitz
from PIL import Image
from pptx import Presentation

from app import app


def make_image(size=(800, 600), color=(230, 100, 30), image_format="PNG"):
    stream = io.BytesIO()
    Image.new("RGB", size, color).save(stream, format=image_format)
    stream.seek(0)
    return stream


def make_pdf(page_count=2):
    document = fitz.open()
    for page_number in range(page_count):
        page = document.new_page(width=842, height=595)
        page.insert_text((72, 72), f"Testseite {page_number + 1}")
    stream = io.BytesIO(document.tobytes())
    document.close()
    stream.seek(0)
    return stream


def test_health_endpoint():
    with app.test_client() as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_image_and_pdf_create_one_slide_per_page():
    with app.test_client() as client:
        response = client.post(
            "/upload",
            data={
                "files": [
                    (make_image(), "bild.png"),
                    (make_pdf(page_count=2), "folien.pdf"),
                ]
            },
            content_type="multipart/form-data",
        )
        presentation_bytes = response.get_data()
        response.close()

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    presentation = Presentation(io.BytesIO(presentation_bytes))
    assert len(presentation.slides) == 3
    assert all(len(slide.shapes) == 1 for slide in presentation.slides)


def test_portrait_image_is_centered_without_distortion():
    with app.test_client() as client:
        response = client.post(
            "/upload",
            data={"files": (make_image(size=(600, 900)), "portrait.jpg")},
            content_type="multipart/form-data",
        )
        presentation_bytes = response.get_data()
        response.close()

    presentation = Presentation(io.BytesIO(presentation_bytes))
    picture = presentation.slides[0].shapes[0]
    assert picture.height == presentation.slide_height
    assert picture.width < presentation.slide_width
    assert picture.left == (presentation.slide_width - picture.width) // 2


def test_broken_image_returns_clear_error_instead_of_partial_pptx():
    with app.test_client() as client:
        response = client.post(
            "/upload",
            data={"files": (io.BytesIO(b"not an image"), "defekt.png")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert "defekt.png" in response.get_json()["error"]


def test_unsupported_extension_is_rejected():
    with app.test_client() as client:
        response = client.post(
            "/upload",
            data={"files": (io.BytesIO(b"text"), "notizen.txt")},
            content_type="multipart/form-data",
        )

    assert response.status_code == 400
    assert "nicht unterstützten Dateityp" in response.get_json()["error"]


def test_pdf_page_limit_is_enforced():
    previous_limit = app.config["MAX_PDF_PAGES"]
    app.config["MAX_PDF_PAGES"] = 1
    try:
        with app.test_client() as client:
            response = client.post(
                "/upload",
                data={"files": (make_pdf(page_count=2), "zu-viele-seiten.pdf")},
                content_type="multipart/form-data",
            )
    finally:
        app.config["MAX_PDF_PAGES"] = previous_limit

    assert response.status_code == 400
    assert "höchstens 1 Seite" in response.get_json()["error"]


def test_total_slide_limit_is_enforced_across_files():
    previous_limit = app.config["MAX_SLIDES"]
    app.config["MAX_SLIDES"] = 1
    try:
        with app.test_client() as client:
            response = client.post(
                "/upload",
                data={
                    "files": [
                        (make_image(), "eins.png"),
                        (make_image(), "zwei.png"),
                    ]
                },
                content_type="multipart/form-data",
            )
    finally:
        app.config["MAX_SLIDES"] = previous_limit

    assert response.status_code == 400
    assert "höchstens 1 Folie" in response.get_json()["error"]


def test_media_budget_rejects_output(monkeypatch):
    monkeypatch.setitem(app.config, "MAX_MEDIA_BYTES", 1)
    with app.test_client() as client:
        response = client.post("/upload", data={"files": (make_image(), "image.png")})
        assert response.status_code == 400
        assert "Speicherbudget" in response.json["error"]


def test_concurrent_conversion_is_rejected():
    from app import conversion_slot
    with conversion_slot:
        with app.test_client() as client:
            response = client.post("/upload")
            assert response.status_code == 503
            assert response.headers["Retry-After"] == "5"


def test_upload_limit(monkeypatch):
    monkeypatch.setitem(app.config, "MAX_CONTENT_LENGTH", 32)
    with app.test_client() as client:
        response = client.post("/upload", data={"files": (make_image(), "image.png")})
        assert response.status_code == 413
        assert "error" in response.json


def test_file_limit(monkeypatch):
    monkeypatch.setitem(app.config, "MAX_FILES", 1)
    with app.test_client() as client:
        response = client.post("/upload", data={"files": [
            (make_image(), "one.png"), (make_image(), "two.png")]})
        assert response.status_code == 400


def test_valid_then_broken_file_is_not_partial_success():
    with app.test_client() as client:
        response = client.post("/upload", data={"files": [
            (make_image(), "one.png"), (io.BytesIO(b"broken"), "two.png")]})
        assert response.status_code == 400
        assert response.is_json


def test_output_cleanup_after_download_and_abort(tmp_path, monkeypatch):
    import app as module
    original = module.tempfile.NamedTemporaryFile
    monkeypatch.setattr(module.tempfile, "NamedTemporaryFile",
                        lambda **kwargs: original(dir=tmp_path, **kwargs))
    for consume in (True, False):
        with app.test_client() as client:
            response = client.post("/upload", data={"files": (make_image(), "image.png")},
                                   buffered=False)
            assert response.status_code == 200
            assert list(tmp_path.glob("*.pptx"))
            if consume:
                response.get_data()
            response.close()
            assert not list(tmp_path.glob("*.pptx"))


def test_large_image_is_downscaled():
    with app.test_client() as client:
        response = client.post("/upload", data={
            "files": (make_image(size=(3840, 2160)), "large.png")})
        presentation = Presentation(io.BytesIO(response.get_data()))
        response.close()
    with Image.open(io.BytesIO(presentation.slides[0].shapes[0].image.blob)) as image:
        assert image.size == (1920, 1080)


def test_broken_and_encrypted_pdf():
    document = fitz.open()
    document.new_page()
    encrypted = document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,
                                owner_pw="owner", user_pw="secret")
    document.close()
    for data in (b"not a PDF", encrypted):
        with app.test_client() as client:
            response = client.post("/upload", data={"files": (io.BytesIO(data), "bad.pdf")})
            assert response.status_code == 400


def test_pixel_bomb_is_rejected():
    with app.test_client() as client:
        response = client.post("/upload", data={"files": (make_image(size=(5001, 5000)), "bomb.png")})
        assert response.status_code == 400


def test_timeout_leaves_web_service_usable(monkeypatch):
    monkeypatch.setitem(app.config, "CONVERSION_TIMEOUT", 0.001)
    with app.test_client() as client:
        response = client.post("/upload", data={"files": (make_image(), "image.png")})
        assert response.status_code == 400
        assert "Zeitlimit" in response.json["error"]
        assert client.get("/healthz").status_code == 200
        monkeypatch.setitem(app.config, "CONVERSION_TIMEOUT", 90)
        response = client.post("/upload", data={"files": (make_image(), "image.png")})
        assert response.status_code == 200
        response.close()


def test_native_worker_crash_is_clean_error(monkeypatch):
    import app as module
    import subprocess
    original = subprocess.run

    def crash(command, **kwargs):
        return original([command[0], "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
                        **kwargs)
    monkeypatch.setattr(module.subprocess, "run", crash)
    with app.test_client() as client:
        response = client.post("/upload", data={"files": (make_image(), "image.png")})
        assert response.status_code == 400
        assert "Ressourcenlimits" in response.json["error"]
        assert client.get("/healthz").status_code == 200


def test_worker_memory_limit_is_enforced_by_os():
    import subprocess
    import sys
    code = """from conversion_worker import set_resource_limits
set_resource_limits()
try:
    allocation = bytearray(400 * 1024 * 1024)
except MemoryError:
    print('limited')
else:
    raise SystemExit('memory limit not enforced')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, timeout=10, check=True)
    assert result.stdout.strip() == "limited"
