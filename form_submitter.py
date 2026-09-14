"""
Form Submitter module for LeapGen Intern Progress Update.
Packages structured update data into Google Form URL-encoded POST payloads.
Supports switching between Official Form and Test Form dynamically,
extracting CSRF tokens, and handling multi-page form submissions.
"""

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

try:
    from form_schema import ENTRIES as OFFICIAL_ENTRIES, FORM_SUBMIT_URL as OFFICIAL_SUBMIT_URL, FORM_VIEW_URL as OFFICIAL_VIEW_URL
    from form_extractor import extract_schema_from_url
except ImportError:
    from intern_daily_updater.form_schema import ENTRIES as OFFICIAL_ENTRIES, FORM_SUBMIT_URL as OFFICIAL_SUBMIT_URL, FORM_VIEW_URL as OFFICIAL_VIEW_URL
    from intern_daily_updater.form_extractor import extract_schema_from_url


def parse_date(date_str: str) -> Tuple[str, str, str]:
    """Parse YYYY-MM-DD or return today's parts."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"
    except Exception:
        today = datetime.date.today()
        return str(today.year), f"{today.month:02d}", f"{today.day:02d}"


def get_form_session_token(view_url: str, cookie: Optional[str] = None) -> Optional[str]:
    """Extract fbzx session token from the live form HTML."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        if cookie:
            headers["Cookie"] = cookie
        resp = requests.get(view_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            match = re.search(r'name="fbzx"\s+value="([^"]+)"', resp.text)
            if match:
                return match.group(1)
            match2 = re.search(r'"FB_PUBLIC_LOAD_DATA_"\s*,\s*\[.*?,"(-?\d{15,25})"', resp.text)
            if match2:
                return match2.group(1)
    except Exception:
        pass
    return None


def load_env_cookies(base_dir: Path) -> str:
    cookie = os.environ.get("GOOGLE_FORM_COOKIE", "").strip()
    if cookie:
        return cookie
    env_file = base_dir / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GOOGLE_FORM_COOKIE="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class FormSubmitter:
    def __init__(self, history_file: Optional[Path] = None, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent
        self.history_file = history_file or self.base_dir / "history.json"

    def load_history(self) -> Dict[str, Any]:
        """Load history data from history.json."""
        if not self.history_file.exists():
            return {"last_submission": None, "submissions": {}}
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_submission": None, "submissions": {}}

    def save_history(self, history: Dict[str, Any]):
        """Save history dictionary to history.json."""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def get_previous_tasks(self, before_date_str: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve the latest submitted tasks before before_date_str,
        plus a list of recent past submissions for context.
        """
        history = self.load_history()
        submissions = history.get("submissions", {})
        if not submissions:
            return "", []

        sorted_dates = sorted(submissions.keys())
        if before_date_str:
            eligible_dates = [d for d in sorted_dates if d < before_date_str]
        else:
            eligible_dates = sorted_dates

        if not eligible_dates:
            return "", []

        latest_date = eligible_dates[-1]
        latest_sub = submissions[latest_date]
        latest_today_tasks = latest_sub.get("tasks_today", "")

        recent_context = []
        for d in eligible_dates[-4:]:
            sub = submissions[d]
            recent_context.append({
                "date": d,
                "tasks_today": sub.get("tasks_today", ""),
                "challenges": sub.get("challenges", "None"),
            })

        return latest_today_tasks, recent_context

    def resolve_form_schema(self, config: Dict[str, Any], target: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve whether to use the Official Form or Test Form schema.
        Returns a dict containing endpoints, entry IDs, and page history.
        """
        active_target = target or config.get("active_target", "official")

        if active_target == "test":
            test_schema_file = self.base_dir / "test_form_schema.json"
            if test_schema_file.exists():
                try:
                    with open(test_schema_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass

            # Extract dynamically if file not present
            test_url = config.get("test_form_url")
            if test_url:
                schema = extract_schema_from_url(test_url)
                with open(test_schema_file, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2)
                return schema

        # Default: Official Form Schema
        return {
            "title": "Daily Intern Progress Update: LeapGen IIT Accelerator (Official)",
            "view_url": config.get("official_form_url", OFFICIAL_VIEW_URL),
            "submit_url": OFFICIAL_SUBMIT_URL,
            "email": OFFICIAL_ENTRIES["email"],
            "startup_name": OFFICIAL_ENTRIES["startup_name"],
            "intern_name": OFFICIAL_ENTRIES["intern_name"],
            "designation": OFFICIAL_ENTRIES["designation"],
            "today_date": OFFICIAL_ENTRIES["today_date"],
            "tasks_yesterday": OFFICIAL_ENTRIES["tasks_yesterday"],
            "tasks_today": OFFICIAL_ENTRIES["tasks_today"],
            "continuation": OFFICIAL_ENTRIES["continuation"],
            "status": OFFICIAL_ENTRIES["status"],
            "time_spent": OFFICIAL_ENTRIES["time_spent"],
            "completion_date": OFFICIAL_ENTRIES["completion_date"],
            "challenges": OFFICIAL_ENTRIES["challenges"],
            "page_history": "0,1",
        }

    def build_payload(
        self,
        config: Dict[str, Any],
        update_data: Dict[str, Any],
        submission_date_str: Optional[str] = None,
        target: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Convert config and generated update into Google Form POST data.
        Returns (payload, schema).
        """
        schema = self.resolve_form_schema(config, target=target)
        payload: Dict[str, Any] = {}

        # Email
        email_key = schema.get("email", "emailAddress")
        payload[email_key] = config.get("email", "")

        # Basic Info
        payload[schema["startup_name"]] = config.get("startup_name", "")
        payload[schema["intern_name"]] = config.get("intern_name", "")
        payload[schema["designation"]] = config.get("designation", "")

        # Form Date
        target_date = submission_date_str or datetime.date.today().strftime("%Y-%m-%d")
        year, month, day = parse_date(target_date)
        date_id = schema["today_date"]
        payload[f"{date_id}_year"] = year
        payload[f"{date_id}_month"] = month
        payload[f"{date_id}_day"] = day
        payload[date_id] = f"{year}-{month}-{day}"

        # Tasks text
        payload[schema["tasks_yesterday"]] = update_data.get("tasks_yesterday", "")
        payload[schema["tasks_today"]] = update_data.get("tasks_today", "")

        # Tasks breakdown (Tasks 1 to 4)
        task_items = update_data.get("task_items", [])
        cont_map = schema.get("continuation", {})
        status_map = schema.get("status", {})
        time_map = schema.get("time_spent", {})
        cdate_map = schema.get("completion_date", {})

        for i in range(1, 5):
            i_str = str(i)
            c_key = cont_map.get(i) or cont_map.get(i_str)
            s_key = status_map.get(i) or status_map.get(i_str)
            t_key = time_map.get(i) or time_map.get(i_str)
            d_key = cdate_map.get(i) or cdate_map.get(i_str)

            if i <= len(task_items):
                item = task_items[i - 1]
                if c_key:
                    payload[c_key] = item.get("continuation", "No")
                if s_key:
                    payload[s_key] = item.get("status", "Completed")
                if t_key:
                    payload[t_key] = str(item.get("time_spent", 3.0))
                if d_key:
                    c_date = item.get("completion_date", f"{year}-{month}-{day}")
                    c_year, c_month, c_day = parse_date(c_date)
                    payload[f"{d_key}_year"] = c_year
                    payload[f"{d_key}_month"] = c_month
                    payload[f"{d_key}_day"] = c_day
                    payload[d_key] = f"{c_year}-{c_month}-{c_day}"

        # Challenges
        if "challenges" in schema:
            payload[schema["challenges"]] = update_data.get("challenges", "None")

        # Hidden parameters for multi-page Google Forms
        payload["fvv"] = "1"
        payload["pageHistory"] = schema.get("page_history", "0,1")

        cookie = load_env_cookies(self.base_dir) or config.get("google_cookie", "")
        fbzx = get_form_session_token(schema.get("view_url", OFFICIAL_VIEW_URL), cookie=cookie)
        if fbzx:
            payload["fbzx"] = fbzx

        return payload, schema

    def submit_browser(
        self,
        config: Dict[str, Any],
        update_data: Dict[str, Any],
        submission_date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit via headless browser (Playwright) using verified Google session cookies."""
        import asyncio
        from playwright.async_api import async_playwright

        target_date = submission_date_str or datetime.date.today().strftime("%Y-%m-%d")
        cookie_str = load_env_cookies(self.base_dir) or config.get("google_cookie", "")
        view_url = "https://docs.google.com/forms/u/2/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/viewform?hl=en"

        async def _run_browser():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(locale="en-US")
                if cookie_str:
                    cookies = []
                    for pair in cookie_str.split("; "):
                        if "=" in pair:
                            name, val = pair.split("=", 1)
                            cookies.append({
                                "name": name.strip(),
                                "value": val.strip(),
                                "domain": ".google.com",
                                "path": "/",
                                "sameSite": "Lax",
                                "secure": True,
                            })
                    await context.add_cookies(cookies)

                page = await context.new_page()
                await page.goto(view_url, wait_until="networkidle")

                # Check for sign-in dialog or disabled form (expired cookie)
                dialog = page.locator("div[role='dialog']")
                has_dialog = await dialog.count() > 0
                listbox_0 = page.locator("div[role='listbox']").first
                is_disabled = (await listbox_0.get_attribute("aria-disabled")) == "true" if await listbox_0.count() > 0 else False

                if has_dialog or is_disabled:
                    await browser.close()
                    return "EXPIRED_COOKIE"

                # Check email consent checkbox if present (required by Google Forms)
                checkboxes = await page.locator("div[role='checkbox']").all()
                for cb in checkboxes:
                    if (await cb.get_attribute("aria-checked")) == "false":
                        await cb.click()
                        await page.wait_for_timeout(200)

                # Page 0: Startup and Intern Dropdowns
                dropdowns = await page.locator("div[role='listbox']").all()
                if len(dropdowns) >= 2:
                    await dropdowns[0].click()
                    await page.wait_for_timeout(300)
                    s_name = config.get("startup_name", "Clovio")
                    await page.locator("div[role='option']").filter(has_text=s_name).click()
                    await page.wait_for_timeout(200)

                    await dropdowns[1].click()
                    await page.wait_for_timeout(300)
                    i_name = config.get("intern_name", "Senith Sagarage")
                    await page.locator("div[role='option']").filter(has_text=i_name).click()
                    await page.wait_for_timeout(200)

                # Designation
                text_inputs = await page.locator("input[type='text']:visible").all()
                if text_inputs:
                    await text_inputs[0].fill(config.get("designation", "Full Stack Developer"))

                # Date
                date_inputs_p0 = await page.locator("input[type='date']:visible").all()
                if date_inputs_p0:
                    await date_inputs_p0[0].fill(target_date)

                # Click Next
                next_btn = page.locator("div[role='button']").filter(has_text=re.compile(r"^(Next|ඉදිරියට)$", re.I))
                await next_btn.click()
                await page.wait_for_timeout(2000)

                # Page 1: Tasks
                textareas = await page.locator("textarea:visible").all()
                if len(textareas) >= 2:
                    await textareas[0].fill(update_data.get("tasks_yesterday", ""))
                    await textareas[1].fill(update_data.get("tasks_today", ""))
                if len(textareas) >= 3:
                    await textareas[2].fill(update_data.get("challenges", "None"))

                # Continuation & Status Radios
                task_items = update_data.get("task_items", [])
                for idx in range(1, len(task_items) + 1):
                    item = task_items[idx - 1]
                    cont = item.get("continuation", "No")
                    status = item.get("status", "Completed")
                    t_label = f"Task {idx} " if idx == 1 else f"Task {idx}"
                    r_cont = page.locator(f"div[role='radio'][aria-label^='{cont}, response for {t_label}']")
                    if await r_cont.count() > 0:
                        await r_cont.click()
                    r_status = page.locator(f"div[role='radio'][aria-label^='{status}, response for Task {idx}']")
                    if await r_status.count() > 0:
                        await r_status.click()

                # Hours and Dates
                hours_inputs = await page.locator("input[type='text']:visible").all()
                date_inputs = await page.locator("input[type='date']:visible").all()
                for idx in range(len(task_items)):
                    item = task_items[idx]
                    if idx < len(hours_inputs):
                        await hours_inputs[idx].fill(str(item.get("time_spent", 2.5)))
                    if idx < len(date_inputs):
                        c_date = item.get("completion_date", target_date)
                        await date_inputs[idx].fill(c_date)

                # Submit
                submit_btn = page.locator("div[role='button']").filter(has_text=re.compile(r"^(Submit|යොමු කරන්න)$", re.I))
                await submit_btn.click()
                await page.wait_for_timeout(3000)

                final_html = await page.content()
                success = ("Your response has been recorded" in final_html or 
                           "Thank you for your response" in final_html)
                await browser.close()
                return success

        try:
            res = asyncio.run(_run_browser())
            if res == "EXPIRED_COOKIE":
                return {
                    "success": False,
                    "dry_run": False,
                    "status_code": 401,
                    "target_form": "LeapGen Official Form",
                    "message": (
                        "Google Session Cookie Expired!\n"
                        "Google displayed a 'Sign in to continue' modal.\n"
                        "To refresh your session:\n"
                        "  1. Open Chrome with senith.20231705@iit.ac.lk\n"
                        "  2. Refresh the LeapGen form page (F5)\n"
                        "  3. Press F12 -> Network tab -> click 'viewform' -> copy 'Cookie' request header\n"
                        "  4. Run: python intern_daily_updater\\run.py --set-cookie \"<cookie>\"\n"
                        "  5. In this terminal prompt, press [R] to retry immediately!"
                    ),
                }
            elif res is True:
                self.record_history(update_data, submission_date_str=target_date)
                return {
                    "success": True,
                    "dry_run": False,
                    "status_code": 200,
                    "target_form": "LeapGen Official Form",
                    "message": f"Successfully submitted to LeapGen Official Form for {target_date}!",
                }
            else:
                return {
                    "success": False,
                    "dry_run": False,
                    "status_code": 400,
                    "target_form": "LeapGen Official Form",
                    "message": "Browser submission did not reach confirmation page.",
                }
        except Exception as e:
            return {
                "success": False,
                "dry_run": False,
                "status_code": None,
                "target_form": "LeapGen Official Form",
                "message": f"Browser submission error: {e}",
            }

    def submit(
        self,
        config: Dict[str, Any],
        update_data: Dict[str, Any],
        submission_date_str: Optional[str] = None,
        target: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Submit the payload to Google Form or perform a dry-run test."""
        active_target = target or config.get("active_target", "test")
        target_date = submission_date_str or datetime.date.today().strftime("%Y-%m-%d")

        if dry_run:
            payload, schema = self.build_payload(
                config, update_data, submission_date_str=submission_date_str, target=target
            )
            return {
                "success": True,
                "dry_run": True,
                "status_code": 200,
                "target_form": schema.get("title", "Google Form"),
                "submit_url": schema.get("submit_url", OFFICIAL_SUBMIT_URL),
                "message": f"Dry-run successful for date {target_date} targeting '{schema.get('title')}'.",
                "payload": payload,
            }

        # For official form, use browser submission to handle Google Workspace multi-page authentication
        if active_target == "official":
            return self.submit_browser(config, update_data, submission_date_str=submission_date_str)

        # For test form or fallback, use HTTP POST
        payload, schema = self.build_payload(
            config, update_data, submission_date_str=submission_date_str, target=target
        )
        submit_url = schema.get("submit_url", OFFICIAL_SUBMIT_URL)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": schema.get("view_url", OFFICIAL_VIEW_URL),
        }
        cookie = load_env_cookies(self.base_dir) or config.get("google_cookie", "")
        if cookie:
            headers["Cookie"] = cookie

        try:
            res = requests.post(submit_url, data=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                self.record_history(update_data, submission_date_str=target_date)
                return {
                    "success": True,
                    "dry_run": False,
                    "status_code": res.status_code,
                    "target_form": schema.get("title", "Google Form"),
                    "message": f"Successfully submitted to '{schema.get('title')}' for {target_date}!",
                }
            else:
                return {
                    "success": False,
                    "dry_run": False,
                    "status_code": res.status_code,
                    "target_form": schema.get("title", "Google Form"),
                    "message": f"Submission returned status code {res.status_code}",
                }
        except Exception as e:
            return {
                "success": False,
                "dry_run": False,
                "status_code": None,
                "target_form": schema.get("title", "Google Form"),
                "message": f"Network/HTTP error: {e}",
            }

    def record_history(self, update_data: Dict[str, Any], submission_date_str: Optional[str] = None):
        """Save submitted update into history.json."""
        date_str = submission_date_str or datetime.date.today().strftime("%Y-%m-%d")
        history = self.load_history()

        record = {
            "date": date_str,
            "tasks_yesterday": update_data.get("tasks_yesterday", ""),
            "tasks_today": update_data.get("tasks_today", ""),
            "task_items": update_data.get("task_items", []),
            "challenges": update_data.get("challenges", ""),
        }

        if "submissions" not in history:
            history["submissions"] = {}
        history["submissions"][date_str] = record

        all_dates = sorted(history["submissions"].keys())
        history["last_submission"] = history["submissions"][all_dates[-1]]

        self.save_history(history)
