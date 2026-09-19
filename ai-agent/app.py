import os
from pathlib import Path

from fastapi import FastAPI


app = FastAPI(title="Zanimo Reference Tool")

REFERENCE_DIR = Path(os.getenv("REFERENCE_DIR", "/data/reference"))
MAX_CHARS = int(os.getenv("REFERENCE_MAX_CHARS", "30000"))


@app.get("/health")
def health():
    files = []

    if REFERENCE_DIR.exists():
        files = [p.name for p in sorted(REFERENCE_DIR.glob("*.txt"))]

    return {
        "ok": True,
        "service": "reference-tool",
        "reference_dir": str(REFERENCE_DIR),
        "txt_files_count": len(files),
        "txt_files": files,
        "max_chars": MAX_CHARS
    }


@app.get("/tools/prompt-references")
def prompt_references():
    if not REFERENCE_DIR.exists():
        return {
            "ok": False,
            "error": f"REFERENCE_DIR not found: {REFERENCE_DIR}",
            "references": ""
        }

    texts = []

    for file in sorted(REFERENCE_DIR.glob("*.txt")):
        try:
            content = file.read_text(encoding="utf-8", errors="ignore").strip()

            if content:
                texts.append(f"--- {file.name} ---\n{content}")

        except Exception as e:
            texts.append(f"--- {file.name} ---\nERROR READING FILE: {e}")

    references = "\n\n".join(texts)

    if len(references) > MAX_CHARS:
        references = references[:MAX_CHARS] + "\n\n[TRUNCATED]"

    if not references:
        return {
            "ok": False,
            "error": "No .txt reference files found or files are empty",
            "references": ""
        }

    return {
        "ok": True,
        "files_count": len(texts),
        "references": references
    }