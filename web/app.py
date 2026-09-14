"""
FastAPI Local Web Server for LeapGen Intern Daily Progress Studio.
Provides REST APIs for generating, editing, reviewing, and submitting daily progress updates.
"""

import datetime
import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from form_submitter import FormSubmitter
from gemini_generator import GeminiProgressGenerator, validate_and_normalize_hours
from catch_up import find_missing_weekdays, parse_date_str, ACCELERATOR_TOPICS
from credentials import (
    get_gemini_api_key,
    set_gemini_api_key,
    get_google_cookie,
    set_google_cookie,
    test_gemini_api_key,
    mask_secret,
)
from form_schema import STARTUP_OPTIONS, INTERN_NAMES

app = FastAPI(title="LeapGen Intern Progress Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_submitter() -> FormSubmitter:
    return FormSubmitter(history_file=BASE_DIR / "history.json", base_dir=BASE_DIR)


def load_config() -> Dict[str, Any]:
    cfg_file = BASE_DIR / "config.json"
    example_file = BASE_DIR / "config.example.json"
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            return json.load(f)
    if example_file.exists():
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            return cfg
        except Exception:
            pass
    return {}


def save_config(cfg: Dict[str, Any]):
    cfg_file = BASE_DIR / "config.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_context_notes() -> str:
    ctx_file = BASE_DIR / "context.txt"
    if ctx_file.exists():
        return ctx_file.read_text(encoding="utf-8")
    return ""


def save_context_notes(content: str):
    ctx_file = BASE_DIR / "context.txt"
    ctx_file.write_text(content, encoding="utf-8")


class GenerateRequest(BaseModel):
    date: str
    direction: Optional[str] = ""
    general_direction: Optional[str] = ""
    is_workshop: Optional[bool] = False
    workshop_topic: Optional[str] = None


class SubmitRequest(BaseModel):
    date: str
    update_data: Dict[str, Any]
    target: Optional[str] = None
    dry_run: Optional[bool] = False


class MarkAbsentRequest(BaseModel):
    date: str


class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]


class ContextUpdateRequest(BaseModel):
    context: str


class CredentialsUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    google_form_cookie: Optional[str] = None


class FullSetupRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    google_form_cookie: Optional[str] = None
    startup_name: Optional[str] = None
    intern_name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    context: Optional[str] = None


class TestKeyRequest(BaseModel):
    gemini_api_key: Optional[str] = None


@app.get("/")
def get_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Static index.html not found</h1>", status_code=404)


@app.get("/api/status")
def get_status():
    config = load_config()
    submitter = get_submitter()
    history = submitter.load_history()
    submissions = history.get("submissions", {})
    absent = set(config.get("absent_dates", []))

    missing = find_missing_weekdays(
        submissions=submissions,
        start_date="2026-07-24",
        end_date=datetime.date.today().strftime("%Y-%m-%d"),
        absent_dates=absent,
    )

    last_sub = history.get("last_submission", {})
    latest_date = None
    if submissions:
        latest_date = sorted(submissions.keys())[-1]

    key = get_gemini_api_key(BASE_DIR)
    cookie = get_google_cookie(BASE_DIR)

    return {
        "startup_name": config.get("startup_name", "Clovio"),
        "intern_name": config.get("intern_name", "Senith Sagarage"),
        "designation": config.get("designation", "Full Stack Developer"),
        "target": config.get("default_target", "official"),
        "total_submitted": len(submissions),
        "latest_submitted_date": latest_date,
        "missing_count": len(missing),
        "missing_dates": missing,
        "absent_dates": sorted(list(absent)),
        "today": datetime.date.today().strftime("%Y-%m-%d"),
        "has_gemini_key": bool(key),
        "has_cookie": bool(cookie),
    }


@app.get("/api/dates")
def get_dates():
    config = load_config()
    submitter = get_submitter()
    history = submitter.load_history()
    submissions = history.get("submissions", {})
    absent = set(config.get("absent_dates", []))

    start_dt = parse_date_str("2026-07-24")
    end_dt = datetime.date.today()

    all_days = []
    curr = start_dt
    while curr <= end_dt:
        if curr.weekday() < 5:  # Weekday
            d_str = curr.strftime("%Y-%m-%d")
            w_name = curr.strftime("%A")
            if d_str in submissions:
                status = "submitted"
            elif d_str in absent:
                status = "absent"
            else:
                status = "pending"

            all_days.append({
                "date": d_str,
                "weekday": w_name,
                "status": status,
                "has_data": d_str in submissions,
            })
        curr += datetime.timedelta(days=1)

    return {"days": all_days}


@app.get("/api/day-data/{date_str}")
def get_day_data(date_str: str):
    submitter = get_submitter()
    history = submitter.load_history()
    submissions = history.get("submissions", {})

    if date_str in submissions:
        return {"found": True, "source": "history", "data": submissions[date_str]}

    prev_tasks, recent_history = submitter.get_previous_tasks(before_date_str=date_str)
    return {
        "found": False,
        "source": "draft",
        "previous_tasks": prev_tasks,
        "recent_history": recent_history,
    }


@app.post("/api/generate")
def generate_update(req: GenerateRequest):
    config = load_config()
    submitter = get_submitter()
    context = load_context_notes()

    prev_tasks, recent_history = submitter.get_previous_tasks(before_date_str=req.date)

    effective_direction = ""
    if req.general_direction and req.direction:
        effective_direction = f"Phase: {req.general_direction}. Today's focus: {req.direction}"
    elif req.general_direction:
        effective_direction = req.general_direction
    elif req.direction:
        effective_direction = req.direction

    session_topic = None
    if req.is_workshop:
        session_topic = req.workshop_topic or "Insights to Startups - Digital Marketing & Growth"

    generator = GeminiProgressGenerator(
        base_dir=BASE_DIR,
        model=config.get("gemini_model", "gemini-3.6-flash"),
    )

    try:
        data = generator.generate_update(
            project_name=config.get("project_name", "Clovio"),
            context_notes=context,
            yesterday_submitted_tasks=prev_tasks,
            recent_history_context=recent_history,
            direction=effective_direction,
            today_date_str=req.date,
            leapgen_session=session_topic,
        )
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/submit")
def submit_update(req: SubmitRequest):
    config = load_config()
    submitter = get_submitter()
    target = req.target or config.get("default_target", "official")

    update_data = req.update_data
    if "task_items" in update_data:
        update_data["task_items"] = validate_and_normalize_hours(update_data["task_items"])

    res = submitter.submit(
        config=config,
        update_data=update_data,
        submission_date_str=req.date,
        target=target,
        dry_run=bool(req.dry_run),
    )
    return res


@app.post("/api/mark-absent")
def mark_absent(req: MarkAbsentRequest):
    config = load_config()
    absent = set(config.get("absent_dates", []))
    absent.add(req.date)
    config["absent_dates"] = sorted(list(absent))
    save_config(config)
    return {"success": True, "absent_dates": config["absent_dates"]}


@app.post("/api/unmark-absent")
def unmark_absent(req: MarkAbsentRequest):
    config = load_config()
    absent = set(config.get("absent_dates", []))
    if req.date in absent:
        absent.remove(req.date)
    config["absent_dates"] = sorted(list(absent))
    save_config(config)
    return {"success": True, "absent_dates": config["absent_dates"]}


@app.get("/api/history")
def get_history():
    submitter = get_submitter()
    return submitter.load_history()


@app.get("/api/context")
def get_context():
    return {"context": load_context_notes()}


@app.post("/api/context")
def update_context(req: ContextUpdateRequest):
    save_context_notes(req.context)
    return {"success": True}


@app.get("/api/config")
def get_config_endpoint():
    return load_config()


@app.post("/api/config")
def update_config_endpoint(req: ConfigUpdateRequest):
    save_config(req.config)
    return {"success": True, "config": req.config}


@app.post("/api/normalize-hours")
def normalize_hours_endpoint(task_items: List[Dict[str, Any]]):
    normalized = validate_and_normalize_hours(task_items)
    return {"task_items": normalized, "total": sum(float(t.get("time_spent", 0.0)) for t in normalized)}


@app.get("/api/credentials")
def get_credentials_endpoint():
    config = load_config()
    key = get_gemini_api_key(BASE_DIR)
    cookie = get_google_cookie(BASE_DIR)
    return {
        "has_gemini_key": bool(key),
        "gemini_key_masked": mask_secret(key),
        "has_cookie": bool(cookie),
        "cookie_masked": mask_secret(cookie, show_start=20, show_end=15),
        "startup_options": STARTUP_OPTIONS,
        "intern_names": INTERN_NAMES,
        "current_profile": {
            "startup_name": config.get("startup_name", "Clovio"),
            "intern_name": config.get("intern_name", "Senith Sagarage"),
            "designation": config.get("designation", "Full Stack Developer"),
            "email": config.get("email", ""),
        },
    }


@app.post("/api/credentials")
def save_credentials_endpoint(req: CredentialsUpdateRequest):
    if req.gemini_api_key is not None and req.gemini_api_key.strip():
        set_gemini_api_key(BASE_DIR, req.gemini_api_key.strip())
    if req.google_form_cookie is not None:
        set_google_cookie(BASE_DIR, req.google_form_cookie.strip())
    return {"success": True, "message": "Credentials updated successfully."}


@app.post("/api/test-gemini-key")
def test_gemini_key_endpoint(req: TestKeyRequest):
    key = req.gemini_api_key
    if not key or not key.strip():
        key = get_gemini_api_key(BASE_DIR)
    ok, msg = test_gemini_api_key(key)
    return {"success": ok, "message": msg}


@app.post("/api/setup")
def full_setup_endpoint(req: FullSetupRequest):
    if req.gemini_api_key and req.gemini_api_key.strip():
        set_gemini_api_key(BASE_DIR, req.gemini_api_key.strip())
    if req.google_form_cookie is not None and req.google_form_cookie.strip():
        set_google_cookie(BASE_DIR, req.google_form_cookie.strip())

    config = load_config()
    if req.startup_name:
        config["startup_name"] = req.startup_name
        config["project_name"] = req.startup_name
    if req.intern_name:
        config["intern_name"] = req.intern_name
    if req.designation:
        config["designation"] = req.designation
    if req.email:
        config["email"] = req.email
    save_config(config)

    if req.context is not None and req.context.strip():
        save_context_notes(req.context.strip())

    return {
        "success": True,
        "message": "Setup completed successfully! Profile and credentials saved.",
        "config": config,
    }


def run_server(port: int = 5000, open_browser: bool = True):
    url = f"http://127.0.0.1:{port}"
    print(f"\n============================================================")
    print(f"      LEAPGEN INTERN PROGRESS STUDIO - WEB GUI")
    print(f"============================================================")
    print(f"  Running locally at: {url}")
    print(f"  Press Ctrl+C to stop the server anytime.\n")

    if open_browser:
        def _open():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        import threading
        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    run_server()
