"""
Google Form Schema Auto-Extractor.
Extracts all field entry IDs, options, and submission endpoints dynamically
from any Google Form URL.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional
import requests


ALL_DATA_FIELDS = "FB_PUBLIC_LOAD_DATA_"


def get_form_submit_url(view_url: str) -> str:
    """Convert viewform URL to formResponse URL."""
    url = view_url.split("?")[0].replace("/viewform", "/formResponse")
    if not url.endswith("/formResponse"):
        if not url.endswith("/"):
            url += "/"
        url += "formResponse"
    return url


def extract_fb_public_load_data(html: str) -> Optional[Any]:
    """Parse FB_PUBLIC_LOAD_DATA_ array from HTML string."""
    pattern = re.compile(r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', re.DOTALL)
    match = pattern.search(html)
    if not match:
        pattern2 = re.compile(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', re.DOTALL)
        match = pattern2.search(html)
        if not match:
            return None
    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def extract_schema_from_url(form_url: str) -> Dict[str, Any]:
    """
    Fetch and parse the exact entry mapping for LeapGen Daily Intern forms.
    Works for both the official form and custom test forms.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(form_url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch form HTML from {form_url} (HTTP {resp.status_code})")

    data = extract_fb_public_load_data(resp.text)
    if not data or len(data) < 2 or not data[1] or not data[1][1]:
        raise RuntimeError("Could not find or parse FB_PUBLIC_LOAD_DATA_ in the form HTML.")

    entries_raw = data[1][1]
    title = data[1][8] if len(data[1]) > 8 and data[1][8] else "Google Form"

    extracted: Dict[str, Any] = {
        "title": title,
        "view_url": form_url.split("?")[0],
        "submit_url": get_form_submit_url(form_url),
        "email": "emailAddress",
        "continuation": {},
        "status": {},
        "time_spent": {},
        "completion_date": {},
        "page_count": 1,
    }

    page_breaks = 0

    for item in entries_raw:
        item_id = item[0]
        label = item[1] or ""
        item_type = item[3]
        sub_items = item[4] if len(item) > 4 and item[4] else []

        # Type 8 is PageBreak
        if item_type == 8:
            page_breaks += 1
            continue

        label_lower = label.lower().strip()

        # Startup Name
        if "startup" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["startup_name"] = f"entry.{sub_items[0][0]}"

        # Intern Name
        elif "intern name" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["intern_name"] = f"entry.{sub_items[0][0]}"

        # Designation
        elif "designation" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["designation"] = f"entry.{sub_items[0][0]}"

        # Today's date
        elif "today's date" in label_lower or "today&#39;s date" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["today_date"] = f"entry.{sub_items[0][0]}"

        # Tasks yesterday
        elif "yesterday" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["tasks_yesterday"] = f"entry.{sub_items[0][0]}"

        # Tasks today
        elif "tasks i did today" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["tasks_today"] = f"entry.{sub_items[0][0]}"

        # Continuation Grid
        elif "continuation" in label_lower:
            for idx, sub in enumerate(sub_items, 1):
                extracted["continuation"][idx] = f"entry.{sub[0]}"

        # Status Grid
        elif "task status" in label_lower:
            for idx, sub in enumerate(sub_items, 1):
                extracted["status"][idx] = f"entry.{sub[0]}"

        # Time spent Task 1-4
        elif "time spent on today's task" in label_lower or "time spent on today&#39;s task" in label_lower:
            for t_num in range(1, 5):
                if f"task {t_num}" in label_lower:
                    if sub_items and len(sub_items[0]) > 0:
                        extracted["time_spent"][t_num] = f"entry.{sub_items[0][0]}"

        # Completion date Task 1-4
        elif "completion date" in label_lower:
            for t_num in range(1, 5):
                if f"task {t_num}" in label_lower:
                    if sub_items and len(sub_items[0]) > 0:
                        extracted["completion_date"][t_num] = f"entry.{sub_items[0][0]}"

        # Challenges
        elif "challenges" in label_lower or "problems" in label_lower:
            if sub_items and len(sub_items[0]) > 0:
                extracted["challenges"] = f"entry.{sub_items[0][0]}"

    extracted["page_count"] = page_breaks + 1
    extracted["page_history"] = ",".join(str(i) for i in range(extracted["page_count"]))

    return extracted


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://docs.google.com/forms/d/e/1FAIpQLSc9v7B37abD5zX8jzlM91ch4i83H7-mDDiCYZ6qqwoe06UxNQ/viewform"
    print(f"Extracting schema from: {test_url}")
    res = extract_schema_from_url(test_url)
    print("\n--- Extracted Schema ---")
    print(json.dumps(res, indent=2))
