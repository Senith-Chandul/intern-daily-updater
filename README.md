# LeapGen IIT Accelerator: Daily Intern Progress Update Tool

Automated tool to synthesize professional, plausible daily intern progress reports using Google Gemini API, review and adjust them interactively, and submit them directly to the [Daily Intern Progress Update Google Form](https://docs.google.com/forms/d/e/1FAIpQLSclwYWri8MXXTa9wHDyn3fuBopn33F-eyi_Oi2aF7WUJCRE_g/viewform).

---

## Features

1. **Automatic Plausible Progress Generation**:
   - Uses Google Gemini API (`gemini-2.5-flash` or `gemini-1.5-flash`).
   - Learns your startup's context from `context.txt`.
   - Synthesizes realistic engineering tasks formatted strictly as:
     ```
     1. Project_the_task_belongs_to : Details_of_Task_1
     2. Project_the_task_belongs_to : Details_of_Task_2
     ```
2. **Direction Control**:
   - You can supply an optional direction or focus area (e.g. *"fixing redis caching"*, *"frontend navbar responsiveness"*, or press Enter to let Gemini invent plausible progress).
3. **Strict Hour Enforcement (6 to 9 Hours)**:
   - Total hours spent across tasks are guaranteed to sum to between **6.0 and 9.0 hours**.
4. **History Tracking for Next-Day Continuity**:
   - Submissions are logged in `history.json`.
   - The next day you run the tool, yesterday's tasks are automatically loaded from yesterday's submission, ensuring consistent progress tracking across consecutive days without duplicate typing!
5. **Interactive Review & Edit**:
   - View a clean preview of all fields before anything is submitted.
   - One-key submit (`[S]`), regenerate with a modified direction (`[R]`), edit fields (`[E]`), or dry-run without sending.

---

## Quick Setup (Zero-Config, Self-Prompting)

No manual file editing is required! When you run the tool for the first time, it automatically prompts you for everything it needs and saves it securely to `.env` and `config.json`:

1. **Google Gemini API Key**:
   - Prompts for your key (free in 30 seconds at [Google AI Studio](https://aistudio.google.com/app/apikey)).
   - Automatically tests and verifies the key with Google's API before saving.
2. **Google Form Session Cookie**:
   - Enables authorized submissions to the official LeapGen Google Form without typing your Google password.
   - Includes a step-by-step 20-second copy guide.
   - If the cookie expires at any point during catch-up, the tool catches it and prompts you for a new one without losing your work!
3. **Startup & Intern Profile**:
   - Offers number-choice selection from the official **8 LeapGen Startups** (*Yamu Car Rentals, Trivista Labs, The Astryd Labs, QuickBrix, Axacrate Technologies, Alertrix, Dectave, Clovio*).
   - Offers number-choice selection from the official **18 LeapGen Intern Names**.
4. **💡 Instant Fast-Track (Paste Confirmation Emails)**:
   - If you have past Google Form confirmation emails in your Gmail inbox, paste them directly into the tool (CLI or Web Studio). Gemini will automatically extract your name, startup, and past submissions into `history.json`!

To re-run the setup at any time:
```bash
python run.py --setup
```
Or use the **"Keys & Profile"** button in the Web GUI.

---

## Usage

### 🚀 Option A: Google Material 3 Web GUI Studio (Recommended)
Launch the local browser workspace:
```bash
python run.py --gui
```
- **Visual Weekday Timeline**: See all missing and submitted dates at a glance.
- **Material 3 Cards**: Edit individual tasks, statuses, continuation flags, and hours with real-time progress bar.
- **Auto-Balance**: Rebalance hours across tasks to the required 7.5h standard with one click.
- **Keys & Profile Manager**: Test Gemini keys live and update session cookies right in the browser.

### 💻 Option B: Interactive CLI
```bash
python run.py
```
1. It prompts you for an optional direction (e.g., *"working on user auth & JWT"* or press Enter for automatic).
2. Gemini drafts the update.
3. The Review screen appears:
   - Press **`S`** to submit immediately to Google Form!
   - Press **`R`** to regenerate if you want to change direction.
   - Press **`E`** to manually edit yesterday's or today's tasks.
   - Press **`Q`** to cancel.

### 2. Backfill Backed-Up / Past Days
If you have past days you haven't submitted yet:
```bash
python run.py --date 2026-09-05
```
Gemini will generate plausible progress for that date, connect with the previous day's tasks, submit it to Google Forms with the date `2026-09-05`, and save it in history.
Then run the next day:
```bash
python run.py --date 2026-09-06
```
and it will automatically carry over the previous day's tasks into yesterday's!

### 3. Days with a LeapGen Accelerator Session
On days where you had a 3-hour LeapGen workshop, lecture, or mentoring session:
```bash
# Interactive prompt will ask: "Was there a 3-hour LeapGen session/workshop today? (y/N or enter topic)"
python run.py

# Or pass the session flag via command-line:
python run.py --session "Startup Valuation and Pitch Deck Review"

# Or just flag that there was a session (uses default accelerator topic):
python run.py --session
```
*When a session is indicated, the tool automatically fixes Task 1 to the 3-hour LeapGen session (3.0h) and generates fewer project tasks (total 2 to 3 tasks for the day).*
*On normal days without a session, the tool generates **3 or 4 tasks** (rarely 2).*

### 4. Record Manually Submitted Past Updates
If you already submitted forms in the past manually and want Gemini to know about them:
```bash
python run.py --add-history
```
Prompts you for the date, yesterday's tasks, and today's tasks, and records them into `history.json` without re-submitting to the Google Form.

### 5. View Recorded History
```bash
python run.py --list-history
```

### 6. Supply Direction Directly
```bash
python run.py --direction "fixed the mobile navigation and added t-shirt cards"
```

### 7. Dry-Run Mode (Test without Submitting)
```bash
python run.py --dry-run
```

### 8. Automated Run (For Cron/Task Scheduler)
```bash
python run.py --auto
```

---

## File Structure

- `.env` - Paste your `GEMINI_API_KEY` here.
- `config.json` - Profile defaults (Startup, Intern Name, Designation, Email).
- `context.txt` - Project notes & tech stack fed to Gemini.
- `history.json` - Log of submissions (automatically supplies yesterday's tasks).
- `form_schema.py` - Exact Google Form entry IDs and dropdown values.
- `gemini_generator.py` - Calls Gemini REST API and enforces 6–9 hours rule.
- `form_submitter.py` - Builds URL-encoded payload and posts to Google Form.
- `run.py` - Main interactive CLI entrypoint.
- `test_workflow.py` - Automated component verification tests.
