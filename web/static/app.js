/**
 * LeapGen Intern Progress Studio - Frontend Logic (Google Material 3)
 * Handles reactive state, M3 chips, task breakdown synchronization, and form submission.
 */

// Application State
const state = {
  status: null,
  config: null,
  days: [],
  currentDate: null,
  currentDayStatus: 'pending',
  currentData: {
    tasks_today: '',
    tasks_yesterday: '',
    task_items: [],
    challenges: 'None',
  },
  generalPhase: 'Building Pettah print shop website and fulfilling custom mug orders',
  dayFocus: '',
  isWorkshop: false,
  workshopTopic: null,
  target: 'official',
  dryRun: false,
  isBusy: false,
};

// DOM Elements Cache
const elements = {
  internNameVal: document.getElementById('intern-name-val'),
  startupNameVal: document.getElementById('startup-name-val'),
  targetVal: document.getElementById('target-val'),
  targetToggleBtn: document.getElementById('target-toggle-btn'),
  historyCountBadge: document.getElementById('history-count-badge'),
  historyModalBtn: document.getElementById('history-modal-btn'),
  settingsModalBtn: document.getElementById('settings-modal-btn'),

  // Credentials & Setup Elements
  credentialsModalBtn: document.getElementById('credentials-modal-btn'),
  credentialsStatusIcon: document.getElementById('credentials-status-icon'),
  credentialsChipLabel: document.getElementById('credentials-chip-label'),
  credentialsModal: document.getElementById('credentials-modal'),
  closeCredentialsModalBtn: document.getElementById('close-credentials-modal-btn'),
  cancelCredentialsBtn: document.getElementById('cancel-credentials-btn'),
  saveCredentialsBtn: document.getElementById('save-credentials-btn'),
  setupGeminiKeyInput: document.getElementById('setup-gemini-key-input'),
  toggleKeyVisibilityBtn: document.getElementById('toggle-key-visibility-btn'),
  keyVisIcon: document.getElementById('key-vis-icon'),
  testGeminiKeyBtn: document.getElementById('test-gemini-key-btn'),
  geminiKeyStatusText: document.getElementById('gemini-key-status-text'),
  setupCookieInput: document.getElementById('setup-cookie-input'),
  setupStartupSelect: document.getElementById('setup-startup-select'),
  setupInternSelect: document.getElementById('setup-intern-select'),
  setupDesignationInput: document.getElementById('setup-designation-input'),
  setupEmailInput: document.getElementById('setup-email-input'),

  // Email Import Elements
  importEmailModalBtn: document.getElementById('import-email-modal-btn'),
  importEmailModal: document.getElementById('import-email-modal'),
  closeImportEmailModalBtn: document.getElementById('close-import-email-modal-btn'),
  cancelImportEmailBtn: document.getElementById('cancel-import-email-btn'),
  submitImportEmailBtn: document.getElementById('submit-import-email-btn'),
  doneImportEmailBtn: document.getElementById('done-import-email-btn'),
  importEmailTextarea: document.getElementById('import-email-textarea'),
  importEmailBtnText: document.getElementById('import-email-btn-text'),
  importEmailResultCard: document.getElementById('import-email-result-card'),
  importResultTitle: document.getElementById('import-result-title'),
  importResultSummary: document.getElementById('import-result-summary'),
  importResultDetails: document.getElementById('import-result-details'),
  shortcutImportEmailBtn: document.getElementById('shortcut-import-email-btn'),

  generalPhaseInput: document.getElementById('general-phase-input'),
  savePhaseBtn: document.getElementById('save-phase-btn'),

  timelineStrip: document.getElementById('timeline-strip'),
  statSubmittedCount: document.getElementById('stat-submitted-count'),
  statPendingCount: document.getElementById('stat-pending-count'),
  statAbsentCount: document.getElementById('stat-absent-count'),

  activeDateTitle: document.getElementById('active-date-title'),
  activeWeekdayBadge: document.getElementById('active-weekday-badge'),
  activeStatusBadge: document.getElementById('active-status-badge'),
  activeDayStatusDot: document.getElementById('active-day-status-dot'),
  activeDateSubtitle: document.getElementById('active-date-subtitle'),

  workshopToggleBtn: document.getElementById('workshop-toggle-btn'),
  workshopBtnLabel: document.getElementById('workshop-btn-label'),
  markAbsentBtn: document.getElementById('mark-absent-btn'),
  absentBtnLabel: document.getElementById('absent-btn-label'),
  generateAiBtn: document.getElementById('generate-ai-btn'),

  dayFocusInput: document.getElementById('day-focus-input'),
  tasksTodayInput: document.getElementById('tasks-today-input'),
  tasksYesterdayInput: document.getElementById('tasks-yesterday-input'),
  todayTaskLinesCount: document.getElementById('today-task-lines-count'),
  syncLinesToItemsBtn: document.getElementById('sync-lines-to-items-btn'),
  refillYesterdayBtn: document.getElementById('refill-yesterday-btn'),

  totalHoursValue: document.getElementById('total-hours-value'),
  hoursProgressBar: document.getElementById('hours-progress-bar'),
  taskCardsList: document.getElementById('task-cards-list'),
  addTaskCardBtn: document.getElementById('add-task-card-btn'),
  autobalanceHoursBtn: document.getElementById('autobalance-hours-btn'),

  challengesInput: document.getElementById('challenges-input'),

  submissionTargetLabel: document.getElementById('submission-target-label'),
  dryRunCheckbox: document.getElementById('dry-run-checkbox'),
  nextDayBtn: document.getElementById('next-day-btn'),
  submitFormBtn: document.getElementById('submit-form-btn'),
  submitBtnText: document.getElementById('submit-btn-text'),

  consoleDrawer: document.getElementById('console-drawer'),
  consoleHeaderHandle: document.getElementById('console-header-handle'),
  consoleStatusDot: document.getElementById('console-status-dot'),
  consoleStatusTitle: document.getElementById('console-status-title'),
  consoleLogs: document.getElementById('console-logs'),
  closeConsoleBtn: document.getElementById('close-console-btn'),

  historyModal: document.getElementById('history-modal'),
  closeHistoryModalBtn: document.getElementById('close-history-modal-btn'),
  historyList: document.getElementById('history-list'),

  settingsModal: document.getElementById('settings-modal'),
  closeSettingsModalBtn: document.getElementById('close-settings-modal-btn'),
  settingsTargetSelect: document.getElementById('settings-target-select'),
  settingsModelInput: document.getElementById('settings-model-input'),
  settingsContextTextarea: document.getElementById('settings-context-textarea'),
  saveSettingsBtn: document.getElementById('save-settings-btn'),

  toastContainer: document.getElementById('toast-container'),
};

// Material 3 Logging and Snackbars
function logMessage(msg, type = 'info') {
  const line = document.createElement('div');
  line.className = `log-line ${type}`;
  const time = new Date().toLocaleTimeString();
  line.textContent = `[${time}] ${msg}`;
  elements.consoleLogs.appendChild(line);
  elements.consoleLogs.scrollTop = elements.consoleLogs.scrollHeight;
}

function showSnackbar(message, type = 'info') {
  const snack = document.createElement('div');
  snack.className = `m3-snackbar ${type}`;
  snack.innerHTML = `
    <span class="material-symbols-outlined">${type === 'success' ? 'check_circle' : type === 'error' ? 'error' : 'info'}</span>
    <span>${message}</span>
  `;
  elements.toastContainer.appendChild(snack);
  setTimeout(() => {
    snack.style.opacity = '0';
    setTimeout(() => snack.remove(), 250);
  }, 3500);
}

function setBusy(isBusy, title = 'System Busy') {
  state.isBusy = isBusy;
  if (isBusy) {
    elements.consoleStatusDot.className = 'console-status-dot busy';
    elements.consoleStatusTitle.textContent = title;
    elements.submitFormBtn.disabled = true;
    elements.generateAiBtn.disabled = true;
  } else {
    elements.consoleStatusDot.className = 'console-status-dot';
    elements.consoleStatusTitle.textContent = 'System Ready';
    elements.submitFormBtn.disabled = false;
    elements.generateAiBtn.disabled = false;
  }
}

// API Calls
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    state.status = data;
    state.target = data.target || 'official';

    elements.internNameVal.textContent = data.intern_name;
    elements.startupNameVal.textContent = data.startup_name;
    elements.targetVal.textContent = state.target.toUpperCase();
    elements.submissionTargetLabel.textContent = `${state.target.toUpperCase()} Google Form`;
    elements.historyCountBadge.textContent = data.total_submitted;

    return data;
  } catch (err) {
    logMessage(`Error loading status: ${err.message}`, 'error');
  }
}

async function fetchDates() {
  try {
    const res = await fetch('/api/dates');
    const data = await res.json();
    state.days = data.days || [];
    renderTimeline();
    updateStatsCounters();

    // Select active date: First missing date, or today
    if (!state.currentDate) {
      const firstPending = state.days.find(d => d.status === 'pending');
      const targetDate = firstPending ? firstPending.date : (state.status?.today || state.days[state.days.length - 1]?.date);
      if (targetDate) {
        selectDate(targetDate);
      }
    }
  } catch (err) {
    logMessage(`Error loading dates: ${err.message}`, 'error');
  }
}

async function loadDayData(dateStr) {
  setBusy(true, `Loading ${dateStr}...`);
  try {
    const res = await fetch(`/api/day-data/${dateStr}`);
    const data = await res.json();

    if (data.found && data.data) {
      // Historical submission
      state.currentData = {
        tasks_today: data.data.tasks_today || '',
        tasks_yesterday: data.data.tasks_yesterday || '',
        task_items: data.data.task_items || [],
        challenges: data.data.challenges || 'None',
      };
      state.currentDayStatus = 'submitted';
      logMessage(`Loaded recorded submission for ${dateStr} from history.`, 'success');
    } else {
      // Draft mode
      state.currentData = {
        tasks_today: '',
        tasks_yesterday: data.previous_tasks || '',
        task_items: [],
        challenges: 'None',
      };
      const dayObj = state.days.find(d => d.date === dateStr);
      state.currentDayStatus = dayObj ? dayObj.status : 'pending';
      logMessage(`Prepared draft for ${dateStr}. Chained previous tasks.`);
    }

    renderActiveDayWorkspace();
  } catch (err) {
    logMessage(`Failed to load day data for ${dateStr}: ${err.message}`, 'error');
  } finally {
    setBusy(false);
  }
}

async function generateWithAI() {
  if (state.isBusy) return;
  setBusy(true, `Generating AI standup for ${state.currentDate}...`);
  logMessage(`Calling Gemini for ${state.currentDate} (Phase: '${state.generalPhase}', Focus: '${elements.dayFocusInput.value}')...`);

  try {
    const payload = {
      date: state.currentDate,
      direction: elements.dayFocusInput.value.trim(),
      general_direction: state.generalPhase.trim(),
      is_workshop: state.isWorkshop,
      workshop_topic: state.workshopTopic,
    };

    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Generation failed');
    }

    const result = await res.json();
    state.currentData = result.data;
    renderActiveDayWorkspace();
    logMessage(`Successfully generated standup for ${state.currentDate}!`, 'success');
    showSnackbar(`AI update generated for ${state.currentDate}!`, 'success');
  } catch (err) {
    logMessage(`Gemini generation error: ${err.message}`, 'error');
    showSnackbar(`AI generation failed: ${err.message}`, 'error');
    if (err.message && (err.message.includes('API key') || err.message.includes('GEMINI_API_KEY') || err.message.includes('API_KEY_INVALID'))) {
      checkCredentials(true);
    }
  } finally {
    setBusy(false);
  }
}

async function submitCurrentDay() {
  if (state.isBusy) return;

  saveFormInputsToState();

  const totalHours = calculateTotalHours();
  if (totalHours < 6.0 || totalHours > 9.0) {
    if (!confirm(`Total work hours is ${totalHours.toFixed(1)}h. Form standard is 6.0 to 9.0 hours. Do you want to auto-balance to 7.5h before submitting?`)) {
      return;
    }
    await autobalanceHours();
  }

  setBusy(true, `Submitting ${state.currentDate}...`);
  logMessage(`Initiating submission for ${state.currentDate} to [${state.target.toUpperCase()}] form...`);
  elements.submitBtnText.textContent = 'Submitting...';

  try {
    const payload = {
      date: state.currentDate,
      update_data: state.currentData,
      target: state.target,
      dry_run: elements.dryRunCheckbox.checked,
    };

    const res = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await res.json();

    if (result.success) {
      const prefix = result.dry_run ? '[DRY-RUN]' : '[SUCCESS]';
      logMessage(`${prefix} Submission successful for ${state.currentDate}!`, 'success');
      showSnackbar(`Submitted ${state.currentDate} successfully!`, 'success');

      if (!result.dry_run) {
        await fetchStatus();
        await fetchDates();
        selectNextDay();
      }
    } else {
      logMessage(`[FAILED] Submission failed for ${state.currentDate}: ${result.message}`, 'error');
      showSnackbar(`Submission failed: ${result.message}`, 'error');

      // Detect cookie / auth failure and auto-prompt credentials modal
      const msgLower = (result.message || '').toLowerCase();
      if (msgLower.includes('cookie') || msgLower.includes('401') || msgLower.includes('login') || msgLower.includes('permission') || msgLower.includes('auth')) {
        logMessage('Session cookie appears expired or unauthorized. Opening Credentials & Profile dialog...', 'warning');
        checkCredentials(true);
      }
    }
  } catch (err) {
    logMessage(`Network / Submitter exception: ${err.message}`, 'error');
    showSnackbar(`Error: ${err.message}`, 'error');
  } finally {
    setBusy(false);
    elements.submitBtnText.textContent = 'Submit to Google Form';
  }
}

async function toggleMarkAbsent() {
  if (!state.currentDate) return;

  const isCurrentlyAbsent = state.currentDayStatus === 'absent';
  const endpoint = isCurrentlyAbsent ? '/api/unmark-absent' : '/api/mark-absent';

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: state.currentDate }),
    });
    if (res.ok) {
      logMessage(`${isCurrentlyAbsent ? 'Unmarked' : 'Marked'} ${state.currentDate} as absent.`);
      await fetchStatus();
      await fetchDates();
      loadDayData(state.currentDate);
    }
  } catch (err) {
    logMessage(`Error changing absent status: ${err.message}`, 'error');
  }
}

// UI Rendering & Synchronization
function renderTimeline() {
  elements.timelineStrip.innerHTML = '';

  state.days.forEach(day => {
    const chip = document.createElement('div');
    chip.className = `m3-day-chip ${day.status}`;
    if (day.date === state.currentDate) {
      chip.classList.add('active');
    }

    chip.innerHTML = `
      <span class="chip-date">${day.date.slice(5)}</span>
      <span class="chip-weekday">${day.weekday.slice(0, 3)}</span>
    `;

    chip.addEventListener('click', () => selectDate(day.date));
    elements.timelineStrip.appendChild(chip);
  });
}

function updateStatsCounters() {
  const submitted = state.days.filter(d => d.status === 'submitted').length;
  const pending = state.days.filter(d => d.status === 'pending').length;
  const absent = state.days.filter(d => d.status === 'absent').length;

  elements.statSubmittedCount.textContent = submitted;
  elements.statPendingCount.textContent = pending;
  elements.statAbsentCount.textContent = absent;
}

function selectDate(dateStr) {
  state.currentDate = dateStr;
  const dayObj = state.days.find(d => d.date === dateStr);
  const weekday = dayObj ? dayObj.weekday : '';

  elements.activeDateTitle.textContent = dateStr;
  elements.activeWeekdayBadge.querySelector ? (elements.activeWeekdayBadge.textContent = weekday) : null;

  document.querySelectorAll('.m3-day-chip').forEach(c => {
    if (c.querySelector('.chip-date')?.textContent === dateStr.slice(5)) {
      c.classList.add('active');
      c.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    } else {
      c.classList.remove('active');
    }
  });

  loadDayData(dateStr);
}

function selectNextDay() {
  const currentIndex = state.days.findIndex(d => d.date === state.currentDate);
  if (currentIndex >= 0 && currentIndex < state.days.length - 1) {
    selectDate(state.days[currentIndex + 1].date);
  }
}

function renderActiveDayWorkspace() {
  const isSubmitted = state.currentDayStatus === 'submitted';
  const isAbsent = state.currentDayStatus === 'absent';

  // Badges & Subtitle
  elements.activeDayStatusDot.className = `date-indicator-circle ${state.currentDayStatus}`;
  elements.activeStatusBadge.className = `m3-badge-pill ${state.currentDayStatus}`;
  elements.activeStatusBadge.textContent = isSubmitted
    ? 'Submitted'
    : isAbsent
    ? 'Marked Absent'
    : 'Pending Catch-up';

  elements.activeDateSubtitle.textContent = isSubmitted
    ? 'Historical submission recorded in history.json'
    : 'Ready to review and submit daily progress';

  elements.absentBtnLabel.textContent = isAbsent ? 'Unmark Absent' : 'Mark Absent';

  // Reset workshop toggle
  state.isWorkshop = false;
  elements.workshopToggleBtn.classList.remove('active');
  elements.workshopBtnLabel.textContent = '+ Add Workshop (3h)';

  // Text inputs
  elements.tasksTodayInput.value = state.currentData.tasks_today || '';
  elements.tasksYesterdayInput.value = state.currentData.tasks_yesterday || '';
  elements.challengesInput.value = state.currentData.challenges || 'None';

  updateLineCounts();
  renderTaskCards();
  updateHoursMeter();
}

function updateLineCounts() {
  const todayLines = elements.tasksTodayInput.value.split('\n').filter(l => l.trim().length > 0);
  elements.todayTaskLinesCount.textContent = `${todayLines.length} tasks detected`;
}

function renderTaskCards() {
  elements.taskCardsList.innerHTML = '';
  const items = state.currentData.task_items || [];

  if (items.length === 0) {
    elements.taskCardsList.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--md-sys-color-outline); font-size: 0.875rem;">
        No task items yet. Click <strong>"Generate with AI"</strong> or <strong>"Add Task"</strong> to start.
      </div>
    `;
    return;
  }

  items.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'm3-task-item-card';

    card.innerHTML = `
      <div class="task-item-number-chip">${index + 1}</div>
      <div class="m3-text-field outlined-field dense">
        <input type="text" class="task-title-input" value="${escapeHtml(item.title || '')}" placeholder="Task title">
      </div>
      <div class="task-hours-group">
        <div class="m3-text-field outlined-field dense">
          <input type="number" step="0.5" min="0.5" max="9.0" class="task-hours-input" value="${item.time_spent || 2.5}">
        </div>
        <span class="m3-body-small text-muted">hrs</span>
      </div>
      <select class="m3-select status-select">
        <option value="Completed" ${item.status === 'Completed' ? 'selected' : ''}>Completed</option>
        <option value="In progress" ${item.status === 'In progress' ? 'selected' : ''}>In progress</option>
      </select>
      <select class="m3-select cont-select">
        <option value="No" ${item.continuation === 'No' ? 'selected' : ''}>New (No)</option>
        <option value="Yes" ${item.continuation === 'Yes' ? 'selected' : ''}>Cont. (Yes)</option>
      </select>
      <button class="m3-icon-button btn-xs delete-task-btn" title="Delete Task">
        <span class="material-symbols-outlined">delete</span>
      </button>
    `;

    // Listeners
    const titleInput = card.querySelector('.task-title-input');
    const hoursInput = card.querySelector('.task-hours-input');
    const statusSelect = card.querySelector('.status-select');
    const contSelect = card.querySelector('.cont-select');
    const deleteBtn = card.querySelector('.delete-task-btn');

    titleInput.addEventListener('input', (e) => { item.title = e.target.value; });
    hoursInput.addEventListener('input', (e) => {
      item.time_spent = parseFloat(e.target.value) || 0.0;
      updateHoursMeter();
    });
    statusSelect.addEventListener('change', (e) => { item.status = e.target.value; });
    contSelect.addEventListener('change', (e) => { item.continuation = e.target.value; });
    deleteBtn.addEventListener('click', () => {
      items.splice(index, 1);
      renderTaskCards();
      updateHoursMeter();
    });

    elements.taskCardsList.appendChild(card);
  });
}

function calculateTotalHours() {
  const items = state.currentData.task_items || [];
  return items.reduce((sum, item) => sum + (parseFloat(item.time_spent) || 0.0), 0.0);
}

function updateHoursMeter() {
  const total = calculateTotalHours();
  elements.totalHoursValue.textContent = `${total.toFixed(1)} hrs`;

  const pct = Math.min(Math.max((total / 12) * 100, 4), 100);
  elements.hoursProgressBar.style.width = `${pct}%`;

  if (total >= 6.0 && total <= 9.0) {
    elements.totalHoursValue.className = 'm3-title-large hours-display valid';
    elements.hoursProgressBar.className = 'm3-linear-progress-fill';
  } else if (total < 6.0) {
    elements.totalHoursValue.className = 'm3-title-large hours-display warning';
    elements.hoursProgressBar.className = 'm3-linear-progress-fill warning';
  } else {
    elements.totalHoursValue.className = 'm3-title-large hours-display danger';
    elements.hoursProgressBar.className = 'm3-linear-progress-fill warning';
  }
}

async function autobalanceHours() {
  const items = state.currentData.task_items || [];
  if (items.length === 0) return;

  try {
    const res = await fetch('/api/normalize-hours', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(items),
    });
    const data = await res.json();
    state.currentData.task_items = data.task_items;
    renderTaskCards();
    updateHoursMeter();
    showSnackbar(`Hours balanced to ${data.total.toFixed(1)} hrs!`, 'success');
  } catch (err) {
    logMessage(`Error auto-balancing hours: ${err.message}`, 'error');
  }
}

function syncLinesToItems() {
  const lines = elements.tasksTodayInput.value.split('\n').filter(l => l.trim().length > 0);
  if (lines.length === 0) {
    showSnackbar('No task lines found in textarea to sync', 'info');
    return;
  }

  const existing = state.currentData.task_items || [];
  const defaultHours = parseFloat((7.5 / lines.length).toFixed(1));

  const newItems = lines.map((line, i) => {
    let title = line.trim();
    if (title.includes(':')) {
      title = title.split(':', 2)[1].trim();
    } else {
      title = title.replace(/^\d+[\.\)]\s*/, '').trim();
    }

    if (i < existing.length) {
      return {
        ...existing[i],
        task_number: i + 1,
        title: title.slice(0, 70),
      };
    } else {
      return {
        task_number: i + 1,
        title: title.slice(0, 70),
        continuation: 'No',
        status: 'Completed',
        time_spent: defaultHours,
        completion_date: state.currentDate,
      };
    }
  });

  state.currentData.task_items = newItems;
  renderTaskCards();
  updateHoursMeter();
  showSnackbar('Synced textarea lines to breakdown cards!', 'success');
}

function saveFormInputsToState() {
  state.currentData.tasks_today = elements.tasksTodayInput.value;
  state.currentData.tasks_yesterday = elements.tasksYesterdayInput.value;
  state.currentData.challenges = elements.challengesInput.value || 'None';
}

function toggleTarget() {
  state.target = state.target === 'official' ? 'test' : 'official';
  elements.targetVal.textContent = state.target.toUpperCase();
  elements.submissionTargetLabel.textContent = `${state.target.toUpperCase()} Google Form`;
  logMessage(`Active submission target switched to: ${state.target.toUpperCase()}`);
  showSnackbar(`Switched target to ${state.target.toUpperCase()}`);
}

function toggleWorkshop() {
  state.isWorkshop = !state.isWorkshop;
  if (state.isWorkshop) {
    elements.workshopToggleBtn.classList.add('active');
    elements.workshopBtnLabel.textContent = 'Workshop (3.0h) Active';
    showSnackbar('3-hour LeapGen Accelerator Session enabled for next generation');
  } else {
    elements.workshopToggleBtn.classList.remove('active');
    elements.workshopBtnLabel.textContent = '+ Add Workshop (3h)';
  }
}

// History Modal
async function openHistoryModal() {
  elements.historyList.innerHTML = '<div class="text-muted" style="padding: 16px;">Loading history...</div>';
  elements.historyModal.classList.remove('hidden');

  try {
    const res = await fetch('/api/history');
    const hist = await res.json();
    const subs = hist.submissions || {};
    const dates = Object.keys(subs).sort().reverse();

    if (dates.length === 0) {
      elements.historyList.innerHTML = '<div style="padding: 16px;">No recorded submissions yet.</div>';
      return;
    }

    elements.historyList.innerHTML = dates.map(d => {
      const item = subs[d];
      return `
        <div class="history-entry-card">
          <div class="history-entry-header">
            <span class="history-entry-date">${d}</span>
            <button class="m3-button m3-button-outlined btn-dense load-history-day-btn" data-date="${d}">
              <span class="material-symbols-outlined" style="font-size: 16px;">visibility</span>
              <span>Inspect</span>
            </button>
          </div>
          <div class="history-entry-tasks">${escapeHtml(item.tasks_today || '')}</div>
        </div>
      `;
    }).join('');

    elements.historyList.querySelectorAll('.load-history-day-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const d = e.currentTarget.getAttribute('data-date');
        elements.historyModal.classList.add('hidden');
        selectDate(d);
      });
    });
  } catch (err) {
    elements.historyList.innerHTML = `<div>Error: ${err.message}</div>`;
  }
}

// Settings Modal
async function openSettingsModal() {
  elements.settingsModal.classList.remove('hidden');
  try {
    const [cfgRes, ctxRes] = await Promise.all([
      fetch('/api/config'),
      fetch('/api/context'),
    ]);
    const cfg = await cfgRes.json();
    const ctx = await ctxRes.json();

    state.config = cfg;
    elements.settingsTargetSelect.value = cfg.default_target || 'official';
    elements.settingsModelInput.value = cfg.gemini_model || 'gemini-3.6-flash';
    elements.settingsContextTextarea.value = ctx.context || '';
  } catch (err) {
    logMessage(`Error loading settings: ${err.message}`, 'error');
  }
}

async function saveSettings() {
  try {
    const newTarget = elements.settingsTargetSelect.value;
    const newModel = elements.settingsModelInput.value.trim();
    const newCtx = elements.settingsContextTextarea.value;

    const updatedConfig = {
      ...(state.config || {}),
      default_target: newTarget,
      gemini_model: newModel,
    };

    await Promise.all([
      fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: updatedConfig }),
      }),
      fetch('/api/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: newCtx }),
      }),
    ]);

    state.target = newTarget;
    elements.targetVal.textContent = state.target.toUpperCase();
    elements.submissionTargetLabel.textContent = `${state.target.toUpperCase()} Google Form`;

    elements.settingsModal.classList.add('hidden');
    showSnackbar('Settings & context saved successfully!', 'success');
  } catch (err) {
    showSnackbar(`Failed to save settings: ${err.message}`, 'error');
  }
}

// Credentials & Setup Modal
async function checkCredentials(forceOpen = false) {
  try {
    const res = await fetch('/api/credentials');
    const data = await res.json();

    // Populate startup select
    if (elements.setupStartupSelect && elements.setupStartupSelect.options.length <= 1) {
      elements.setupStartupSelect.innerHTML = '<option value="">-- Choose your LeapGen Startup --</option>';
      (data.startup_options || []).forEach(st => {
        const opt = document.createElement('option');
        opt.value = st;
        opt.textContent = st;
        elements.setupStartupSelect.appendChild(opt);
      });
    }

    // Populate intern select
    if (elements.setupInternSelect && elements.setupInternSelect.options.length <= 1) {
      elements.setupInternSelect.innerHTML = '<option value="">-- Select your Full Name --</option>';
      (data.intern_names || []).forEach(name => {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        elements.setupInternSelect.appendChild(opt);
      });
    }

    // Set current profile
    if (data.current_profile) {
      if (data.current_profile.startup_name) {
        elements.setupStartupSelect.value = data.current_profile.startup_name;
      }
      if (data.current_profile.intern_name) {
        elements.setupInternSelect.value = data.current_profile.intern_name;
      }
      elements.setupDesignationInput.value = data.current_profile.designation || 'Intern';
      elements.setupEmailInput.value = data.current_profile.email || '';
    }

    // Status texts & placeholders
    if (data.has_gemini_key) {
      elements.setupGeminiKeyInput.placeholder = `Active (${data.gemini_key_masked}). Paste new key to update.`;
      elements.geminiKeyStatusText.textContent = `Active Key: ${data.gemini_key_masked}`;
      elements.geminiKeyStatusText.style.color = '#81c784';
    } else {
      elements.setupGeminiKeyInput.placeholder = 'AIzaSy... (Paste your Gemini API key)';
      elements.geminiKeyStatusText.textContent = 'No Gemini API key configured yet.';
      elements.geminiKeyStatusText.style.color = '#ffb74d';
    }

    if (data.has_cookie) {
      elements.setupCookieInput.placeholder = `Active cookie saved (${data.cookie_masked}). Paste fresh cookie here to update.`;
    } else {
      elements.setupCookieInput.placeholder = 'Paste Google Form session cookie string here (S=...; COMPASS=...; etc.)...';
    }

    // Chip styling
    const allConfigured = data.has_gemini_key && data.has_cookie;
    if (allConfigured) {
      elements.credentialsStatusIcon.textContent = 'key';
      elements.credentialsStatusIcon.style.color = '#81c784';
      elements.credentialsChipLabel.textContent = 'Keys Active';
    } else {
      elements.credentialsStatusIcon.textContent = 'warning';
      elements.credentialsStatusIcon.style.color = '#ffb74d';
      elements.credentialsChipLabel.textContent = 'Setup Required';
    }

    if (forceOpen || !data.has_gemini_key) {
      elements.credentialsModal.classList.remove('hidden');
      if (!data.has_gemini_key) {
        showSnackbar('Welcome to LeapGen Intern Studio! Please set up your Gemini API Key & Profile.', 'info');
      }
    }

    return data;
  } catch (err) {
    logMessage(`Error checking credentials: ${err.message}`, 'error');
  }
}

function openCredentialsModal() {
  checkCredentials(true);
}

function closeCredentialsModal() {
  elements.credentialsModal.classList.add('hidden');
}

function toggleKeyVisibility() {
  if (elements.setupGeminiKeyInput.type === 'password') {
    elements.setupGeminiKeyInput.type = 'text';
    elements.keyVisIcon.textContent = 'visibility_off';
  } else {
    elements.setupGeminiKeyInput.type = 'password';
    elements.keyVisIcon.textContent = 'visibility';
  }
}

async function testGeminiKey() {
  const key = elements.setupGeminiKeyInput.value.trim();
  elements.geminiKeyStatusText.textContent = 'Verifying key with Google Gemini API...';
  elements.geminiKeyStatusText.style.color = 'var(--md-sys-color-on-surface-variant)';
  elements.testGeminiKeyBtn.disabled = true;

  try {
    const res = await fetch('/api/test-gemini-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gemini_api_key: key }),
    });
    const result = await res.json();
    if (result.success) {
      elements.geminiKeyStatusText.textContent = `✓ ${result.message}`;
      elements.geminiKeyStatusText.style.color = '#81c784';
      showSnackbar('Gemini API key is verified and working!', 'success');
    } else {
      elements.geminiKeyStatusText.textContent = `✗ ${result.message}`;
      elements.geminiKeyStatusText.style.color = '#e57373';
      showSnackbar(`Key verification failed: ${result.message}`, 'error');
    }
  } catch (err) {
    elements.geminiKeyStatusText.textContent = `✗ Error: ${err.message}`;
    elements.geminiKeyStatusText.style.color = '#e57373';
  } finally {
    elements.testGeminiKeyBtn.disabled = false;
  }
}

async function saveCredentials() {
  const key = elements.setupGeminiKeyInput.value.trim();
  const cookie = elements.setupCookieInput.value.trim();
  const startup = elements.setupStartupSelect.value;
  const intern = elements.setupInternSelect.value;
  const desig = elements.setupDesignationInput.value.trim();
  const email = elements.setupEmailInput.value.trim();

  elements.saveCredentialsBtn.disabled = true;
  elements.saveCredentialsBtn.textContent = 'Saving...';

  try {
    const payload = {
      gemini_api_key: key || null,
      google_form_cookie: cookie || null,
      startup_name: startup || null,
      intern_name: intern || null,
      designation: desig || null,
      email: email || null,
    };

    const res = await fetch('/api/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (data.success) {
      showSnackbar('Setup saved successfully!', 'success');
      elements.credentialsModal.classList.add('hidden');
      await fetchStatus();
      await checkCredentials(false);
    } else {
      showSnackbar(`Failed to save setup: ${data.message || 'Unknown error'}`, 'error');
    }
  } catch (err) {
    showSnackbar(`Error saving setup: ${err.message}`, 'error');
  } finally {
    elements.saveCredentialsBtn.disabled = false;
    elements.saveCredentialsBtn.textContent = 'Save & Continue';
  }
}

// Email Import Modal
function openImportEmailModal() {
  elements.importEmailModal.classList.remove('hidden');
  elements.importEmailResultCard.classList.add('hidden');
  elements.doneImportEmailBtn.classList.add('hidden');
  elements.submitImportEmailBtn.classList.remove('hidden');
  elements.importEmailTextarea.focus();
}

function closeImportEmailModal() {
  elements.importEmailModal.classList.add('hidden');
}

async function submitImportEmail() {
  const rawText = elements.importEmailTextarea.value.trim();
  if (!rawText) {
    showSnackbar('Please paste your confirmation email text before importing.', 'error');
    return;
  }

  elements.submitImportEmailBtn.disabled = true;
  elements.importEmailBtnText.textContent = 'Parsing with Gemini AI...';
  logMessage('Sending confirmation email text to Gemini AI for parsing and auto-fill...');

  try {
    const res = await fetch('/api/import-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to parse confirmation email');
    }

    const data = await res.json();
    const prof = data.profile || {};
    const dates = data.imported_dates || [];

    // Update Result Preview Card
    elements.importResultTitle.textContent = `Imported ${dates.length} Submission(s) Successfully!`;
    elements.importResultSummary.textContent = `Profile and history have been automatically configured.`;
    elements.importResultDetails.innerHTML = `
      <div style="margin-bottom: 6px;"><strong>Intern:</strong> ${escapeHtml(prof.intern_name || 'N/A')} · <strong>Startup:</strong> ${escapeHtml(prof.startup_name || 'N/A')}</div>
      <div style="margin-bottom: 6px;"><strong>Email:</strong> ${escapeHtml(prof.email || 'N/A')} · <strong>Designation:</strong> ${escapeHtml(prof.designation || 'N/A')}</div>
      <div><strong>Imported Dates (${dates.length}):</strong> <span class="text-primary">${dates.join(', ') || 'None'}</span></div>
    `;
    elements.importEmailResultCard.classList.remove('hidden');

    elements.submitImportEmailBtn.classList.add('hidden');
    elements.doneImportEmailBtn.classList.remove('hidden');

    logMessage(`[SUCCESS] Imported ${dates.length} submissions for ${prof.intern_name} (${prof.startup_name}).`, 'success');
    showSnackbar(`Successfully imported profile and ${dates.length} submission(s)!`, 'success');

    // Refresh state in background
    await fetchStatus();
    await checkCredentials(false);
    await fetchDates();
  } catch (err) {
    logMessage(`Email import error: ${err.message}`, 'error');
    showSnackbar(`Email import failed: ${err.message}`, 'error');
  } finally {
    elements.submitImportEmailBtn.disabled = false;
    elements.importEmailBtnText.textContent = 'Parse & Import with AI';
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Event Bindings
function initEventListeners() {
  elements.targetToggleBtn.addEventListener('click', toggleTarget);

  elements.savePhaseBtn.addEventListener('click', () => {
    state.generalPhase = elements.generalPhaseInput.value.trim();
    showSnackbar('General direction updated!', 'success');
  });

  document.querySelectorAll('.quick-phase-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      elements.generalPhaseInput.value = chip.getAttribute('data-text');
      state.generalPhase = elements.generalPhaseInput.value;
      showSnackbar('General direction updated!', 'success');
    });
  });

  document.querySelectorAll('.challenge-preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      elements.challengesInput.value = chip.getAttribute('data-text');
    });
  });

  elements.generateAiBtn.addEventListener('click', generateWithAI);
  elements.workshopToggleBtn.addEventListener('click', toggleWorkshop);
  elements.markAbsentBtn.addEventListener('click', toggleMarkAbsent);
  elements.autobalanceHoursBtn.addEventListener('click', autobalanceHours);
  elements.syncLinesToItemsBtn.addEventListener('click', syncLinesToItems);
  elements.refillYesterdayBtn.addEventListener('click', () => {
    if (confirm('Reset yesterday tasks to previous day submission?')) {
      loadDayData(state.currentDate);
    }
  });

  elements.addTaskCardBtn.addEventListener('click', () => {
    state.currentData.task_items.push({
      task_number: (state.currentData.task_items.length || 0) + 1,
      title: 'New Task',
      continuation: 'No',
      status: 'Completed',
      time_spent: 1.5,
      completion_date: state.currentDate,
    });
    renderTaskCards();
    updateHoursMeter();
  });

  elements.submitFormBtn.addEventListener('click', submitCurrentDay);
  elements.nextDayBtn.addEventListener('click', selectNextDay);

  elements.consoleHeaderHandle.addEventListener('click', () => {
    elements.consoleDrawer.classList.toggle('collapsed');
  });
  elements.closeConsoleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    elements.consoleDrawer.classList.toggle('collapsed');
  });

  elements.historyModalBtn.addEventListener('click', openHistoryModal);
  elements.closeHistoryModalBtn.addEventListener('click', () => { elements.historyModal.classList.add('hidden'); });
  elements.settingsModalBtn.addEventListener('click', openSettingsModal);
  elements.closeSettingsModalBtn.addEventListener('click', () => { elements.settingsModal.classList.add('hidden'); });
  elements.saveSettingsBtn.addEventListener('click', saveSettings);

  // Credentials & Setup Modal Events
  elements.credentialsModalBtn.addEventListener('click', () => openCredentialsModal());
  elements.closeCredentialsModalBtn.addEventListener('click', closeCredentialsModal);
  elements.cancelCredentialsBtn.addEventListener('click', closeCredentialsModal);
  elements.toggleKeyVisibilityBtn.addEventListener('click', toggleKeyVisibility);
  elements.testGeminiKeyBtn.addEventListener('click', testGeminiKey);
  elements.saveCredentialsBtn.addEventListener('click', saveCredentials);

  // Email Import Modal Events
  elements.importEmailModalBtn.addEventListener('click', openImportEmailModal);
  elements.closeImportEmailModalBtn.addEventListener('click', closeImportEmailModal);
  elements.cancelImportEmailBtn.addEventListener('click', closeImportEmailModal);
  elements.submitImportEmailBtn.addEventListener('click', submitImportEmail);
  elements.doneImportEmailBtn.addEventListener('click', () => {
    closeImportEmailModal();
    showSnackbar('Import applied! Timeline and profile refreshed.', 'success');
  });
  if (elements.shortcutImportEmailBtn) {
    elements.shortcutImportEmailBtn.addEventListener('click', () => {
      closeCredentialsModal();
      openImportEmailModal();
    });
  }

  elements.tasksTodayInput.addEventListener('input', updateLineCounts);

  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      submitCurrentDay();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g') {
      e.preventDefault();
      generateWithAI();
    }
  });
}

async function initApp() {
  logMessage('Material 3 Intern Progress Studio initialized.');
  initEventListeners();
  await fetchStatus();
  await checkCredentials(false);
  await fetchDates();
}

window.addEventListener('DOMContentLoaded', initApp);

