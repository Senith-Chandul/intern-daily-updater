"""
Credentials and Onboarding Manager for LeapGen Daily Intern Updater.
Handles discovering, prompting, validating, and saving GEMINI_API_KEY and GOOGLE_FORM_COOKIE
into .env, as well as managing user profile defaults for all LeapGen members.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

from form_schema import STARTUP_OPTIONS, INTERN_NAMES


def mask_secret(val: str, show_start: int = 6, show_end: int = 4) -> str:
    if not val:
        return ""
    val = val.strip()
    if len(val) <= (show_start + show_end):
        return "***"
    return f"{val[:show_start]}...{val[-show_end:]}"


def load_env_dict(env_path: Path) -> Dict[str, str]:
    vars_dict = {}
    if not env_path.exists():
        return vars_dict
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            vars_dict[key.strip()] = val.strip().strip('"').strip("'")
    return vars_dict


def save_env_var(base_dir: Path, key: str, value: str):
    """Update or add an environment variable in base_dir / .env."""
    env_path = base_dir / ".env"
    lines = []
    found = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
                    lines.append(f'{key}="{value}"\n')
                    found = True
                else:
                    lines.append(line)

    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f'{key}="{value}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Also update runtime os.environ
    os.environ[key] = value


def get_gemini_api_key(base_dir: Path) -> str:
    """Retrieve Gemini API key from environment variable or .env."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return key

    env_vars = load_env_dict(base_dir / ".env")
    key = env_vars.get("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return key
    return ""


def set_gemini_api_key(base_dir: Path, key: str):
    save_env_var(base_dir, "GEMINI_API_KEY", key.strip())


def get_google_cookie(base_dir: Path) -> str:
    """Retrieve Google session Cookie header from environment or .env."""
    cookie = os.environ.get("GOOGLE_FORM_COOKIE", "").strip()
    if cookie:
        return cookie

    env_vars = load_env_dict(base_dir / ".env")
    return env_vars.get("GOOGLE_FORM_COOKIE", "").strip()


def set_google_cookie(base_dir: Path, cookie: str):
    save_env_var(base_dir, "GOOGLE_FORM_COOKIE", cookie.strip())


def set_cookie_in_env(cookie_str: str, base_dir: Optional[Path] = None):
    if base_dir is None:
        base_dir = Path(__file__).parent
    set_google_cookie(base_dir, cookie_str)


def test_gemini_api_key(api_key: str, model: str = "gemini-flash-latest") -> Tuple[bool, str]:
    """Test calling the Gemini API with the given key."""
    if not api_key:
        return False, "API key cannot be empty."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"
    payload = {
        "contents": [{"parts": [{"text": "Hello, respond with OK if you receive this."}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 10},
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200:
            return True, "API Key successfully verified with Gemini!"
        else:
            try:
                err_data = resp.json()
                msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            return False, f"Gemini verification failed ({resp.status_code}): {msg}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"


def interactive_cli_setup(base_dir: Path, config: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
    """
    Guides any new LeapGen member through entering their API key, session cookie, and profile.
    Automatically called if API key is missing, or when user chooses setup.
    """
    current_key = get_gemini_api_key(base_dir)
    current_cookie = get_google_cookie(base_dir)

    print("\n" + "=" * 70)
    print("        LEAPGEN INTERN PROGRESS TOOL: ONBOARDING & SETUP")
    print("=" * 70)
    print("Welcome! Let's quickly set up your keys and startup profile.\n")

    # Step 1: Gemini API Key
    if not current_key or force:
        print("--- STEP 1: Google Gemini API Key ---")
        print("To generate realistic daily standups, this tool connects to Google Gemini.")
        print("👉 Get your 100% free Gemini API key here in 30 seconds:")
        print("   https://aistudio.google.com/app/apikey\n")

        while True:
            prompt_text = "Enter your Gemini API key: " if not current_key else f"Enter Gemini API key [Enter to keep {mask_secret(current_key)}]: "
            entered_key = input(prompt_text).strip()
            if not entered_key and current_key:
                break
            if entered_key:
                print("Verifying key with Gemini API...")
                ok, msg = test_gemini_api_key(entered_key)
                if ok:
                    set_gemini_api_key(base_dir, entered_key)
                    print(f"[Success] {msg}")
                    break
                else:
                    print(f"[Warning] {msg}")
                    retry = input("Save this key anyway? [y/N]: ").strip().lower()
                    if retry in ["y", "yes"]:
                        set_gemini_api_key(base_dir, entered_key)
                        break
            else:
                print("API key is required to generate progress reports.")

    # Step 2: Google Form Cookie
    if not current_cookie or force:
        print("\n--- STEP 2: Google Form Session Cookie ---")
        print("The official LeapGen Google Form records your verified @iit.ac.lk identity.")
        print("To authorize submissions:")
        print("  1. Open Google Chrome/Edge and open the LeapGen Google Form (logged into @iit.ac.lk).")
        print("  2. Press F12 -> Network tab -> Refresh the page.")
        print("  3. Click 'viewform' -> in Request Headers, right-click 'Cookie' -> Copy value.")
        print("  4. Paste the copied cookie header below.\n")

        prompt_cookie = "Paste your Google Form Cookie (or press Enter to skip for now): " if not current_cookie else f"Paste new Cookie [Enter to keep current {mask_secret(current_cookie)}]: "
        entered_cookie = input(prompt_cookie).strip()
        if entered_cookie:
            set_google_cookie(base_dir, entered_cookie)
            print("[Success] Google Form Cookie saved into .env!")
        elif not current_cookie:
            print("[Notice] Cookie skipped. You can still test with test forms or set it later.")

    # Step 3: Startup Profile
    print("\n--- STEP 3: Your Startup Profile & Past Submissions ---")
    print("💡 Fast-Track: If you have Google Form confirmation email receipts in your inbox,")
    print("   you can paste them now to automatically detect your name, startup, and past submissions!")
    fast_track = input("Paste confirmation email(s) now to auto-fill? [y/N]: ").strip().lower()
    if fast_track in ["y", "yes"]:
        try:
            from email_importer import cli_import_confirmation_emails, load_config_data
            if cli_import_confirmation_emails(base_dir, config):
                config = load_config_data(base_dir)
                print("=" * 70)
                print("          SETUP COMPLETE! ALL CREDENTIALS & PROFILE SAVED")
                print("=" * 70)
                return config
        except Exception as e:
            print(f"[Notice] Email import encountered an error ({e}). Continuing with manual profile selection...\n")

    print("\nChoose your startup from the official LeapGen accelerator cohort:")
    for i, st in enumerate(STARTUP_OPTIONS, 1):
        is_curr = " (current)" if st == config.get("startup_name") else ""
        print(f"  [{i}] {st}{is_curr}")
    
    st_choice = input(f"Select startup (1-{len(STARTUP_OPTIONS)}, or press Enter to keep): ").strip()
    if st_choice.isdigit() and 1 <= int(st_choice) <= len(STARTUP_OPTIONS):
        selected_startup = STARTUP_OPTIONS[int(st_choice) - 1]
        config["startup_name"] = selected_startup
        config["project_name"] = selected_startup
        print(f"-> Startup set to: {selected_startup}")

    print("\nChoose your name from the official intern roster:")
    for i, name in enumerate(INTERN_NAMES, 1):
        is_curr = " (current)" if name == config.get("intern_name") else ""
        print(f"  [{i:2d}] {name}{is_curr}")
    print("  [0] Other (enter custom name)")

    name_choice = input("Select your name (0-18, or press Enter to keep): ").strip()
    if name_choice == "0":
        custom_name = input("Enter your full intern name: ").strip()
        if custom_name:
            config["intern_name"] = custom_name
    elif name_choice.isdigit() and 1 <= int(name_choice) <= len(INTERN_NAMES):
        config["intern_name"] = INTERN_NAMES[int(name_choice) - 1]

    desig = input(f"Enter Designation [current: {config.get('designation', 'Software Engineering Intern')}]: ").strip()
    if desig:
        config["designation"] = desig

    email = input(f"Enter your @iit.ac.lk Email [current: {config.get('email', '')}]: ").strip()
    if email:
        config["email"] = email

    # Save to config.json
    cfg_path = base_dir / "config.json"
    import json
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 70)
    print("          SETUP COMPLETE! ALL CREDENTIALS & PROFILE SAVED")
    print("=" * 70)
    print(f"Startup:      {config.get('startup_name')}")
    print(f"Intern Name:  {config.get('intern_name')}")
    print(f"Email:        {config.get('email')}")
    print("You're ready to start generating and submitting daily updates!\n")
    return config
