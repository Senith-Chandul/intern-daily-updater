"""
LeapGen Intern Progress Update CLI.
Generates plausible, professional daily reports with Gemini API,
offers an interactive review screen, and submits to Google Forms.
Supports custom submission dates, switching between Official and Test Forms,
and dynamic schema auto-extraction from any Google Form URL.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from form_schema import STARTUP_OPTIONS, INTERN_NAMES
from form_submitter import FormSubmitter
from form_extractor import extract_schema_from_url
from gemini_generator import GeminiProgressGenerator
from catch_up import run_catch_up, find_missing_weekdays
from credentials import (
    get_gemini_api_key,
    get_google_cookie,
    interactive_cli_setup,
    set_cookie_in_env,
    set_google_cookie,
    set_gemini_api_key,
    test_gemini_api_key,
    mask_secret,
)
from email_importer import cli_import_confirmation_emails, import_confirmation_emails

BASE_DIR = Path(__file__).parent


def load_config() -> Dict[str, Any]:
    config_path = BASE_DIR / "config.json"
    example_path = BASE_DIR / "config.example.json"
    if not config_path.exists():
        if example_path.exists():
            try:
                with open(example_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                return cfg
            except Exception:
                pass
        return {
            "startup_name": "Clovio",
            "intern_name": "Senith Sagarage",
            "designation": "Full Stack Developer",
            "email": "senith.20231705@iit.ac.lk",
            "project_name": "Clovio",
            "gemini_model": "gemini-3.6-flash",
            "active_target": "test",
            "test_form_url": "https://docs.google.com/forms/d/e/1FAIpQLSc9v7B37abD5zX8jzlM91ch4i83H7-mDDiCYZ6qqwoe06UxNQ/viewform",
            "official_form_url": "https://docs.google.com/forms/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/viewform",
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: Dict[str, Any]):
    config_path = BASE_DIR / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_context() -> str:
    context_path = BASE_DIR / "context.txt"
    if context_path.exists():
        with open(context_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def display_preview(config: Dict[str, Any], update_data: Dict[str, Any], submission_date: str, target_name: str, leapgen_session: Optional[str] = None):
    is_today = submission_date == datetime.date.today().strftime("%Y-%m-%d")
    date_label = f"{submission_date} (Today)" if is_today else f"{submission_date} (Backfill / Past Date)"
    session_label = f"Yes ({leapgen_session})" if leapgen_session and leapgen_session != "default" else ("Yes (3-hr Accelerator Workshop)" if leapgen_session else "No (Regular Workday)")

    print("\n" + "=" * 70)
    print("           LEAPGEN DAILY INTERN UPDATE: REVIEW & CONFIRMATION")
    print("=" * 70)
    print(f"Target Form:   {target_name}")
    print(f"Startup:       {config.get('startup_name')}")
    print(f"Intern Name:   {config.get('intern_name')}")
    print(f"Designation:   {config.get('designation')}")
    print(f"Email:         {config.get('email')}")
    print(f"Report Date:   {date_label}")
    print(f"LeapGen Sess:  {session_label}")
    print("-" * 70)
    print("TASKS I DID YESTERDAY:")
    print(update_data.get("tasks_yesterday", "").strip())
    print("-" * 70)
    print("TASKS I DID TODAY:")
    print(update_data.get("tasks_today", "").strip())
    print("-" * 70)
    print("TASK BREAKDOWN & METRICS:")

    task_items = update_data.get("task_items", [])
    total_hours = sum(float(item.get("time_spent", 0.0)) for item in task_items)
    for i, item in enumerate(task_items, 1):
        print(
            f"  Task {i}: {item.get('title', '')}\n"
            f"          Status: {item.get('status')} | Continuation: {item.get('continuation')} | "
            f"Hours: {item.get('time_spent')}h | Target Date: {item.get('completion_date')}"
        )
    print(f"\n  >> Total Hours Today: {total_hours:.1f} hrs (Allowed range: 6.0 - 9.0 hrs)")
    print("-" * 70)
    print(f"PROBLEMS / CHALLENGES FACED:\n{update_data.get('challenges', 'None')}")
    print("=" * 70 + "\n")


def interactive_edit(update_data: Dict[str, Any]) -> Dict[str, Any]:
    print("\nSelect field to edit:")
    print("1. Tasks I did yesterday")
    print("2. Tasks I did today")
    print("3. Challenges faced")
    print("4. Back to main review")
    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        print("Enter new 'Tasks I did yesterday' (paste text, enter an empty line to finish):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        if lines:
            update_data["tasks_yesterday"] = "\n".join(lines)

    elif choice == "2":
        print("Enter new 'Tasks I did today' (paste text, enter an empty line to finish):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        if lines:
            update_data["tasks_today"] = "\n".join(lines)

    elif choice == "3":
        new_val = input("Enter new challenges: ").strip()
        if new_val:
            update_data["challenges"] = new_val

    return update_data


def interactive_setup():
    print("\n--- Profile Setup ---")
    config = load_config()

    print("\nAvailable Startups:")
    for idx, name in enumerate(STARTUP_OPTIONS, 1):
        print(f"  {idx}. {name}")
    s_choice = input(f"Choose startup (1-{len(STARTUP_OPTIONS)}) [current: {config.get('startup_name')}]: ").strip()
    if s_choice.isdigit() and 1 <= int(s_choice) <= len(STARTUP_OPTIONS):
        config["startup_name"] = STARTUP_OPTIONS[int(s_choice) - 1]

    print("\nAvailable Intern Names:")
    for idx, name in enumerate(INTERN_NAMES, 1):
        print(f"  {idx}. {name}")
    n_choice = input(f"Choose intern name (1-{len(INTERN_NAMES)}) [current: {config.get('intern_name')}]: ").strip()
    if n_choice.isdigit() and 1 <= int(n_choice) <= len(INTERN_NAMES):
        config["intern_name"] = INTERN_NAMES[int(n_choice) - 1]

    desig = input(f"Enter Designation [current: {config.get('designation')}]: ").strip()
    if desig:
        config["designation"] = desig

    email = input(f"Enter Email [current: {config.get('email')}]: ").strip()
    if email:
        config["email"] = email

    save_config(config)
    print("\nConfig saved successfully to config.json!\n")


def list_history():
    submitter = FormSubmitter(history_file=BASE_DIR / "history.json", base_dir=BASE_DIR)
    history = submitter.load_history()
    submissions = history.get("submissions", {})

    print("\n" + "=" * 70)
    print("                    RECORDED SUBMISSION HISTORY")
    print("=" * 70)
    if not submissions:
        print("No past submissions recorded yet in history.json.")
    else:
        for d in sorted(submissions.keys()):
            sub = submissions[d]
            print(f"\n[Date: {d}]")
            print("Today's Tasks:")
            for line in sub.get("tasks_today", "").strip().splitlines():
                print(f"   {line}")
            if sub.get("challenges") and sub.get("challenges") != "None":
                print(f"Challenges: {sub.get('challenges')}")
    print("\n" + "=" * 70 + "\n")


def add_past_history():
    print("\n--- Add Past Submission to History ---")
    print("Use this to record a past update you already submitted manually.")
    date_str = input("Enter date of past submission (YYYY-MM-DD): ").strip()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("[Error] Invalid date format. Please use YYYY-MM-DD (e.g. 2026-09-05).")
        return

    print("Enter 'Tasks I did yesterday' (paste text, enter an empty line to finish):")
    lines_y = []
    while True:
        line = input()
        if not line:
            break
        lines_y.append(line)
    tasks_yesterday = "\n".join(lines_y)

    print("Enter 'Tasks I did today' (paste text, enter an empty line to finish):")
    lines_t = []
    while True:
        line = input()
        if not line:
            break
        lines_t.append(line)
    tasks_today = "\n".join(lines_t)

    challenges = input("Challenges faced [default: None]: ").strip() or "None"

    submitter = FormSubmitter(history_file=BASE_DIR / "history.json", base_dir=BASE_DIR)
    update_data = {
        "tasks_yesterday": tasks_yesterday,
        "tasks_today": tasks_today,
        "task_items": [],
        "challenges": challenges,
    }
    submitter.record_history(update_data, submission_date_str=date_str)
    print(f"\n[Success] Recorded update for {date_str} in history.json!")
    print("Gemini will now use this past data to maintain continuity for subsequent days.\n")


def auto_extract_and_set_form(url: str):
    """Fetch form from URL, extract schema, save to test_form_schema.json, and update config."""
    print(f"\nExtracting schema from: {url}")
    try:
        schema = extract_schema_from_url(url)
        test_schema_file = BASE_DIR / "test_form_schema.json"
        with open(test_schema_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)

        config = load_config()
        config["test_form_url"] = url.split("?")[0]
        config["active_target"] = "test"
        save_config(config)

        print(f"[Success] Extracted schema for: '{schema.get('title')}'")
        print(f"[Success] Saved schema to {test_schema_file.name} and set active_target = 'test' in config.json!\n")
    except Exception as e:
        print(f"[Error] Failed to extract form schema: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="LeapGen Daily Intern Progress Update Generator")
    parser.add_argument("--date", "-t", type=str, default="", help="Submission date in YYYY-MM-DD (supports backfilling past days)")
    parser.add_argument("--direction", "-d", type=str, default="", help="Direction or focus for today's tasks")
    parser.add_argument("--session", "-s", nargs="?", const="default", default=None, help="Indicate if a 3-hour LeapGen session took place (optional topic, e.g. --session 'pitch preparation' or just --session)")
    parser.add_argument("--catch-up", "-c", action="store_true", help="Batch catch-up mode to backfill all missing weekdays")
    parser.add_argument("--from-date", type=str, default="", help="Start date for catch-up (YYYY-MM-DD)")
    parser.add_argument("--to-date", type=str, default="", help="End date for catch-up (YYYY-MM-DD)")
    parser.add_argument("--absent", type=str, action="append", default=[], help="Comma-separated absent dates to skip (e.g. --absent 2026-08-05,2026-08-14)")
    parser.add_argument("--set-cookie", type=str, default="", help="Save your Google session Cookie header to authorize official form submissions")
    parser.add_argument("--target", choices=["test", "official"], default=None, help="Target form (test or official)")
    parser.add_argument("--set-test-url", type=str, default="", help="Extract and set a new test Google Form URL")
    parser.add_argument("--dry-run", action="store_true", help="Generate and review without submitting to Google Form")
    parser.add_argument("--auto", action="store_true", help="Automatically submit without review prompt")
    parser.add_argument("--setup", action="store_true", help="Run interactive profile setup")
    parser.add_argument("--add-history", action="store_true", help="Manually add a past day's submission into history.json")
    parser.add_argument("--list-history", action="store_true", help="List all past recorded submissions in history.json")
    parser.add_argument("--import-email", nargs="?", const="interactive", default=None, help="Import past updates from confirmation email(s) (file path or paste interactively)")
    parser.add_argument("--gui", "-g", action="store_true", help="Launch the local Web GUI Studio")
    parser.add_argument("--port", type=int, default=5000, help="Port for the Web GUI (default: 5000)")
    args = parser.parse_args()

    if args.gui:
        try:
            from web.app import run_server
        except ImportError:
            from intern_daily_updater.web.app import run_server
        run_server(port=args.port, open_browser=True)
        return

    if args.set_cookie:
        set_cookie_in_env(args.set_cookie)
        return

    if args.set_test_url:
        auto_extract_and_set_form(args.set_test_url)
        return

    if args.setup:
        config = load_config()
        interactive_cli_setup(BASE_DIR, config, force=True)
        return

    if args.import_email:
        config = load_config()
        if args.import_email != "interactive" and Path(args.import_email).exists():
            file_text = Path(args.import_email).read_text(encoding="utf-8")
            try:
                res = import_confirmation_emails(file_text, base_dir=BASE_DIR, model=config.get("gemini_model", "gemini-flash-latest"))
                print(f"\n[Success] {res.get('message')}")
                print(f"Profile: {res.get('profile')}")
                print(f"Dates: {res.get('imported_dates')}\n")
            except Exception as e:
                print(f"\n[Error] Import failed: {e}\n")
        else:
            cli_import_confirmation_emails(BASE_DIR, config)
        return

    if args.list_history:
        list_history()
        return

    if args.add_history:
        add_past_history()
        return

    config = load_config()
    context = load_context()
    submitter = FormSubmitter(history_file=BASE_DIR / "history.json", base_dir=BASE_DIR)

    api_key = get_gemini_api_key(BASE_DIR)
    if not api_key:
        config = interactive_cli_setup(BASE_DIR, config)
        api_key = get_gemini_api_key(BASE_DIR)
        if not api_key:
            print("\n[Error] Cannot proceed without a valid Gemini API key. Exiting.\n")
            sys.exit(1)

    active_target = args.target or config.get("active_target", "official")

    if active_target == "official" and not args.dry_run:
        cookie = get_google_cookie(BASE_DIR)
        if not cookie:
            print("\n" + "=" * 70)
            print("        GOOGLE FORM SESSION COOKIE REQUIRED FOR OFFICIAL FORM")
            print("=" * 70)
            print("The official LeapGen form requires your @iit.ac.lk Google authentication.")
            print("To get your cookie:")
            print("  1. Open Chrome/Edge and go to the LeapGen Google Form (logged into @iit.ac.lk).")
            print("  2. Press F12 -> Network tab -> refresh the page.")
            print("  3. Click 'viewform' -> in Request Headers, copy 'Cookie:' value.")
            cookie_input = input("\nPaste your Google Form Cookie (or press Enter to skip for now): ").strip()
            if cookie_input:
                set_google_cookie(BASE_DIR, cookie_input)

    resolved_schema = submitter.resolve_form_schema(config, target=active_target)
    target_display = f"[{active_target.upper()}] {resolved_schema.get('title')}"

    if args.catch_up:
        run_catch_up(
            config=config,
            context=context,
            target=active_target,
            start_date=args.from_date or None,
            end_date=args.to_date or None,
            absent_dates_input=args.absent,
            auto_pilot=args.auto,
            dry_run=args.dry_run,
        )
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    sub_date = args.date.strip()

    if not sub_date and not args.auto:
        print("\n=== LeapGen Daily Intern Update Tool ===")
        print(f"Active Submission Target: {target_display}")

        missing_weekdays = find_missing_weekdays(submitter.load_history().get("submissions", {}))
        if len(missing_weekdays) > 1:
            print(f"[Notice] You have {len(missing_weekdays)} unsubmitted weekday(s) since July 24!")
            print("  [1] Single date update (default today)")
            print("  [2] Batch Catch-Up (terminal stepper)")
            print("  [3] Launch Web GUI Studio (Recommended)")
            print("  [4] Import past updates from Confirmation Email(s)")
            mode_choice = input("Select mode [1/2/3/4, default 3]: ").strip()
            if mode_choice in ["3", "g", "gui", ""]:
                try:
                    from web.app import run_server
                except ImportError:
                    from intern_daily_updater.web.app import run_server
                run_server(port=args.port, open_browser=True)
                return
            elif mode_choice == "2":
                run_catch_up(
                    config=config,
                    context=context,
                    target=active_target,
                    start_date=args.from_date or None,
                    end_date=args.to_date or None,
                    absent_dates_input=args.absent,
                    auto_pilot=args.auto,
                    dry_run=args.dry_run,
                )
                return
            elif mode_choice in ["4", "import", "email"]:
                cli_import_confirmation_emails(BASE_DIR, config)
                config = load_config()
                missing_weekdays = find_missing_weekdays(submitter.load_history().get("submissions", {}))
                print(f"[Notice] You now have {len(missing_weekdays)} unsubmitted weekday(s).\n")

        date_input = input(f"Submission Date [default today: {today_str}]: ").strip()
        sub_date = date_input if date_input else today_str
    elif not sub_date:
        sub_date = today_str

    try:
        datetime.datetime.strptime(sub_date, "%Y-%m-%d")
    except ValueError:
        print(f"[Error] Invalid date format: '{sub_date}'. Please use YYYY-MM-DD.")
        sys.exit(1)

    # Load past tasks and chronological history strictly before the target date
    prev_tasks, recent_history = submitter.get_previous_tasks(before_date_str=sub_date)
    if prev_tasks:
        print(f"[Info] Found previous work before {sub_date}. Carrying over into yesterday's tasks.")
    if recent_history:
        print(f"[Info] Loaded {len(recent_history)} past submission(s) into Gemini context for continuity.")

    direction = args.direction
    if not direction and not args.auto:
        direction_input = input("Enter direction/focus for this update (or press Enter for automatic generation): ").strip()
        direction = direction_input

    leapgen_session = args.session
    if leapgen_session is None and not args.auto:
        sess_input = input("Was there a 3-hour LeapGen session/workshop today? (y/N or enter topic) [default: N]: ").strip()
        if sess_input:
            if sess_input.lower() in ["n", "no"]:
                leapgen_session = None
            elif sess_input.lower() in ["y", "yes"]:
                leapgen_session = "default"
            else:
                leapgen_session = sess_input

    generator = GeminiProgressGenerator(base_dir=BASE_DIR, model=config.get("gemini_model", "gemini-3.6-flash"))

    print(f"\nGenerating plausible progress update for {sub_date} with Gemini API...")
    try:
        update_data = generator.generate_update(
            project_name=config.get("project_name", "Clovio"),
            context_notes=context,
            yesterday_submitted_tasks=prev_tasks,
            recent_history_context=recent_history,
            direction=direction,
            today_date_str=sub_date,
            leapgen_session=leapgen_session,
        )
    except Exception as e:
        print(f"\n[Error] {e}")
        sys.exit(1)

    # Review Loop
    while True:
        display_preview(config, update_data, submission_date=sub_date, target_name=target_display, leapgen_session=leapgen_session)

        if args.auto:
            action = "s"
        else:
            print("Options:")
            print(f"  [S] Submit to {target_display}")
            print("  [R] Regenerate (provide new or modified direction / session)")
            print("  [E] Edit field manually")
            print("  [Q] Quit without submitting")
            action = input("\nChoose an option [S/R/E/Q]: ").strip().lower()

        if action == "s":
            while True:
                print(f"\nSubmitting to {target_display} for date {sub_date}...")
                res = submitter.submit(
                    config,
                    update_data,
                    submission_date_str=sub_date,
                    target=active_target,
                    dry_run=args.dry_run
                )
                if res.get("success"):
                    if res.get("dry_run"):
                        print(f"\n[DRY RUN SUCCESS] {res.get('message')}")
                    else:
                        print(f"\n[SUCCESS] {res.get('message')}")
                        print(f"Recorded update for {sub_date} in history.json!")
                    break
                else:
                    print(f"\n[FAILED] {res.get('message')}")
                    if res.get("status_code"):
                        print(f"HTTP Status: {res.get('status_code')}")
                    msg_str = str(res.get("message", "")).lower()
                    if "401" in msg_str or "cookie" in msg_str or "auth" in msg_str:
                        print("\n[Auth Required] Your Google Form session cookie is missing or has expired.")
                        print("Open Chrome/Edge (logged into @iit.ac.lk) -> F12 -> Network -> copy 'Cookie:' from viewform request.")
                        new_cookie = input("Paste your updated Google Form Cookie (or press Enter to cancel): ").strip()
                        if new_cookie:
                            set_google_cookie(BASE_DIR, new_cookie)
                            print("-> Updated cookie saved to .env! Retrying submission...")
                            continue
                    break
            break

        elif action == "r":
            new_dir = input("Enter new direction/feedback for Gemini (or press Enter to keep current): ").strip()
            new_sess = input("Was there a 3-hour LeapGen session today? (y/N/topic, or press Enter to keep): ").strip()
            if new_sess:
                if new_sess.lower() in ["n", "no"]:
                    leapgen_session = None
                elif new_sess.lower() in ["y", "yes"]:
                    leapgen_session = "default"
                else:
                    leapgen_session = new_sess
            direction = new_dir if new_dir else direction
            print("\nRegenerating update...")
            try:
                update_data = generator.generate_update(
                    project_name=config.get("project_name", "Clovio"),
                    context_notes=context,
                    yesterday_submitted_tasks=prev_tasks,
                    recent_history_context=recent_history,
                    direction=direction,
                    today_date_str=sub_date,
                    leapgen_session=leapgen_session,
                )
            except Exception as e:
                print(f"[Error regenerating] {e}")

        elif action == "e":
            update_data = interactive_edit(update_data)

        elif action == "q":
            print("Cancelled. Nothing submitted.")
            break
        else:
            print("Invalid selection. Please choose S, R, E, or Q.")


if __name__ == "__main__":
    main()
