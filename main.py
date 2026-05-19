"""
Crucible Upload UI — Flask backend
"""
import logging
import queue
import re
import threading
import uuid
import webbrowser
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

import prefect_backend as backend
from instrument_conf import DEFAULT_BROWSE_DIR, IS_SESSION, DEFAULT_INSTRUMENT_NAME, PRINT_BARCODE_ENABLED, INSTRUMENTS, INSTRUMENT_FLOWS
from ai_services import voice_bp, extract_keywords

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(funcName)s: %(message)s")

app = Flask(__name__)
app.register_blueprint(voice_bp)

LOGS_DIR = Path(".upload_logs")
LOGS_DIR.mkdir(exist_ok=True)

_jobs: dict = {}
_jobs_lock = threading.Lock()


class _JobFilter(logging.Filter):
    """Only emits records whose calling thread is registered with this job_id."""
    def __init__(self, job_id: str):
        super().__init__()
        self.job_id = job_id

    def filter(self, record):
        return backend.get_current_job_id() == self.job_id


def _sanitize_for_filename(s: str) -> str:
    return (re.sub(r'[^a-zA-Z0-9._-]+', '_', s).strip('_') or 'session')[:80]


def _run_upload_job(job_id: str, flow_fn, params: dict, log_path: Path):
    backend.set_current_job_id(job_id)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    handler.addFilter(_JobFilter(job_id))
    target_loggers = [logging.getLogger('prefect_backend'), logging.getLogger('crucible')]
    for lg in target_loggers:
        lg.addHandler(handler)
    try:
        dsid = flow_fn(**params)
        with _jobs_lock:
            _jobs[job_id].update({'status': 'completed', 'dsid': dsid,
                                  'finished_at': datetime.now().isoformat()})
    except Exception as e:
        backend.logger.exception(f"Upload job {job_id} failed")
        with _jobs_lock:
            _jobs[job_id].update({'status': 'failed', 'error': str(e),
                                  'finished_at': datetime.now().isoformat()})
    finally:
        for lg in target_loggers:
            lg.removeHandler(handler)
        handler.close()

# Tkinter must run on the main thread. Flask runs in a background thread.
# We use two queues to hand off dialog requests/results between threads.
_tk_root = tk.Tk()
_tk_root.withdraw()
_tk_root.wm_attributes("-topmost", 1)

_browse_request: queue.Queue = queue.Queue()
_browse_result: queue.Queue = queue.Queue()


def _check_browse_queue():
    """Called repeatedly on the main thread via tkinter's event loop."""
    try:
        _browse_request.get_nowait()
        if IS_SESSION:
            kwargs = {"master": _tk_root, "title": "Select session folder"}
            if DEFAULT_BROWSE_DIR:
                kwargs["initialdir"] = DEFAULT_BROWSE_DIR
            path = filedialog.askdirectory(**kwargs)
        else:
            kwargs = {"master": _tk_root, "title": "Select file"}
            if DEFAULT_BROWSE_DIR:
                kwargs["initialdir"] = DEFAULT_BROWSE_DIR
            path = filedialog.askopenfilename(**kwargs)
        _browse_result.put(path or "")
    except queue.Empty:
        pass
    _tk_root.after(50, _check_browse_queue)


@app.get("/")
def index():
    return render_template("index.html", print_barcode_enabled=PRINT_BARCODE_ENABLED)


@app.get("/api/instruments")
def get_instruments():
    return jsonify({"instruments": INSTRUMENTS, "default": DEFAULT_INSTRUMENT_NAME})


@app.get("/api/browse")
def browse():
    # Signal the main thread to open the dialog, then wait for the result.
    _browse_request.put(True)
    path = _browse_result.get(timeout=60)
    return jsonify({"path": path})


@app.post("/api/user/lookup")
def user_lookup():
    email = (request.json or {}).get("email", "").strip()
    if not email:
        return jsonify({"error": "email required"}), 400
    try:
        result = backend.lookup_user_by_email(email)
        backend.logger.info(f"Lookup for email '{email}' returned: {result}")
    except Exception as e:
        backend.logger.error(e)
        return jsonify({"error": str(e)}), 500
    if not result:
        backend.logger.info(f"No user found for email '{email}'")
        return jsonify({"error": f"No user found for '{email}'"}), 404
    return jsonify(result)


@app.post("/api/sample/lookup")
def sample_lookup():
    data = request.json or {}
    sample_name = data.get("sample_name") or None
    sample_unique_id = data.get("sample_unique_id") or None
    project_id = data.get("project_id") or None
    if not sample_name and not sample_unique_id:
        return jsonify({"error": "sample_name or sample_unique_id required"}), 400
    try:
        result = backend.lookup_sample(
            sample_name=sample_name,
            sample_unique_id=sample_unique_id,
            project_id=project_id,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not result:
        return jsonify({"error": "No sample found"}), 404
    return jsonify(result)


@app.post("/api/sample/create")
def sample_create():
    data = request.json or {}
    sample_name = (data.get("sample_name") or "").strip()
    owner_orcid = (data.get("owner_orcid") or "").strip()
    project_id = (data.get("project_id") or "").strip()
    if not sample_name or not owner_orcid or not project_id:
        return jsonify({"error": "sample_name, owner_orcid, and project_id are required"}), 400
    try:
        result = backend.create_sample(
            sample_name=sample_name,
            owner_orcid=owner_orcid,
            project_id=project_id,
            description=data.get("description") or None,
            sample_type=data.get("sample_type") or None,
        )
    except Exception as e:
        backend.logger.error(e)
        return jsonify({"error": str(e)}), 500
    return jsonify(result)


@app.post("/api/sample/print-barcode")
def print_barcode():
    data = request.json or {}
    sample_unique_id = data.get("sample_unique_id", "").strip()
    sample_name = data.get("sample_name", "").strip()
    if not sample_unique_id:
        return jsonify({"error": "Missing sample_unique_id"}), 400
    try:
        backend.print_sample_barcode(sample_unique_id, sample_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@app.post("/api/session/check")
def session_check():
    data = request.json or {}
    required = ["orcid", "project_id", "instrument_name", "session_folder_path"]
    missing = [f for f in required if not (data.get(f) or "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    try:
        sessions = backend.check_existing_sessions(
            session_folder_path=data["session_folder_path"].strip(),
            orcid=data["orcid"].strip(),
            project_id=data["project_id"].strip(),
            instrument_name=data["instrument_name"].strip(),
        )
    except Exception as e:
        backend.logger.error(e)
        return jsonify({"error": str(e)}), 500
    return jsonify({"sessions": sessions})


@app.post("/api/upload")
def do_upload():
    data = request.json or {}
    required = ["orcid", "project_id", "instrument_name", "session_folder_path"]
    missing = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    orcid = data["orcid"].strip()
    project_id = data["project_id"].strip()
    instrument_name = data["instrument_name"].strip()
    sample_unique_id = data.get("sample_unique_id", None)
    session_dsid = data.get("session_dsid", None)
    session_folder_path = data["session_folder_path"].strip()
    comments = data.get("comments", "").strip()
    kw_list = data.get("keywords", []) or extract_keywords(comments, instrument_name)

    flow_fn = INSTRUMENT_FLOWS.get(instrument_name)
    if not flow_fn:
        return jsonify({"error": f"No upload flow configured for instrument '{instrument_name}'"}), 400

    job_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    session_basename = Path(session_folder_path).name or "session"
    log_filename = f"{timestamp}-{_sanitize_for_filename(session_basename)}-{job_id}.log"
    log_path = LOGS_DIR / log_filename

    params = {
        "file": session_folder_path,
        "instrument_name": instrument_name,
        "project_id": project_id,
        "orcid": orcid,
        "sample_unique_id": sample_unique_id,
        "session_dsid": session_dsid,
        "kw_list": kw_list,
        "comments": comments,
    }

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "running",
            "project_id": project_id,
            "session_folder_path": session_folder_path,
            "log_filename": log_filename,
            "started_at": datetime.now().isoformat(),
        }

    threading.Thread(
        target=_run_upload_job,
        args=(job_id, flow_fn, params, log_path),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id, "project_id": project_id, "log_filename": log_filename})


@app.get("/api/job/<job_id>")
def job_status(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@app.get("/logs/<path:filename>")
def serve_log(filename):
    if "/" in filename or ".." in filename:
        abort(400)
    return send_from_directory(LOGS_DIR.resolve(), filename, mimetype="text/plain")


if __name__ == "__main__":
    # Flask runs in a daemon thread; tkinter mainloop holds the main thread.
    flask_thread = threading.Thread(
        target=lambda: app.run(debug=False, port=5000), daemon=True
    )
    flask_thread.start()
    webbrowser.open("http://localhost:5000")
    _tk_root.after(50, _check_browse_queue)
    _tk_root.mainloop()
