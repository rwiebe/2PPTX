"""Linux conversion subprocess. Apply limits before importing native parsers."""
import json
import resource
import shutil
import sys
from pathlib import Path

MEMORY_BYTES = 320 * 1024 * 1024
OUTPUT_BYTES = 64 * 1024 * 1024
CPU_SECONDS = 60


def set_resource_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_BYTES, OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


class SavedUpload:
    def __init__(self, item):
        self.filename = item["filename"]
        self.path = item["path"]

    def save(self, destination):
        shutil.copyfile(self.path, destination)


def main():
    set_resource_limits()
    # Resource limits also apply to imports and native library initialization.
    from app import ConversionError, _convert_uploads, app

    manifest = json.loads(Path(sys.argv[1]).read_text())
    app.config.update(manifest["config"])
    try:
        count = _convert_uploads(
            [SavedUpload(item) for item in manifest["inputs"]],
            Path(manifest["workdir"]), Path(manifest["output"]),
        )
        result = {"slides": count}
    except ConversionError as exc:
        result = {"error": str(exc)}
    except MemoryError:
        result = {"error": "Die Konvertierung hat das Speicherlimit überschritten."}
    Path(manifest["result"]).write_text(json.dumps(result))


if __name__ == "__main__":
    main()
