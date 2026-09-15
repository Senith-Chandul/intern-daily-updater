"""
Email Importer Module for LeapGen Daily Intern Updater.
Parses pasted Google Form confirmation email receipts using Gemini AI,
automatically extracts intern profile data (Name, Startup, Designation, Email),
and populates history.json with past daily submission records.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from gemini_generator import GeminiProgressGenerator, get_api_key
except ImportError:
    from intern_daily_updater.gemini_generator import GeminiProgressGenerator, get_api_key


def load_config_data(base_dir: Path) -> Dict[str, Any]:
    cfg_file = base_dir / "config.json"
    example_file = base_dir / "config.example.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if example_file.exists():
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config_data(base_dir: Path, cfg: Dict[str, Any]):
    cfg_file = base_dir / "config.json"
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_history_data(base_dir: Path) -> Dict[str, Any]:
    hist_file = base_dir / "history.json"
    if hist_file.exists():
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_submission": None, "submissions": {}}


def save_history_data(base_dir: Path, hist: Dict[str, Any]):
    hist_file = base_dir / "history.json"
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2)


def import_confirmation_emails(
    raw_email_text: str,
    base_dir: Optional[Path] = None,
    model: str = "gemini-flash-latest",
) -> Dict[str, Any]:
    """
    Parses raw Google Form confirmation email receipts using Gemini AI,
    updates config.json with the detected profile, and populates history.json.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent

    api_key = get_api_key(base_dir)
    if not api_key:
        raise ValueError(
            "Gemini API Key not found! Please configure your GEMINI_API_KEY in .env "
            "before importing confirmation emails."
        )

    if not raw_email_text or not raw_email_text.strip():
        raise ValueError("Please provide confirmation email text to import.")

    generator = GeminiProgressGenerator(base_dir=base_dir, model=model)
    parsed_data = generator.parse_confirmation_emails(raw_email_text)

    profile = parsed_data.get("profile", {})
    submissions = parsed_data.get("submissions", [])

    # 1. Update config.json with extracted profile
    config = load_config_data(base_dir)
    profile_updated = False
    if profile.get("startup_name"):
        config["startup_name"] = profile["startup_name"].strip()
        config["project_name"] = profile["startup_name"].strip()
        profile_updated = True
    if profile.get("intern_name"):
        config["intern_name"] = profile["intern_name"].strip()
        profile_updated = True
    if profile.get("designation"):
        config["designation"] = profile["designation"].strip()
        profile_updated = True
    if profile.get("email"):
        config["email"] = profile["email"].strip()
        profile_updated = True

    if profile_updated:
        save_config_data(base_dir, config)

    # 2. Merge extracted submissions into history.json
    history = load_history_data(base_dir)
    existing_subs = history.get("submissions", {})

    newly_added_dates = []
    for sub in submissions:
        d = sub.get("date")
        if d:
            existing_subs[d] = sub
            newly_added_dates.append(d)

    history["submissions"] = existing_subs
    if existing_subs:
        sorted_dates = sorted(existing_subs.keys())
        history["last_submission"] = existing_subs[sorted_dates[-1]]

    save_history_data(base_dir, history)

    return {
        "success": True,
        "profile": profile,
        "imported_count": len(submissions),
        "imported_dates": sorted(newly_added_dates),
        "total_history_count": len(existing_subs),
        "message": (
            f"Successfully parsed and saved {len(submissions)} submission(s) and profile for "
            f"'{profile.get('intern_name', 'Intern')}' ({profile.get('startup_name', 'Startup')})!"
        ),
    }


def cli_import_confirmation_emails(base_dir: Path, config: Dict[str, Any]) -> bool:
    """
    Interactive CLI helper to prompt the user to paste their confirmation email(s).
    """
    print("\n" + "=" * 70)
    print("        IMPORT CONFIRMATION EMAILS WITH GEMINI AI")
    print("=" * 70)
    print("Copy the Google Form confirmation email(s) from your Gmail / Outlook inbox.")
    print("You can paste multiple emails back-to-back.")
    print("When done pasting, type 'END' on a new line and press Enter (or press Ctrl+Z/Ctrl+D):\n")
    print("-" * 70)

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n[Notice] Import cancelled by user.")
            return False

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        print("[Notice] No email text was pasted.")
        return False

    print("\nAnalyzing confirmation email(s) with Gemini AI...")
    try:
        res = import_confirmation_emails(raw_text, base_dir=base_dir, model=config.get("gemini_model", "gemini-flash-latest"))
        prof = res.get("profile", {})
        print("\n" + "=" * 70)
        print("                 EMAIL IMPORT SUCCESSFUL!")
        print("=" * 70)
        print("Detected Profile:")
        print(f"  - Intern Name : {prof.get('intern_name', 'N/A')}")
        print(f"  - Startup     : {prof.get('startup_name', 'N/A')}")
        print(f"  - Designation : {prof.get('designation', 'N/A')}")
        print(f"  - Email       : {prof.get('email', 'N/A')}")
        print(f"\nImported {res.get('imported_count', 0)} daily submission(s) into history.json:")
        for d in res.get("imported_dates", []):
            print(f"  [✓] {d}")
        print(f"\nTotal historical submissions recorded: {res.get('total_history_count', 0)}")
        print("Your profile and historical submissions are now automatically configured!\n")
        return True
    except Exception as e:
        print(f"\n[Error] Failed to import confirmation emails: {e}\n")
        return False
