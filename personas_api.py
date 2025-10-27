# personas_api.py
from flask import Blueprint, jsonify, request, abort
from pathlib import Path
import json

bp = Blueprint("personas", __name__)
PERSONA_DIR = Path("assistant_personalities")
PERSONA_DIR.mkdir(exist_ok=True)

def persona_path(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in ("_", "-"))
    return PERSONA_DIR / f"{safe}.json"


from flask import Flask, request, jsonify, render_template_string
import os, json

app = Flask(__name__)
PERSONA_DIR = "./assistant_personalities"


@bp.get("/personas/<name>")
def get_persona(name):
    p = persona_path(name)
    if not p.exists(): abort(404)
    data = json.loads(p.read_text(encoding="utf-8"))
    return jsonify(data)


@bp.put("/personas/<name>")
def save_persona(name):
    # Optional: simple auth/ACL check here
    try:
        data = request.get_json(force=True)
        # Optional: validate with a schema (see note below)
    except Exception as e:
        abort(400, f"Invalid JSON: {e}")
    p = persona_path(name)
    # Keep a quick backup
    if p.exists(): p.with_suffix(".json.bak").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


