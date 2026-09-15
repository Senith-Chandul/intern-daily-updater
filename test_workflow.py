"""
Unit and verification test for intern_daily_updater components.
Tests schema, hour normalization, payload generation, and history tracking.
"""

import json
import shutil
import tempfile
from pathlib import Path
from form_schema import ENTRIES, STARTUP_OPTIONS, INTERN_NAMES
from form_submitter import FormSubmitter
from gemini_generator import validate_and_normalize_hours


def test_schema_and_constants():
    assert len(STARTUP_OPTIONS) == 8, "Expected 8 startups in schema"
    assert len(INTERN_NAMES) == 18, "Expected 18 intern names in schema"
    assert ENTRIES["startup_name"] == "entry.1157714591"
    assert ENTRIES["intern_name"] == "entry.301083567"
    assert ENTRIES["designation"] == "entry.2111390916"
    assert ENTRIES["tasks_yesterday"] == "entry.1620462389"
    assert ENTRIES["tasks_today"] == "entry.396642985"
    print("[OK] Schema and constants verified.")


def test_hours_validation():
    # Case 1: Low hours (e.g. 2.0 + 2.0 = 4.0) -> must scale to between 6.0 and 9.0
    low_tasks = [
        {"title": "Task 1", "time_spent": 2.0},
        {"title": "Task 2", "time_spent": 2.0},
    ]
    normalized = validate_and_normalize_hours(low_tasks)
    total = sum(t["time_spent"] for t in normalized)
    assert 6.0 <= total <= 9.0, f"Expected 6.0 <= total <= 9.0, got {total}"

    # Case 2: High hours (e.g. 6.0 + 5.0 = 11.0) -> must scale down to between 6.0 and 9.0
    high_tasks = [
        {"title": "Task 1", "time_spent": 6.0},
        {"title": "Task 2", "time_spent": 5.0},
    ]
    normalized_high = validate_and_normalize_hours(high_tasks)
    total_high = sum(t["time_spent"] for t in normalized_high)
    assert 6.0 <= total_high <= 9.0, f"Expected 6.0 <= total <= 9.0, got {total_high}"

    # Case 3: Already in range (e.g. 4.5 + 3.0 = 7.5) -> unchanged
    normal_tasks = [
        {"title": "Task 1", "time_spent": 4.5},
        {"title": "Task 2", "time_spent": 3.0},
    ]
    norm_normal = validate_and_normalize_hours(normal_tasks)
    total_norm = sum(t["time_spent"] for t in norm_normal)
    # Case 4: LeapGen session preservation (Session is 3.0h, other task needs scaling)
    session_tasks = [
        {"title": "LeapGen : Attended a 3-hour lecture on Startup Success", "time_spent": 3.0},
        {"title": "Worked on website UI", "time_spent": 1.0},
    ]
    norm_session = validate_and_normalize_hours(session_tasks)
    total_session = sum(t["time_spent"] for t in norm_session)
    assert norm_session[0]["time_spent"] == 3.0, "Session task must stay 3.0h"
    assert 6.0 <= total_session <= 9.0, f"Expected 6.0 <= total <= 9.0, got {total_session}"

    print(f"[OK] Hours validation verified (totals: {total}, {total_high}, {total_norm}, {total_session}).")


def test_payload_builder_and_history():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        hist_file = temp_dir / "history.json"
        submitter = FormSubmitter(history_file=hist_file)

        sample_config = {
            "startup_name": "Axacrate Technologies",
            "intern_name": "Dulaj Yuthsara Jayasingha",
            "designation": "Software Engineering Intern",
            "email": "intern@example.com",
        }

        sample_update = {
            "tasks_yesterday": "1. Core Platform : Implemented REST authentication\n2. Core Platform : Configured JWT middleware",
            "tasks_today": "1. Core Platform : Created unit tests for auth module\n2. Core Platform : Added rate-limiting filter",
            "task_items": [
                {
                    "task_number": 1,
                    "title": "Created unit tests for auth module",
                    "continuation": "Yes",
                    "status": "In progress",
                    "time_spent": 4.5,
                    "completion_date": "2026-09-09",
                },
                {
                    "task_number": 2,
                    "title": "Added rate-limiting filter",
                    "continuation": "No",
                    "status": "Completed",
                    "time_spent": 3.0,
                    "completion_date": "2026-09-09",
                },
            ],
            "challenges": "None",
        }

        # Dry run submit
        res = submitter.submit(sample_config, sample_update, dry_run=True)
        assert res["success"] is True
        assert res["dry_run"] is True

        payload = res["payload"]
        assert payload[ENTRIES["startup_name"]] == "Axacrate Technologies"
        assert payload[ENTRIES["intern_name"]] == "Dulaj Yuthsara Jayasingha"
        assert payload[ENTRIES["designation"]] == "Software Engineering Intern"
        assert payload[ENTRIES["email"]] == "intern@example.com"
        assert payload[ENTRIES["tasks_today"]] == sample_update["tasks_today"]
        assert payload[ENTRIES["continuation"][1]] == "Yes"
        assert payload[ENTRIES["status"][1]] == "In progress"
        assert payload[ENTRIES["time_spent"][1]] == "4.5"
        assert payload[ENTRIES["challenges"]] == "None"

        # Test history recording with custom date
        submitter.record_history(sample_update, submission_date_str="2026-09-05")
        assert hist_file.exists()
        with open(hist_file, "r") as f:
            hist_data = json.load(f)
            assert "2026-09-05" in hist_data["submissions"]
            assert hist_data["submissions"]["2026-09-05"]["tasks_today"] == sample_update["tasks_today"]

        # Test chronological retrieval: retrieving tasks before 2026-09-08 should yield 2026-09-05's tasks
        prev_tasks, recent_ctx = submitter.get_previous_tasks(before_date_str="2026-09-08")
        assert prev_tasks == sample_update["tasks_today"]
        assert len(recent_ctx) == 1

        print("[OK] Payload building, custom dates, and history chaining verified.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_missing_weekdays():
    from catch_up import find_missing_weekdays, _sync_task_items_from_lines
    # July 24 (Fri) to July 28 (Tue):
    # July 24 = Fri (submitted)
    # July 25 = Sat (weekend, skipped)
    # July 26 = Sun (weekend, skipped)
    # July 27 = Mon (missing)
    # July 28 = Tue (missing)
    mock_submissions = {"2026-07-24": {}}
    missing = find_missing_weekdays(mock_submissions, start_date="2026-07-24", end_date="2026-07-28")
    assert missing == ["2026-07-27", "2026-07-28"]

    # With absent date
    missing_with_absent = find_missing_weekdays(
        mock_submissions, start_date="2026-07-24", end_date="2026-07-28", absent_dates={"2026-07-27"}
    )
    assert missing_with_absent == ["2026-07-28"]

    # Test manual edit line sync
    sample_data = {"task_items": []}
    _sync_task_items_from_lines(sample_data, [
        "1. Clovio : Fixed navbar mobile bug",
        "2. LeapGen_Business : Printed sample shirts in Pettah"
    ])
    assert len(sample_data["task_items"]) == 2
    assert sample_data["task_items"][0]["title"] == "Fixed navbar mobile bug"
    assert sample_data["task_items"][1]["title"] == "Printed sample shirts in Pettah"
    total_h = sum(t["time_spent"] for t in sample_data["task_items"])
    assert 6.0 <= total_h <= 9.0
    print("[OK] find_missing_weekdays and manual edit line sync verified.")


def test_email_importer():
    from email_importer import load_config_data, save_config_data, load_history_data, save_history_data

    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        # 1. Config save & load
        cfg = {"startup_name": "Clovio", "intern_name": "Senith Sagarage"}
        save_config_data(temp_dir, cfg)
        loaded_cfg = load_config_data(temp_dir)
        assert loaded_cfg["intern_name"] == "Senith Sagarage"
        assert loaded_cfg["startup_name"] == "Clovio"

        # 2. History save & load
        hist = {
            "last_submission": {"date": "2026-07-24"},
            "submissions": {
                "2026-07-24": {"date": "2026-07-24", "tasks_today": "Task 1"}
            }
        }
        save_history_data(temp_dir, hist)
        loaded_hist = load_history_data(temp_dir)
        assert "2026-07-24" in loaded_hist["submissions"]
        assert loaded_hist["last_submission"]["date"] == "2026-07-24"

    print("[OK] Email importer configuration and history persistence verified.")


if __name__ == "__main__":
    print("Running component tests...")
    test_schema_and_constants()
    test_hours_validation()
    test_payload_builder_and_history()
    test_missing_weekdays()
    test_email_importer()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

