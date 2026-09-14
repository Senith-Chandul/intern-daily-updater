"""
Gemini generator module for LeapGen Intern Progress Updates.
Calls Google Gemini API to synthesize realistic, professional progress reports
conforming strictly to LeapGen IIT Accelerator Google Form requirements.
"""

import datetime
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Parse a simple .env file into key-value pairs."""
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return env_vars


def get_api_key(base_dir: Path) -> str:
    """Retrieve Gemini API key from environment variable or local .env file."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key and api_key != "your_gemini_api_key_here":
        return api_key

    # Check .env in base directory
    env_vars = load_env_file(base_dir / ".env")
    key = env_vars.get("GEMINI_API_KEY", "").strip()
    if key and key != "your_gemini_api_key_here":
        return key

    return ""


def clean_json_response(text: str) -> str:
    """Extract JSON object substring from raw model output."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def validate_and_normalize_hours(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure the sum of hours across all tasks is strictly between 6.0 and 9.0 hours.
    Preserves 3.0h for LeapGen accelerator session tasks and balances the remaining tasks.
    """
    if not tasks:
        return tasks

    total = sum(float(t.get("time_spent", 0.0)) for t in tasks)
    target_total = 7.5  # safe midpoint between 6.0 and 9.0

    if total < 6.0 or total > 9.0:
        # Check if there is an accelerator session task (fixed at 3.0h)
        session_indices = [
            i for i, t in enumerate(tasks)
            if any(kw in t.get("title", "").lower() for kw in ["session", "lecture", "workshop", "leapgen : attended"])
        ]

        if session_indices and len(tasks) > len(session_indices):
            for idx in session_indices:
                tasks[idx]["time_spent"] = 3.0

            fixed_hours = sum(tasks[idx]["time_spent"] for idx in session_indices)
            remaining_target = max(target_total - fixed_hours, 3.0)
            other_indices = [i for i in range(len(tasks)) if i not in session_indices]
            other_sum = sum(float(tasks[i].get("time_spent", 0.0)) for i in other_indices)

            if other_sum <= 0:
                per_other = round(remaining_target / len(other_indices), 1)
                for i in other_indices:
                    tasks[i]["time_spent"] = per_other
            else:
                scale = remaining_target / other_sum
                curr_rem = 0.0
                for i in other_indices:
                    tasks[i]["time_spent"] = max(round(float(tasks[i].get("time_spent", 0.0)) * scale, 1), 1.0)
                    curr_rem += tasks[i]["time_spent"]
                tasks[other_indices[0]]["time_spent"] = round(tasks[other_indices[0]]["time_spent"] + (remaining_target - curr_rem), 1)
        else:
            if total <= 0:
                per_task = round(target_total / len(tasks), 1)
                for t in tasks:
                    t["time_spent"] = per_task
            else:
                scale = target_total / total
                new_total = 0.0
                for i, t in enumerate(tasks):
                    scaled = round(float(t.get("time_spent", 0.0)) * scale, 1)
                    t["time_spent"] = max(scaled, 1.0)
                    new_total += t["time_spent"]
                tasks[0]["time_spent"] = round(tasks[0]["time_spent"] + (target_total - new_total), 1)

    return tasks


class GeminiProgressGenerator:
    def __init__(self, base_dir: Optional[Path] = None, model: str = "gemini-flash-latest"):
        self.base_dir = base_dir or Path(__file__).parent
        self.model = model
        self.api_key = get_api_key(self.base_dir)

    def _call_gemini_api(self, prompt: str, candidate_models: List[str]) -> Dict[str, Any]:
        """Try calling models in sequence until one succeeds."""
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.75,
                "responseMimeType": "application/json",
            }
        }

        last_err = ""
        for mod in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 200:
                    res_json = resp.json()
                    parts = res_json["candidates"][0]["content"]["parts"]
                    text_parts = [p["text"] for p in parts if "text" in p]
                    raw_text = "\n".join(text_parts)
                    cleaned = clean_json_response(raw_text)
                    return json.loads(cleaned)
                else:
                    last_err = f"{mod} (HTTP {resp.status_code}): {resp.text}"
            except Exception as e:
                last_err = f"{mod} exception: {e}"

        raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")

    def generate_update(
        self,
        project_name: str,
        context_notes: str = "",
        yesterday_submitted_tasks: Optional[str] = None,
        recent_history_context: Optional[List[Dict[str, Any]]] = None,
        direction: str = "",
        today_date_str: Optional[str] = None,
        leapgen_session: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate form update JSON using Gemini.
        Supports leapgen_session (3-hour accelerator lecture/workshop) and generates 3-4 tasks on normal days.
        """
        if not self.api_key:
            raise ValueError(
                "Gemini API Key not found!\n"
                "Please add your GEMINI_API_KEY to 'intern_daily_updater/.env' "
                "or set it as an environment variable."
            )

        today_dt = datetime.date.today()
        if today_date_str:
            try:
                today_dt = datetime.datetime.strptime(today_date_str, "%Y-%m-%d").date()
            except Exception:
                pass

        yesterday_dt = today_dt - datetime.timedelta(days=1 if today_dt.weekday() != 0 else 3)
        today_str = today_dt.strftime("%Y-%m-%d")
        yesterday_str = yesterday_dt.strftime("%Y-%m-%d")

        has_session = bool(leapgen_session and str(leapgen_session).strip().lower() not in ["n", "no", "false"])

        system_instruction = (
            "You are an assistant helping a university student / intern (Senith, Full Stack Developer at startup Clovio) "
            "write their daily progress update for the LeapGen IIT Accelerator Google Form.\n\n"
            "CRITICAL WRITING STYLE RULES (HUMANIZE & SIMPLIFY):\n"
            "1. TONE: Write like a real human student intern speaking naturally, NOT like an AI, corporate PR statement, or executive.\n"
            "2. SIMPLE ACTION VERBS: Start tasks with simple, natural everyday verbs: 'Worked on', 'Fixed', 'Added', 'Created', 'Updated', 'Finished', 'Tested', 'Researched', 'Met with', 'Designed', 'Looked into'.\n"
            "3. BANNED AI / ROBOTIC BUZZWORDS: Absolutely NEVER use words like:\n"
            "   - 'spearheaded', 'orchestrated', 'fine-tuned', 'leveraged', 'facilitated', 'seamlessly integrated'\n"
            "   - 'robust', 'holistic', 'meticulously', 'state-of-the-art', 'calibrated', 'comprehensive evaluation'\n"
            "   - 'paradigms', 'heterogeneous', 'architected', 'scalable synergies', 'pioneered', 'conformance', 'endeavors'.\n"
            "4. NATURAL DESCRIPTIONS: Keep descriptions simple, clear, and grounded in realistic day-to-day student intern work:\n"
            "   - GOOD HUMAN EXAMPLE: 'Worked on fixing the navbar on mobile screens and tested it on different browsers.'\n"
            "   - BAD AI EXAMPLE: 'Architected responsive navigation paradigms and fine-tuned cross-viewport styling heuristics.'\n"
            "   - GOOD HUMAN EXAMPLE: 'Met with the print shop in Pettah to inspect the first sample mug and check the print quality.'\n"
            "   - BAD AI EXAMPLE: 'Conducted empirical quality evaluation of ceramic substrates against RGB-to-CMYK color space calibrations.'\n"
            "5. AUTHENTIC CHALLENGES:\n"
            "   - Most days challenges should simply be 'None' or 'No major blockers today.'\n"
            "   - If there is a challenge, phrase it like an actual human: e.g., 'Had an issue where images were loading slowly on mobile, so compressed the files.' or 'The print shop had a delay with their heat press machine so had to wait until the afternoon to collect the sample.' Never write robotic academic sentences for challenges.\n"
            "6. TASK COUNT & DIVERSITY RULES:\n"
            "- ON NORMAL DAYS (no LeapGen accelerator session):\n"
            "  * Generate 3 or 4 distinct tasks for today (aim for 3 or 4; rarely 2).\n"
            "  * If a user gives a direction (e.g. 'fixed the ui'), use that direction for 1 or 2 tasks, but ALWAYS add 1 or 2 other realistic tasks from past work/modules (merchandise designs, print supplier checks, Instagram updates, student surveys, or testing) so the day is complete and realistic.\n"
            "  * Total hours across today's tasks MUST sum to between 6.0 and 9.0 hours (typically 7.0 to 8.0 hrs, e.g. 2.0h, 2.0h, 2.0h, 1.5h).\n"
            "- ON DAYS WITH A LEAPGEN ACCELERATOR SESSION:\n"
            "  * A 3-hour LeapGen session/workshop/lecture took place today.\n"
            "  * Task 1 MUST be the session: '1. LeapGen : Attended a 3-hour lecture/workshop on <Topic>'.\n"
            "  * Time spent on the session task MUST be 3.0 hours (status: 'Completed', continuation: 'No').\n"
            "  * Because the session takes 3 hours, provide FEWER tasks today: generate a total of 2 to 3 tasks for the whole day (1 LeapGen session of 3.0h + 1 or 2 project tasks of ~2.0h-2.5h each), summing to 7.0 - 8.0 hours.\n"
            "7. FORMAT REQUIREMENTS:\n"
            "- 'tasks_yesterday' MUST follow the format:\n"
            "  1. Project_Name : Plain natural task description\n"
            "  2. Project_Name : Plain natural task description\n"
            "- 'tasks_today' MUST follow the format:\n"
            "  1. Project_Name : Plain natural task description\n"
            "  2. Project_Name : Plain natural task description\n"
            "- Valid Project_Names: 'LeapGen_Business', 'LeapGen', 'Aurora_Competition', or 'Clovio'.\n"
            "- For each task item in 'task_items':\n"
            "  - 'title': A short, simple human title (e.g. 'Attended LeapGen lecture on marketing', 'Fixed mobile navbar styling', 'Tested mug sample with printer', 'Added product cards to website')\n"
            "  - 'continuation': 'Yes' if continuing previous work, otherwise 'No'\n"
            "  - 'status': 'Completed' or 'In progress'\n"
            "  - 'time_spent': decimal hours (e.g. 3.0, 2.0, 2.5). Sum MUST be between 6.0 and 9.0 hours.\n"
            "  - 'completion_date': Date string YYYY-MM-DD\n"
        )

        user_prompt_parts = [
            f"Project Name: {project_name}",
            f"Submission / Today's Date: {today_str}",
            f"Previous Work Day's Date: {yesterday_str}",
        ]

        if context_notes:
            user_prompt_parts.append(f"Context & Project Background:\n{context_notes.strip()}")

        if recent_history_context:
            history_lines = ["Recent Chronological Work History (Build logically on this; do NOT duplicate completed items):"]
            for h in recent_history_context:
                history_lines.append(f"- Date {h.get('date')}:\n  {h.get('tasks_today', '').strip()}")
            user_prompt_parts.append("\n".join(history_lines))

        if yesterday_submitted_tasks:
            user_prompt_parts.append(
                f"Previous Day's Today Tasks (MUST BE USED/ALIGNED AS YESTERDAY'S TASKS FOR CONTINUITY):\n{yesterday_submitted_tasks.strip()}"
            )

        if direction:
            user_prompt_parts.append(f"Direction / Specific focus for this update:\n{direction.strip()}")
        else:
            user_prompt_parts.append("Direction: Generate simple, realistic, everyday progress continuing naturally from past work.")

        if has_session:
            topic = leapgen_session if (isinstance(leapgen_session, str) and leapgen_session.strip() and leapgen_session.strip().lower() not in ["y", "yes", "true", "default"]) else "Strategic Startup Operations & Mentoring"
            user_prompt_parts.append(
                f"LEAPGEN ACCELERATOR SESSION TODAY: YES.\n"
                f"- Task 1 MUST BE: '1. LeapGen : Attended a 3-hour lecture/workshop on \'{topic}\''.\n"
                f"- Task 1 time_spent: 3.0 hours, status: 'Completed', continuation: 'No'.\n"
                f"- Because this session took 3 hours, generate FEWER project tasks today: provide 2 to 3 tasks in total (1 LeapGen session + 1 or 2 project tasks), total hours between 6.0 and 9.0."
            )
        else:
            user_prompt_parts.append(
                "LEAPGEN ACCELERATOR SESSION TODAY: NO.\n"
                "- Provide 3 or 4 distinct tasks for today (aim for 3 or 4, rarely 2).\n"
                "- If a direction was given above, use it for 1-2 tasks and ALSO add 1-2 other realistic startup tasks (merchandise designs, print vendor followups, UI testing, surveys, or Instagram updates) to round out a full day."
            )

        user_prompt_parts.append(
            "\nReturn ONLY a valid JSON object with the following structure:\n"
            "{\n"
            '  "tasks_yesterday": "1. Project_Name : Task 1 description\\n2. Project_Name : Task 2 description",\n'
            '  "tasks_today": "1. Project_Name : Task 1 description\\n2. Project_Name : Task 2 description\\n3. Project_Name : Task 3 description",\n'
            '  "task_items": [\n'
            "    {\n"
            '      "task_number": 1,\n'
            '      "title": "Short title",\n'
            '      "continuation": "Yes",\n'
            '      "status": "In progress",\n'
            '      "time_spent": 2.5,\n'
            f'      "completion_date": "{today_str}"\n'
            "    },\n"
            "    {\n"
            '      "task_number": 2,\n'
            '      "title": "Short title",\n'
            '      "continuation": "No",\n'
            '      "status": "Completed",\n'
            '      "time_spent": 2.5,\n'
            f'      "completion_date": "{today_str}"\n'
            "    },\n"
            "    {\n"
            '      "task_number": 3,\n'
            '      "title": "Short title",\n'
            '      "continuation": "No",\n'
            '      "status": "Completed",\n'
            '      "time_spent": 2.5,\n'
            f'      "completion_date": "{today_str}"\n'
            "    }\n"
            "  ],\n"
            '  "challenges": "None"\n'
            "}"
        )

        prompt_body = "\n\n".join(user_prompt_parts)

        models_to_try = []
        for m in [self.model, "gemini-flash-latest", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.6-flash"]:
            if m and m not in models_to_try:
                models_to_try.append(m)

        full_prompt = system_instruction + "\n\n" + prompt_body
        data = self._call_gemini_api(full_prompt, models_to_try)

        # If previous tasks were provided and model changed them, preserve previous tasks unless empty
        if yesterday_submitted_tasks and not data.get("tasks_yesterday"):
            data["tasks_yesterday"] = yesterday_submitted_tasks

        # Normalize and validate total hours strictly between 6.0 and 9.0 hours
        if "task_items" in data:
            data["task_items"] = validate_and_normalize_hours(data["task_items"])

        return data
