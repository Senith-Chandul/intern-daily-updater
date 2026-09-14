"""
Batch Catch-Up and Backfill engine for LeapGen Daily Intern Updates.
Quickly and seamlessly generates and submits missing daily progress reports,
skipping weekends, excluding absent days, and maintaining smooth day-to-day task continuity.
"""

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from form_submitter import FormSubmitter
from gemini_generator import GeminiProgressGenerator, get_api_key, validate_and_normalize_hours


def parse_date_str(date_str: str) -> datetime.date:
    return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def _sync_task_items_from_lines(update_data: Dict[str, Any], lines: List[str]):
    """Sync task_items array with lines from tasks_today, keeping hours valid."""
    existing_items = update_data.get("task_items", [])
    new_items = []
    default_hours = round(7.5 / max(1, len(lines)), 1)

    for i, line in enumerate(lines, 1):
        clean = line.strip()
        if ":" in clean:
            title = clean.split(":", 1)[1].strip()
        else:
            title = re.sub(r"^\d+[\.\)]\s*", "", clean).strip()
        if not title:
            title = clean

        if i <= len(existing_items):
            item = existing_items[i - 1].copy()
            item["task_number"] = i
            item["title"] = title[:70]
        else:
            item = {
                "task_number": i,
                "title": title[:70],
                "continuation": "No",
                "status": "Completed",
                "time_spent": default_hours,
                "completion_date": "",
            }
        new_items.append(item)

    update_data["task_items"] = validate_and_normalize_hours(new_items)


def _edit_tasks_today(update_data: Dict[str, Any]):
    current_lines = [l.strip() for l in update_data.get("tasks_today", "").split("\n") if l.strip()]
    print("\n--- Edit 'Tasks I did today' ---")
    for i, line in enumerate(current_lines, 1):
        print(f"  [{i}] {line}")
    print("\nOptions:")
    print("  [R] Replace ALL lines (paste new lines, empty line to finish)")
    if current_lines:
        print(f"  [1-{len(current_lines)}] Edit a specific line")
    print("  [+] Add a new line")
    if current_lines:
        print("  [-] Delete a line")
    print("  [B] Back to Edit Menu")
    opt = input("Choice: ").strip().lower()

    if opt == "r":
        print("\nEnter all task lines (e.g. '1. Clovio : ...'). Press Enter on an empty line when finished:")
        new_lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line:
                break
            new_lines.append(line.strip())
        if new_lines:
            update_data["tasks_today"] = "\n".join(new_lines)
            _sync_task_items_from_lines(update_data, new_lines)
            print("-> Replaced all today's task lines.")

    elif opt.isdigit() and 1 <= int(opt) <= len(current_lines):
        idx = int(opt) - 1
        print(f"\nCurrent: {current_lines[idx]}")
        nl = input("New line (or Enter to keep): ").strip()
        if nl:
            current_lines[idx] = nl
            update_data["tasks_today"] = "\n".join(current_lines)
            _sync_task_items_from_lines(update_data, current_lines)
            print(f"-> Line {idx + 1} updated.")

    elif opt == "+":
        nl = input("\nEnter new task line (e.g. '3. Clovio : Details'): ").strip()
        if nl:
            current_lines.append(nl)
            update_data["tasks_today"] = "\n".join(current_lines)
            _sync_task_items_from_lines(update_data, current_lines)
            print("-> Task line added.")

    elif opt == "-" and current_lines:
        del_num = input(f"Enter line number to delete (1-{len(current_lines)}): ").strip()
        if del_num.isdigit() and 1 <= int(del_num) <= len(current_lines):
            idx = int(del_num) - 1
            deleted = current_lines.pop(idx)
            update_data["tasks_today"] = "\n".join(current_lines)
            _sync_task_items_from_lines(update_data, current_lines)
            print(f"-> Deleted line: {deleted}")


def _edit_tasks_yesterday(update_data: Dict[str, Any]):
    print("\n--- Edit 'Tasks I did yesterday' ---")
    print("Current:")
    for line in update_data.get("tasks_yesterday", "").split("\n"):
        if line.strip():
            print(f"  {line.strip()}")
    print("\nEnter new yesterday tasks (paste lines, press Enter on empty line to finish, or press Enter immediately to keep):")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line:
            break
        lines.append(line.strip())
    if lines:
        update_data["tasks_yesterday"] = "\n".join(lines)
        print("-> Updated 'Tasks I did yesterday'.")


def _edit_task_breakdown(update_data: Dict[str, Any]):
    task_items = update_data.get("task_items", [])
    if not task_items:
        print("\nNo task items found to edit.")
        return

    while True:
        print("\n--- Current Task Breakdown ---")
        for i, t in enumerate(task_items, 1):
            print(f"  [{i}] {t.get('title')} | {t.get('time_spent')} hrs | {t.get('status')} | Continuation: {t.get('continuation', 'No')}")
        tot = sum(float(t.get("time_spent", 0.0)) for t in task_items)
        print(f"  Total Hours: {tot:.1f} hrs")
        sel = input(f"\nSelect task to edit (1-{len(task_items)}, or Enter to return): ").strip()
        if not sel:
            break
        if sel.isdigit() and 1 <= int(sel) <= len(task_items):
            idx = int(sel) - 1
            item = task_items[idx]
            print(f"\nEditing Task {sel}: '{item.get('title')}'")

            nt = input(f"Title [current: {item.get('title')}]: ").strip()
            if nt:
                item["title"] = nt[:70]

            nh = input(f"Hours spent [current: {item.get('time_spent')}]: ").strip()
            if nh:
                try:
                    item["time_spent"] = float(nh)
                except ValueError:
                    print("Invalid number for hours; keeping current.")

            ns = input(f"Status: 1=Completed, 2=In progress [current: {item.get('status')}]: ").strip()
            if ns == "1":
                item["status"] = "Completed"
            elif ns == "2":
                item["status"] = "In progress"
            elif ns:
                item["status"] = ns

            nc = input(f"Continuation of yesterday? (y/n) [current: {item.get('continuation', 'No')}]: ").strip().lower()
            if nc in ["y", "yes"]:
                item["continuation"] = "Yes"
            elif nc in ["n", "no"]:
                item["continuation"] = "No"

            print(f"-> Updated Task {sel}.")


def _edit_challenges(update_data: Dict[str, Any]):
    print(f"\nCurrent challenges: {update_data.get('challenges', 'None')}")
    new_val = input("Enter new challenges (press Enter to keep, or type 'None'): ").strip()
    if new_val:
        update_data["challenges"] = new_val
        print("-> Challenges updated.")


def interactive_edit(update_data: Dict[str, Any], date_str: str = "") -> Dict[str, Any]:
    """Manually edit tasks, hours, or challenges in catch-up mode."""
    header_date = f" ({date_str})" if date_str else ""
    while True:
        task_items = update_data.get("task_items", [])
        total_h = sum(float(t.get("time_spent", 0.0)) for t in task_items)

        print("\n" + "=" * 60)
        print(f"          MANUAL EDIT MENU{header_date}")
        print("=" * 60)
        print("Current Today's Tasks:")
        for line in update_data.get("tasks_today", "").split("\n"):
            if line.strip():
                print(f"  {line.strip()}")
        print(f"Total Hours: {total_h:.1f}h ({len(task_items)} tasks) | Challenges: {update_data.get('challenges', 'None')}")
        print("-" * 60)
        print("  1. Edit 'Tasks I did today' (edit specific line, add, or replace all)")
        print("  2. Edit 'Tasks I did yesterday'")
        print("  3. Edit Task Breakdown (Hours, Status, Continuation, Title)")
        print("  4. Edit 'Challenges faced'")
        print("  5. Auto-balance hours to 7.5 hrs")
        print("  6. Done (Save & return to stepper)")
        print("-" * 60)
        choice = input("Select option (1-6, Enter=Done): ").strip()

        if choice in ["6", "done", ""]:
            # Check hours warning
            curr_items = update_data.get("task_items", [])
            curr_tot = sum(float(t.get("time_spent", 0.0)) for t in curr_items)
            if curr_tot < 6.0 or curr_tot > 9.0:
                print(f"\n[Warning] Total hours is {curr_tot:.1f}h (form requires 6.0 - 9.0 hrs).")
                fix = input("Auto-balance hours to 7.5h before continuing? [Y/n]: ").strip().lower()
                if fix not in ["n", "no"]:
                    update_data["task_items"] = validate_and_normalize_hours(curr_items)
                    print("-> Hours auto-balanced.")
            break

        elif choice == "1":
            _edit_tasks_today(update_data)

        elif choice == "2":
            _edit_tasks_yesterday(update_data)

        elif choice == "3":
            _edit_task_breakdown(update_data)

        elif choice == "4":
            _edit_challenges(update_data)

        elif choice == "5":
            update_data["task_items"] = validate_and_normalize_hours(update_data.get("task_items", []))
            new_tot = sum(float(t.get("time_spent", 0.0)) for t in update_data["task_items"])
            print(f"-> Hours balanced to {new_tot:.1f} hrs.")

    return update_data


def find_missing_weekdays(
    submissions: Dict[str, Any],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    absent_dates: Optional[Set[str]] = None,
) -> List[str]:
    """
    Find all missing weekdays between start_date and end_date.
    Excludes weekends (Sat/Sun), already submitted dates, and absent dates.
    """
    recorded_dates = set(submissions.keys())
    absent = absent_dates or set()

    # Determine start date
    if start_date:
        start_dt = parse_date_str(start_date)
    else:
        # Default start: July 24, 2026
        start_dt = parse_date_str("2026-07-24")

    # Determine end date
    if end_date:
        end_dt = parse_date_str(end_date)
    else:
        end_dt = datetime.date.today()

    missing = []
    curr = start_dt
    while curr <= end_dt:
        # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
        if curr.weekday() < 5:
            d_str = curr.strftime("%Y-%m-%d")
            if d_str not in recorded_dates and d_str not in absent:
                missing.append(d_str)
        curr += datetime.timedelta(days=1)

    return missing


# Realistic distribution of accelerator workshop topics for session days (only when user opts in with [W])
ACCELERATOR_TOPICS = [
    "Startup Valuation & Financial Modeling",
    "Customer Discovery & Market Validation",
    "B2B Sales, Cold Outreach & Pricing Strategy",
    "Investor Pitch Deck Architecture & Storytelling",
    "Unit Economics, CAC vs. LTV & Growth Levers",
    "Product-Market Fit & Agile Sprint Planning",
    "Mentor Review & Mid-Cohort Progress Pitch",
]


def run_catch_up(
    config: Dict[str, Any],
    context: str,
    target: str = "test",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    absent_dates_input: Optional[List[str]] = None,
    auto_pilot: bool = False,
    dry_run: bool = False,
):
    """
    Run the batch catch-up workflow.
    Supports interactive stepper or automated continuous submission.
    """
    submitter = FormSubmitter(history_file=BASE_DIR / "history.json", base_dir=BASE_DIR)
    history = submitter.load_history()
    submissions = history.get("submissions", {})

    # Load absent dates from config or input
    configured_absent = set(config.get("absent_dates", []))
    if absent_dates_input:
        for item in absent_dates_input:
            for part in item.split(","):
                part = part.strip()
                if part:
                    configured_absent.add(part)

    print("\n" + "=" * 70)
    print("        LEAPGEN BATCH CATCH-UP & FAST BACKFILL SYSTEM")
    print("=" * 70)
    print(f"Target Form:       [{target.upper()}] {config.get('startup_name')} - {config.get('intern_name')}")
    print(f"Mode:              {'Auto-Pilot (Continuous)' if auto_pilot else 'Interactive Stepper'}")
    print(f"Dry Run:           {dry_run}")
    if configured_absent:
        print(f"Absent Days ({len(configured_absent)}): {', '.join(sorted(configured_absent))}")

    missing_dates = find_missing_weekdays(
        submissions=submissions,
        start_date=start_date,
        end_date=end_date,
        absent_dates=configured_absent,
    )

    if not missing_dates:
        print("\n[All Caught Up!] No missing weekdays found in the specified range.")
        print("Your submissions are completely up-to-date!\n")
        return

    print(f"\nFound {len(missing_dates)} missing weekday(s) to catch up:")
    print(f"  From: {missing_dates[0]}")
    print(f"  To:   {missing_dates[-1]}")
    print("-" * 70)

    # If interactive and absent dates weren't given on CLI, prompt user
    if not auto_pilot and not absent_dates_input:
        absent_prompt = input(
            "Enter any absent dates to skip (comma-separated YYYY-MM-DD, or press Enter if none): "
        ).strip()
        if absent_prompt:
            for part in absent_prompt.split(","):
                part = part.strip()
                if part:
                    configured_absent.add(part)
            # Re-filter missing dates
            missing_dates = [d for d in missing_dates if d not in configured_absent]
            print(f"Updated list: {len(missing_dates)} weekday(s) remaining after skipping absent days.")

    # If interactive, prompt for optional general direction / project phase
    general_direction = ""
    if not auto_pilot:
        gen_prompt = input(
            "Enter general direction/phase for catch-up (e.g. 'working on pettah print shop website and mug orders', or press Enter to skip): "
        ).strip()
        if gen_prompt:
            general_direction = gen_prompt
            print(f"-> General direction set: '{general_direction}'")

    if not auto_pilot:
        print("\nInteractive Stepper Controls:")
        print("  [Enter / S] : Approve & Submit this date, immediately advance to next")
        print("  [E]         : Manually edit tasks, hours, or challenges before submitting")
        print("  [A / X]     : Mark this date as ABSENT (skip it)")
        print("  [W]         : Toggle 3-hour LeapGen Workshop for this date")
        print("  [D]         : Provide specific direction for THIS date only")
        print("  [G]         : Set GENERAL direction/phase for this date and all subsequent days")
        print("  [Auto]      : Switch to Auto-Pilot for all remaining dates")
        print("  [Q]         : Pause / Quit (completed days remain saved in history.json)")
        print("-" * 70)
        input("Press Enter to begin catching up...")

    generator = GeminiProgressGenerator(base_dir=BASE_DIR, model=config.get("gemini_model", "gemini-3.6-flash"))
    total_to_process = len(missing_dates)
    success_count = 0
    skipped_count = 0

    session_topic_idx = 0

    for idx, current_date in enumerate(missing_dates, 1):
        dt = parse_date_str(current_date)
        weekday_name = dt.strftime("%A")

        # Do NOT automatically inject workshops unless requested by user via [W]
        is_session_day = False
        session_topic = None
        day_specific_direction = ""

        need_regenerate = True
        update_data = None

        # Loop for current date (allows manual editing, regenerating, or retrying)
        while True:
            if need_regenerate:
                # Refresh previous work dynamically before generating
                prev_tasks, recent_history = submitter.get_previous_tasks(before_date_str=current_date)

                # Determine combined effective direction
                if general_direction and day_specific_direction:
                    effective_direction = f"Phase: {general_direction}. Today's focus: {day_specific_direction}"
                elif general_direction:
                    effective_direction = general_direction
                else:
                    effective_direction = day_specific_direction

                print(f"\n[{idx}/{total_to_process}] Generating update for {current_date} ({weekday_name})...")
                if session_topic:
                    print(f"      LeapGen Session: Yes ('{session_topic}')")
                if general_direction:
                    print(f"      General Phase:   '{general_direction}'")
                if day_specific_direction:
                    print(f"      Today's Focus:   '{day_specific_direction}'")

                try:
                    update_data = generator.generate_update(
                        project_name=config.get("project_name", "Clovio"),
                        context_notes=context,
                        yesterday_submitted_tasks=prev_tasks,
                        recent_history_context=recent_history,
                        direction=effective_direction,
                        today_date_str=current_date,
                        leapgen_session=session_topic,
                    )
                    need_regenerate = False
                except Exception as e:
                    print(f"[Error generating for {current_date}] {e}")
                    retry = input("Press [R] to retry generating this date or [S] to skip: ").strip().lower()
                    if retry == "s":
                        skipped_count += 1
                        break
                    continue

            # Stepper Review
            if not auto_pilot:
                print("\n" + "-" * 70)
                print(f"  DATE: {current_date} ({weekday_name})")
                if general_direction:
                    print(f"  PHASE: {general_direction}")
                print("  TODAY'S TASKS:")
                for line in update_data.get("tasks_today", "").split("\n"):
                    if line.strip():
                        print(f"    {line.strip()}")
                task_items = update_data.get("task_items", [])
                total_h = sum(float(t.get("time_spent", 0.0)) for t in task_items)
                print(f"  TOTAL HOURS: {total_h:.1f} hrs ({len(task_items)} tasks) | Challenges: {update_data.get('challenges', 'None')}")
                print("-" * 70)

                action = input(f"[{idx}/{total_to_process}] Action [Enter=Submit / E=Edit / A=Absent / W=Workshop / D=Day Direction / G=General Direction / Auto / Q=Quit]: ").strip().lower()

                if action in ["e", "edit", "m", "manual"]:
                    update_data = interactive_edit(update_data, date_str=current_date)
                    need_regenerate = False
                    continue

                elif action in ["a", "x"]:
                    print(f"-> Marked {current_date} as ABSENT. Skipped.")
                    configured_absent.add(current_date)
                    config["absent_dates"] = sorted(list(configured_absent))
                    with open(BASE_DIR / "config.json", "w", encoding="utf-8") as cf:
                        json.dump(config, cf, indent=2)
                    skipped_count += 1
                    break

                elif action == "w":
                    is_session_day = not is_session_day
                    if is_session_day:
                        custom_topic = input("Enter workshop topic (or press Enter for default): ").strip()
                        session_topic = custom_topic or ACCELERATOR_TOPICS[session_topic_idx % len(ACCELERATOR_TOPICS)]
                        session_topic_idx += 1
                    else:
                        session_topic = None
                    print(f"-> Toggled workshop: {'YES (' + str(session_topic) + ')' if session_topic else 'NO'}. Regenerating...")
                    need_regenerate = True
                    continue

                elif action == "d":
                    day_specific_direction = input("Enter specific direction/focus for THIS day only: ").strip()
                    print("-> Regenerating with new direction...")
                    need_regenerate = True
                    continue

                elif action == "g":
                    new_gen = input(f"Enter GENERAL direction from {current_date} onwards (press Enter to clear): ").strip()
                    general_direction = new_gen
                    day_specific_direction = ""
                    if general_direction:
                        print(f"-> General direction updated to: '{general_direction}'. Regenerating {current_date}...")
                    else:
                        print(f"-> Cleared general direction. Regenerating {current_date}...")
                    need_regenerate = True
                    continue

                elif action == "auto":
                    print("-> Switching to AUTO-PILOT for all remaining dates!")
                    auto_pilot = True

                elif action == "q":
                    print("\nCatch-up paused by user. All submitted dates are saved in history.json.")
                    print(f"Processed: {success_count} submitted, {skipped_count} skipped. Run again anytime to resume!\n")
                    return

            # Inner Submission Loop (Submits without regenerating; supports retry and manual edit)
            submit_success = False
            while not submit_success:
                print(f"-> Submitting {current_date} to [{target.upper()}] form...")
                res = submitter.submit(
                    config=config,
                    update_data=update_data,
                    submission_date_str=current_date,
                    target=target,
                    dry_run=dry_run,
                )

                if res.get("success"):
                    success_count += 1
                    prefix = "[DRY-RUN]" if dry_run else "[SUCCESS]"
                    print(f"{prefix} Day {idx}/{total_to_process} ({current_date}) completed successfully!")
                    submit_success = True
                    if not dry_run and idx < total_to_process:
                        time.sleep(1.5)
                    break
                else:
                    msg_str = str(res.get("message", "")).lower()
                    print(f"[FAILED] Submission error for {current_date}: {res.get('message')}")
                    if auto_pilot:
                        print("-> Stopping auto-pilot due to submission error.")
                        auto_pilot = False

                    if "401" in msg_str or "cookie" in msg_str or "auth" in msg_str:
                        print("\n[Auth Required] Your Google Form session cookie is missing or has expired.")
                        print("Open Chrome/Edge (logged into @iit.ac.lk) -> F12 -> Network -> copy 'Cookie:' from viewform request.")
                        new_cookie = input("Paste your updated Google Form Cookie (or press Enter to see other options): ").strip()
                        if new_cookie:
                            from credentials import set_google_cookie
                            set_google_cookie(BASE_DIR, new_cookie)
                            print("-> Updated cookie saved to .env! Retrying submission with same tasks...")
                            continue

                    fail_action = input("\nSubmission failed. [R=Retry with same tasks / E=Edit tasks / G=Regenerate / S=Skip date / Q=Quit]: ").strip().lower()
                    if fail_action in ["r", "retry", ""]:
                        print("-> Retrying submission with existing tasks (no regeneration)...")
                        continue
                    elif fail_action in ["e", "edit", "m"]:
                        update_data = interactive_edit(update_data, date_str=current_date)
                        print("-> Retrying submission with edited tasks...")
                        continue
                    elif fail_action in ["g", "regen", "regenerate"]:
                        print(f"-> Regenerating new tasks for {current_date}...")
                        need_regenerate = True
                        break
                    elif fail_action in ["s", "skip"]:
                        print(f"-> Skipped {current_date}.")
                        skipped_count += 1
                        submit_success = True
                        break
                    else:
                        print("\nCatch-up paused by user.")
                        print(f"Processed: {success_count} submitted, {skipped_count} skipped.\n")
                        return

            if need_regenerate:
                continue

            if submit_success:
                break

    print("\n" + "=" * 70)
    print("             BATCH CATCH-UP COMPLETE!")
    print("=" * 70)
    print(f"Successfully Submitted: {success_count} day(s)")
    if skipped_count:
        print(f"Skipped / Absent:       {skipped_count} day(s)")
    print(f"Target:                 [{target.upper()}]")
    print("All progress is saved in history.json.")
    print("=" * 70 + "\n")
