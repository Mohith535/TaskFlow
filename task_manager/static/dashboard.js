    let allTasks = [], currentFilter = 'all', currentActiveTaskId = null, selectedPriority = 'medium';
    let currentSortMode = 'urgency';
    let selectedDuration = null, parsedDeadlineISO = null, selectedDeadlineType = 'soft';
    let recoveryActive = false, recoveryTaskIds = [];

    // ── PRIORITY NORMALIZATION (BUG FIX) ──────────────────────────────
    // CLI stores: Critical, Strategic, Noise, Purge
    // UI expects: high, medium, low
    function normalizePriority(p) {
        if (!p) return 'medium';
        const lp = p.toLowerCase();
        if (lp === 'critical' || lp === 'high') return 'high';
        if (lp === 'strategic' || lp === 'medium') return 'medium';
        if (lp === 'noise' || lp === 'low' || lp === 'purge') return 'low';
        return 'medium';
    }

    // CODE-HEALTH: single TIS→colour threshold (was duplicated across loadStats + loadDayOfWeek)
    function tfScoreColor(s) { return s >= 80 ? 'var(--viz-high)' : (s >= 60 ? 'var(--viz-medium)' : 'var(--viz-low)'); }

    // ── PHASE 1 UTILITIES ─────────────────────────────────────────────
    function escapeHtml(s) {
        // SEC-01: neutralise user-supplied task content before it is placed into innerHTML.
        if (s === null || s === undefined) return '';
        return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }
    function safeHref(u) {
        // SEC-01: only allow safe link schemes in an href (blocks javascript:/data: execution).
        const s = String(u || '').trim();
        return /^(https?:|mailto:|\/)/i.test(s) ? s : '#';
    }

    function formatDeadline(isoString) {
        if (!isoString) return null;
        try {
            const deadline = new Date(isoString);
            if (isNaN(deadline.getTime())) return null;
            const now = new Date();
            const diffMs = deadline - now;
            const diffMin = Math.floor(diffMs / 60000);
            const diffHr = diffMs / 3600000;
            const isToday = deadline.toDateString() === now.toDateString();
            const tomorrow = new Date(now); tomorrow.setDate(tomorrow.getDate() + 1);
            const isTomorrow = deadline.toDateString() === tomorrow.toDateString();
            const timeStr = deadline.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'});
            const dateStr = deadline.toLocaleDateString([], {weekday:'short', day:'numeric', month:'short'});
            let text, color, isOverdue = false, isUrgent = false, pressureLevel = 0;

            if (diffMs < 0) {
                isOverdue = true; pressureLevel = 3;
                const overdueDays = Math.abs(diffMs) / 86400000;
                if (overdueDays > 1) {
                    // Fix 4: more than a day overdue → show the date, never hours
                    text = 'OVERDUE — ' + deadline.toLocaleDateString([], {day:'numeric', month:'short'});
                } else {
                    text = 'OVERDUE · ' + (isToday ? 'Today ' + timeStr : dateStr + ' · ' + timeStr);
                }
                color = 'var(--red)';
            } else if (isToday) {
                if (diffHr > 3) { text = 'Today at ' + timeStr; color = 'var(--text-muted)'; pressureLevel = 0; }
                else if (diffHr > 1) { text = 'Today at ' + timeStr + ' · ' + Math.floor(diffHr) + 'h ' + (diffMin % 60) + 'm left'; color = 'var(--amber)'; pressureLevel = 1; isUrgent = true; }
                else if (diffMin > 15) { text = 'Today at ' + timeStr + ' · ' + diffMin + 'm left'; color = 'var(--amber)'; pressureLevel = 2; isUrgent = true; }
                else { text = 'Today at ' + timeStr + ' · ' + diffMin + 'm left ⚠'; color = 'var(--red)'; pressureLevel = 3; isUrgent = true; }
            } else if (isTomorrow) { text = 'Tomorrow at ' + timeStr; color = 'var(--text-muted)'; }
            else { text = dateStr + ' · ' + timeStr; color = 'var(--text-muted)'; }
            return { text, color, isOverdue, isUrgent, pressureLevel };
        } catch(e) { return null; }
    }

    function getPressureLevel(task) {
        // CODE-HEALTH: single source of truth — prefer the server-computed pressure_level
        // (Python get_pressure_level); fall back to the local derivation only if absent.
        if (task && typeof task.pressure_level === 'number') return task.pressure_level;
        if (!task.deadline) return 0;
        const dl = formatDeadline(task.deadline);
        return dl ? dl.pressureLevel : 0;
    }

    function parseDeadlineInput(str) {
        if (!str || !str.trim()) return null;
        const s = str.trim().toLowerCase();
        const now = new Date();
        let d = null;

        function applyTimeOrDefault(date, text) {
            const m = text.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
            if (m) {
                let h = parseInt(m[1]);
                const min = m[2] ? parseInt(m[2]) : 0;
                const ap = m[3].toLowerCase();
                if (ap === 'pm' && h < 12) h += 12;
                if (ap === 'am' && h === 12) h = 0;
                date.setHours(h, min, 0, 0);
            } else {
                date.setHours(23, 59, 0, 0);
            }
            return date;
        }

        // 1. "today" / "tomorrow"
        if (s.startsWith('today')) {
            d = new Date(now);
            return applyTimeOrDefault(d, s);
        }
        if (s.startsWith('tomorrow')) {
            d = new Date(now); d.setDate(d.getDate() + 1);
            return applyTimeOrDefault(d, s);
        }

        // 2. Relative: "in 2h", "in 30m"
        const relH = s.match(/^in\s+(\d+)\s*h/);
        if (relH) return new Date(now.getTime() + parseInt(relH[1]) * 3600000);
        const relM = s.match(/^in\s+(\d+)\s*m/);
        if (relM) return new Date(now.getTime() + parseInt(relM[1]) * 60000);

        // 3. Day names: "friday", "fri 3pm"
        const dayNames = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday'];
        for (let i = 0; i < dayNames.length; i++) {
            if (s.startsWith(dayNames[i]) || s.startsWith(dayNames[i].slice(0,3))) {
                d = new Date(now);
                let diff = i - now.getDay(); if (diff <= 0) diff += 7;
                d.setDate(d.getDate() + diff);
                return applyTimeOrDefault(d, s);
            }
        }

        // 4. Month names: "may 7", "7 may", "may 7 3pm", "jun 15 8:45am"
        const monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
        const monthFull = ['january','february','march','april','may','june','july','august','september','october','november','december'];
        for (let mi = 0; mi < 12; mi++) {
            const r1 = new RegExp('\b(' + monthFull[mi] + '|' + monthNames[mi] + ')\s+(\d{1,2})');
            const r2 = new RegExp('(\d{1,2})(?:st|nd|rd|th)?\s+(' + monthFull[mi] + '|' + monthNames[mi] + ')');
            let match = s.match(r1);
            if (match) {
                d = new Date(now.getFullYear(), mi, parseInt(match[2]));
                if (d < now) d.setFullYear(d.getFullYear() + 1);
                return applyTimeOrDefault(d, s);
            }
            match = s.match(r2);
            if (match) {
                d = new Date(now.getFullYear(), mi, parseInt(match[1]));
                if (d < now) d.setFullYear(d.getFullYear() + 1);
                return applyTimeOrDefault(d, s);
            }
        }

        // 5. Numeric: "5/7", "5/7/2026"
        const numDate = s.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?/);
        if (numDate) {
            const mo = parseInt(numDate[1]) - 1;
            const dy = parseInt(numDate[2]);
            const yr = numDate[3] ? (numDate[3].length === 2 ? 2000 + parseInt(numDate[3]) : parseInt(numDate[3])) : now.getFullYear();
            d = new Date(yr, mo, dy);
            return applyTimeOrDefault(d, s);
        }

        // 6. ISO: "2026-05-07"
        const isoDate = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (isoDate) {
            d = new Date(parseInt(isoDate[1]), parseInt(isoDate[2]) - 1, parseInt(isoDate[3]));
            return applyTimeOrDefault(d, s);
        }

        // 7. Native Date.parse fallback
        try {
            const attempt = new Date(str.trim());
            if (!isNaN(attempt.getTime()) && attempt.getFullYear() > 2000) return attempt;
        } catch(e) {}

        return d;
    }

    // ── SYSTEM STATES & AMBIENCE ──────────────────────────────────────────
    function setSystemState(state) {
        document.body.className = '';
        document.body.classList.add(`state-${state}`);
        const msg = document.getElementById('advisor-msg');
        if (msg) {
            msg.style.opacity = '0';
            setTimeout(() => {
                const map = {
                    'thinking': 'Intelligence: Analyzing mission parameters... Critical paths established.',
                    'idle': 'System stable. Monitoring activity signals.',
                    'deep-work': 'Protocol: Deep Work active. Peripheral sensors neutralized.'
                };
                msg.textContent = map[state] || map.idle;
                msg.style.opacity = '1';
            }, 300);
        }
    }

    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth - 0.5) * 20;
        const y = (e.clientY / window.innerHeight - 0.5) * 20;
        const par = document.getElementById('bg-parallax');
        if (par) par.style.transform = `translate(${-x}px, ${-y}px)`;
    });
    // ── PROTOCOL TOAST SYSTEM ──────────────────────────────────────────
    function showToast(msg, color) {
        const t = document.getElementById('toast');
        if (!t) return;
        t.textContent = msg;
        t.style.borderLeftColor = color || 'var(--blue)';
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 5000);
    }

    // ── NAVIGATION PROTOCOL (VIEW SWITCHING) ─────────────────────────────
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view-content');

    function switchView(viewId) {
        if (!views || views.length === 0) return;
        views.forEach(v => v.classList.add('hidden'));
        const targetView = document.getElementById(`view-${viewId}`);
        if (targetView) targetView.classList.remove('hidden');

        navItems.forEach(item => {
            item.classList.toggle('active', item.id === `nav-${viewId}`);
        });

        if (typeof startSimulation === 'function') {
            try {
                if (viewId === 'dashboard') startSimulation('execution');
                else if (viewId === 'tasks') startSimulation('missions');
                else if (viewId === 'timeline') startSimulation('focus');
            } catch(e) { console.error("Sim error:", e); }
        }

        if (viewId === 'tasks') {
            loadTasks().catch(console.error);
            setSystemState('idle');
        } else if (viewId === 'dashboard' || viewId === 'timeline') {
            setSystemState('idle');
        }

        // Fix 3: particles run on ALL pages now — visibility is user-controlled (Operator settings).
        // Keep the loop alive across view switches when the user has them enabled.
        try {
            if (window.tfParticlesEnabled !== false && !animationId
                && typeof activeSimType === 'string' && activeSimType) {
                animateSimulation(activeSimType);
            }
        } catch (e) {}
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const vid = item.id.replace('nav-', '');
            switchView(vid);
            if (vid === 'ai' || vid === 'stats') loadStats().catch(console.error);
        });
    });

    // ── MISSION CONTROLS ──────────────────────────────────────────────────
    const missionTitle = document.getElementById('mission-title');
    const btnDeploy = document.getElementById('btn-deploy');

    document.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedPriority = btn.dataset.priority;
        });
    });

    function toggleCreateMission() {
        const p = document.getElementById('deploy-modal-overlay');
        p.classList.toggle('active');
        const isOpen = p.classList.contains('active');
        document.body.style.overflow = isOpen ? 'hidden' : '';
        if (isOpen) {
            // Reset to Task mode on open
            setMissionType('Task');
            document.getElementById('event-date').valueAsDate = new Date();
            tSelection.style.display = 'none';
            tDisplay.textContent = 'Drag to select';
            // Progressive disclosure: enrichment collapsed by default
            const en = document.getElementById('dm-enrich');
            if (en) en.classList.remove('open');
            const et = document.getElementById('dm-enrich-text');
            if (et) et.textContent = '+ Add notes, links & checklist';
            if (window.tfUpdateProgressDots) tfUpdateProgressDots();
            const body = document.getElementById('dm-body');
            if (body) { body.scrollTop = 0; body.style.boxShadow = 'none'; }
            try { tfSyncFocusLock(); } catch (e) {}
            setTimeout(() => { const ti = document.getElementById('mission-title'); if (ti) ti.focus(); }, 280);
        }
    }
    // Backdrop click closes the panel + scroll-shadow on the body zone (run once)
    (function(){
        const ov = document.getElementById('deploy-modal-overlay');
        if (ov && !ov._tfBackdrop) {
            ov._tfBackdrop = true;
            ov.addEventListener('click', e => { if (e.target === ov) toggleCreateMission(); });
            const body = document.getElementById('dm-body');
            if (body) body.addEventListener('scroll', () => {
                body.style.boxShadow = body.scrollTop > 8 ? 'inset 0 8px 16px rgba(0,0,0,0.25)' : 'none';
            });
        }
    })();
    window.tfToggleEnrichSection = function() {
        const en = document.getElementById('dm-enrich');
        if (!en) return;
        const open = en.classList.toggle('open');
        const txt = document.getElementById('dm-enrich-text');
        if (txt) txt.textContent = open ? '▲ Collapse details' : '+ Add notes, links & checklist';
        if (window.tfUpdateProgressDots) tfUpdateProgressDots();
        if (open) setTimeout(() => { const n = document.getElementById('mission-notes'); if (n) n.focus(); }, 300);
    };
    window.tfUpdateProgressDots = function() {
        const d2 = document.getElementById('dm-dot-2');
        const d3 = document.getElementById('dm-dot-3');
        if (d2) d2.classList.toggle('filled', !!parsedDeadlineISO);
        if (d3) {
            const notes = document.getElementById('mission-notes');
            const hasNotes = notes && notes.value.trim().length > 0;
            d3.classList.toggle('filled', hasNotes || (window.pendingLinks||[]).length > 0 || (window.pendingChecklist||[]).length > 0);
        }
    };

    let currentMissionType = 'Task';
    let eventStartMinutes = 8 * 60; // 8 AM
    let eventEndMinutes = 9 * 60;   // 9 AM

    window.setMissionType = function(type) {
        currentMissionType = type;
        document.getElementById('btn-type-task').classList.toggle('active', type === 'Task');
        document.getElementById('btn-type-event').classList.toggle('active', type === 'Event');
        document.querySelectorAll('.task-mode-only').forEach(el => el.style.display = type === 'Task' ? 'block' : 'none');
        document.querySelectorAll('.event-mode-only').forEach(el => el.style.display = type === 'Event' ? 'block' : 'none');
        validateMissionInput();
    }

    function formatTimeFromMinutes(mins) {
        let h = Math.floor(mins / 60);
        let m = mins % 60;
        let ampm = h >= 12 ? 'PM' : 'AM';
        h = h % 12;
        if (h === 0) h = 12;
        return `${h}:${m.toString().padStart(2, '0')} ${ampm}`;
    }

    // Timeline Slider Logic
    const tSlider = document.getElementById('timeline-slider');
    const tSelection = document.getElementById('timeline-selection');
    const tDisplay = document.getElementById('event-time-display');
    let isDraggingTimeline = false;
    let dragStartMins = 0;

    function getMinutesFromEvent(e) {
        const rect = tSlider.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let x = clientX - rect.left;
        x = Math.max(0, Math.min(x, rect.width));
        const pct = x / rect.width;
        const totalMins = 720; // 8 AM to 8 PM (12 hours)
        let mins = Math.round((pct * totalMins) / 15) * 15; // snap to 15 min
        return (8 * 60) + mins;
    }

    function updateTimelineUI() {
        const totalMins = 720;
        const startPct = Math.max(0, (eventStartMinutes - 8 * 60) / totalMins) * 100;
        const endPct = Math.min(100, (eventEndMinutes - 8 * 60) / totalMins) * 100;
        tSelection.style.display = 'block';
        tSelection.style.left = startPct + '%';
        tSelection.style.width = Math.max(1, endPct - startPct) + '%';
        tDisplay.textContent = `${formatTimeFromMinutes(eventStartMinutes)} - ${formatTimeFromMinutes(eventEndMinutes)}`;
        // Sync manual time inputs
        const startInput = document.getElementById('event-start-time');
        const endInput = document.getElementById('event-end-time');
        if (startInput && !startInput._userTyping) startInput.value = formatTimeFromMinutes(eventStartMinutes);
        if (endInput && !endInput._userTyping) endInput.value = formatTimeFromMinutes(eventEndMinutes);
        // Show duration
        const durMins = eventEndMinutes - eventStartMinutes;
        const durDisplay = document.getElementById('event-duration-display');
        const durValue = document.getElementById('event-duration-value');
        if (durDisplay && durValue && durMins > 0) {
            const dh = Math.floor(durMins / 60);
            const dm = durMins % 60;
            durValue.textContent = (dh > 0 ? dh + 'h ' : '') + (dm > 0 ? dm + 'm' : '');
            durDisplay.style.display = 'block';
        } else if (durDisplay) {
            durDisplay.style.display = 'none';
        }
        validateMissionInput();
    }

    tSlider.addEventListener('mousedown', (e) => {
        isDraggingTimeline = true;
        dragStartMins = getMinutesFromEvent(e);
        eventStartMinutes = dragStartMins;
        eventEndMinutes = dragStartMins + 30; // default 30 min duration
        updateTimelineUI();
    });
    window.addEventListener('mousemove', (e) => {
        if (!isDraggingTimeline) return;
        const currentMins = getMinutesFromEvent(e);
        if (currentMins >= dragStartMins) {
            eventStartMinutes = dragStartMins;
            eventEndMinutes = currentMins;
        } else {
            eventStartMinutes = currentMins;
            eventEndMinutes = dragStartMins;
        }
        if (eventEndMinutes === eventStartMinutes) eventEndMinutes += 15; // minimum 15m
        updateTimelineUI();
    });
    window.addEventListener('mouseup', () => isDraggingTimeline = false);

    // Manual time input parsing
    function parseTimeInput(str) {
        if (!str) return null;
        const m = str.trim().match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
        if (!m) return null;
        let h = parseInt(m[1]);
        const min = m[2] ? parseInt(m[2]) : 0;
        const ap = m[3] ? m[3].toLowerCase() : null;
        if (ap === 'pm' && h < 12) h += 12;
        if (ap === 'am' && h === 12) h = 0;
        if (!ap && h < 8) h += 12; // assume PM for small numbers
        return h * 60 + min;
    }

    const eventStartInput = document.getElementById('event-start-time');
    const eventEndInput = document.getElementById('event-end-time');
    function handleTimeInputChange() {
        const startMins = parseTimeInput(eventStartInput.value);
        const endMins = parseTimeInput(eventEndInput.value);
        if (startMins !== null) eventStartMinutes = startMins;
        if (endMins !== null) eventEndMinutes = endMins;
        if (eventEndMinutes <= eventStartMinutes) eventEndMinutes = eventStartMinutes + 15;
        eventStartInput._userTyping = false;
        eventEndInput._userTyping = false;
        updateTimelineUI();
    }
    if (eventStartInput) {
        eventStartInput.addEventListener('focus', () => eventStartInput._userTyping = true);
        eventStartInput.addEventListener('change', handleTimeInputChange);
        eventStartInput.addEventListener('blur', handleTimeInputChange);
    }
    if (eventEndInput) {
        eventEndInput.addEventListener('focus', () => eventEndInput._userTyping = true);
        eventEndInput.addEventListener('change', handleTimeInputChange);
        eventEndInput.addEventListener('blur', handleTimeInputChange);
    }

    // Validation logic for Deploy button
    function validateMissionInput() {
        let valid = missionTitle.value.trim().length > 0;
        if (currentMissionType === 'Event') {
            const dt = document.getElementById('event-date').value;
            if (!dt || tSelection.style.display === 'none') valid = false;
        }
        if (btnDeploy) {
            btnDeploy.disabled = !valid;
            btnDeploy.classList.toggle('active', valid);
        }
    }
    missionTitle.addEventListener('input', validateMissionInput);
    document.getElementById('event-date').addEventListener('input', validateMissionInput);

    if (btnDeploy) {
        btnDeploy.addEventListener('click', async () => {
            const title = missionTitle.value.trim();
            const tagStr = document.getElementById('mission-tags') ? document.getElementById('mission-tags').value : "";
            const tags = tagStr.split(',').map(s=>s.trim()).filter(s=>s.length > 0);
            if (!title) return;
            setSystemState('thinking');
            
            const payload = { title, priority: selectedPriority, tags, mission_type: currentMissionType };

            // Enrichment (E12): description / links / checklist
            const enrichNotes = (document.getElementById('mission-notes') ? document.getElementById('mission-notes').value : '').trim();
            if (enrichNotes) payload.description = enrichNotes;
            if (window.pendingLinks && window.pendingLinks.length) payload.links = window.pendingLinks.slice(0, 10);
            if (window.pendingChecklist && window.pendingChecklist.length) payload.checklist = window.pendingChecklist.slice(0, 20).map(txt => ({ text: txt }));

            if (currentMissionType === 'Task') {
                const durVal = document.getElementById('mission-duration').value.trim();
                if (durVal) payload.duration = durVal;
                if (parsedDeadlineISO) { payload.deadline = parsedDeadlineISO; payload.deadline_type = selectedDeadlineType; }
            } else if (currentMissionType === 'Event') {
                const dateVal = document.getElementById('event-date').value; // YYYY-MM-DD
                const startTimeStr = formatTimeFromMinutes(eventStartMinutes);
                const endTimeStr = formatTimeFromMinutes(eventEndMinutes);
                
                payload.date = dateVal;
                payload.start_time = startTimeStr;
                payload.end_time = endTimeStr;
                
                // Auto-calculate duration string (e.g. "1h 15m")
                const durationMins = eventEndMinutes - eventStartMinutes;
                const dh = Math.floor(durationMins / 60);
                const dm = durationMins % 60;
                payload.duration = (dh > 0 ? dh + 'h ' : '') + (dm > 0 ? dm + 'm' : '').trim();
                
                // Auto-calculate strict deadline
                const d = new Date(dateVal);
                d.setHours(Math.floor(eventEndMinutes / 60), eventEndMinutes % 60, 0, 0);
                payload.deadline = d.toISOString();
                payload.deadline_type = 'hard'; // Events are reality constraints
                payload.reminder_offset = parseInt(document.getElementById('event-reminder').value);
            }
            try {
                const _focusQueue = !!window.tfFocusActive;
                const res = await fetch(_focusQueue ? '/api/focus/queue' : '/api/tasks/create-full', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    if (_focusQueue) { try { showToast('Queued — adds when focus ends', 'var(--blue)'); } catch(e){} try { tfSyncFocusLock(); } catch(e){} }
                    missionTitle.value = '';
                    if(document.getElementById('mission-tags')) document.getElementById('mission-tags').value = '';
                    tfResetEnrichmentPanel();
                    if(document.getElementById('mission-deadline')) document.getElementById('mission-deadline').value = '';
                    if(document.getElementById('mission-duration')) document.getElementById('mission-duration').value = '';
                    btnDeploy.disabled = true;
                    btnDeploy.classList.remove('active');
                    parsedDeadlineISO = null; selectedDeadlineType = 'soft';
                    const dts = document.getElementById('deadline-type-section'); if(dts) dts.style.display='none';
                    const dp = document.getElementById('deadline-parsed-display'); if(dp){dp.textContent='';dp.classList.remove('visible');}
                    showToast('Mission deployed.', 'var(--green)');
                    toggleCreateMission();
                    await loadTasks();
                    setSystemState('idle');
                } else {
                    const errData = await res.json().catch(()=>({}));
                    showToast('Failed to deploy: ' + (errData.error || res.statusText), 'var(--red)');
                    setSystemState('idle');
                }
            } catch (err) {
                showToast('Error deploying mission', 'var(--red)');
                console.error(err);
                setSystemState('idle');
            }
        });
    }

    let timelineMapping = {}; // Execution Engine: Backend synced timeline mapping

    // ── MOMENTUM CASCADE ENGINE ───────────────────────────────────────────
    async function loadTasks() {
        try {
            const [tasksRes, statsRes, timelineRes] = await Promise.all([
                fetch('/api/tasks'),
                fetch('/api/stats'),
                fetch('/api/timeline')
            ]);
            const tasksData = await tasksRes.json();
            const statsData = await statsRes.json();
            
            try {
                const timelineData = await timelineRes.json();
                const localMappingStr = localStorage.getItem('task_timeline_mapping');
                if (Object.keys(timelineData).length === 0 && localMappingStr && localMappingStr !== '{}') {
                    // One-time migration from Local Storage to Server
                    timelineMapping = JSON.parse(localMappingStr);
                    fetch('/api/timeline', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ mapping: timelineMapping })
                    }).catch(e => {}); // Ignore fail
                } else {
                    timelineMapping = timelineData;
                }
            } catch(e) { console.error("Timeline API fail", e); }
            allTasks = tasksData.tasks || [];
            updateIntegrityMeter(statsData);
            updateControlCenter();
            renderTaskList();
            renderTimeline();
        } catch(e) {
            console.error("Critical: Task Cascade Engine Failed", e);
            showToast('Cascade Error: ' + e.message, 'var(--red)');
        }
    }

    // ── S10: DAILY EXECUTION PATH ──
    function _pathFmtMins(m) {
        m = Math.round(m || 0);
        if (m <= 0) return '0m';
        const h = Math.floor(m / 60), mm = m % 60;
        return h && mm ? `${h}h ${mm}m` : (h ? `${h}h` : `${mm}m`);
    }
    function renderPath(data) {
        const body = document.getElementById('cc-path-body');
        const meta = document.getElementById('cc-path-meta');
        if (!body) return;
        const sections = (data && data.sections) || {};
        const sm = (data && data.section_minutes) || {};
        const prime = sections.prime || [], sec = sections.secondary || [], low = sections.low_effort || [];

        function durBadge(t) {
            return t.duration
                ? `<span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--blue);background:color-mix(in srgb, var(--accent-info) 8%, transparent);padding:1px 6px;border-radius:4px;margin-left:8px;">${t.duration}</span>`
                : '';
        }
        function dlStr(t) {
            const d = (typeof formatDeadline === 'function') ? formatDeadline(t.deadline) : null;
            return d ? `<span style="font-size:10px;color:${d.color};margin-left:8px;font-family:'DM Mono',monospace;">${d.text}</span>` : '';
        }
        function row(t) {
            const done = t.completed ? 'opacity:0.5;text-decoration:line-through;' : '';
            return `<div style="display:flex;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--text-body);${done}">${escapeHtml(t.title)}${durBadge(t)}${dlStr(t)}</div>`;
        }
        function group(label, color, bg, items) {
            if (!items.length) return '';
            const rows = items.map(row).join('<div style="height:6px;"></div>');
            return `<div style="background:${bg};border-left:3px solid ${color};border-radius:8px;padding:12px 14px;">
                <div style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:${color};margin-bottom:8px;font-weight:700;">${label}</div>
                ${rows}
            </div>`;
        }

        let html = '';
        if (data && data.day_note) {
            const nc = data.day_mode === 'best' ? 'var(--viz-high)' : (data.day_mode === 'worst' ? 'var(--viz-medium)' : 'var(--accent-info)');
            html += `<div style="font-size:11px;color:${nc};letter-spacing:0.5px;margin-bottom:4px;">⚡ ${data.day_note}</div>`;
        }
        html += group('★ PRIME TARGET', 'var(--amber)', 'color-mix(in srgb, var(--accent-warning) 4%, transparent)', prime);
        html += group('SECONDARY', 'var(--blue)', 'color-mix(in srgb, var(--accent-info) 3%, transparent)', sec);
        html += group('LOW EFFORT', 'var(--text-disabled)', 'rgba(139,148,158,0.03)', low);
        if (!prime.length && !sec.length && !low.length) {
            // S13-A BLOCK 1: nothing scheduled → a single generate action, not an empty void
            html = `<div style="opacity:0.6;font-size:12px;margin-bottom:10px;">No path generated for today.</div>
                <button onclick="regeneratePath()" style="width:100%;background:transparent;border:1px dashed var(--border-neutral);color:var(--text-disabled);font-size:11px;padding:10px;border-radius:8px;cursor:pointer;font-family:'DM Mono',monospace;letter-spacing:1px;">+ Generate Today's Path</button>`;
        }
        body.innerHTML = html;

        if (meta) {
            const total = (sm.prime || 0) + (sm.secondary || 0) + (sm.low_effort || 0);
            let m = `Est. ${_pathFmtMins(total)}`;
            if (data && data.adherence != null) m += ` · adherence ${Math.round(data.adherence * 100)}%`;
            meta.textContent = m;
        }
        // stash today's path task IDs so TODAY'S MISSIONS can include them
        try { window.tfPathIds = [].concat(prime, sec, low).map(x => x.id); } catch (e) {}
    }
    function loadPath() {
        fetch('/api/path').then(r => r.json()).then(renderPath).catch(() => {});
    }
    function regeneratePath() {
        const btn = document.getElementById('cc-path-regen');
        if (btn) { btn.textContent = '↻ REGENERATING…'; btn.disabled = true; }
        fetch('/api/path/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
            .then(r => r.json()).then(renderPath).catch(() => {})
            .finally(() => { if (btn) { btn.textContent = '↻ REGENERATE PATH'; btn.disabled = false; } });
    }

    // ── S11: FOCUS WINDOW LOCK (deploy button + queue badge) ──
    function tfSyncFocusLock() {
        fetch('/api/focus-status').then(r => r.json()).then(s => {
            window.tfFocusActive = !!(s && s.active);
            window.tfQueueCount = (s && s.queued_count) || 0;
            const btn = document.getElementById('btn-deploy');
            const badge = document.getElementById('dm-focus-badge');
            if (btn) {
                if (window.tfFocusActive) {
                    btn.dataset.focusLabel = '1';
                    btn.textContent = 'FOCUS ACTIVE — WILL QUEUE';
                    btn.style.background = 'linear-gradient(135deg,var(--amber),#E3B341)';
                    btn.style.borderColor = 'transparent';
                    btn.style.color = 'var(--bg-primary)';
                } else if (btn.dataset.focusLabel) {
                    btn.dataset.focusLabel = '';
                    btn.textContent = 'DEPLOY MISSION';
                    btn.style.background = '';
                    btn.style.borderColor = '';
                    btn.style.color = '';
                }
            }
            if (badge) {
                if (window.tfFocusActive && window.tfQueueCount > 0) {
                    badge.style.display = 'inline-block';
                    badge.textContent = window.tfQueueCount + ' queued';
                } else {
                    badge.style.display = 'none';
                }
            }
        }).catch(() => {});
    }

    function tfStartFocus(id) {
        fetch('/api/focus/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ task_id: id, minutes: 25 }) })
            .then(r => r.json())
            .then(() => { try { showToast('Focus started · 25 min', 'var(--blue)'); } catch (e) {} setTimeout(() => { try { tfSyncFocusLock(); } catch (e) {} }, 400); })
            .catch(() => {});
    }

    function updateControlCenter() {
        const now = new Date();
        const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);

        // Calculate pressure levels for Approaching banner
        let p2Count = 0;
        let p3Count = 0;
        activeTasks.forEach(t => {
            const pl = getPressureLevel(t);
            if (pl === 2) p2Count++;
            else if (pl === 3) p3Count++;
        });
        const totalPressure = p2Count + p3Count;
        const banner = document.getElementById('cc-approaching-banner');
        if (banner) {
            if (totalPressure > 0) {
                banner.style.display = 'flex';
                if (p3Count > 0) {
                    banner.style.background = 'color-mix(in srgb, var(--accent-danger) 10%, transparent)';
                    banner.style.border = '1px solid var(--red)';
                    banner.style.color = 'var(--red)';
                    banner.innerHTML = `<span style="animation: glowPulse 1.5s infinite;">⚡</span> ${totalPressure} task(s) need attention now.`;
                } else {
                    banner.style.background = 'color-mix(in srgb, var(--accent-warning) 10%, transparent)';
                    banner.style.border = '1px solid var(--amber)';
                    banner.style.color = 'var(--amber)';
                    banner.innerHTML = `⚡ ${totalPressure} task(s) need attention now.`;
                }
                if (!recoveryActive) {
                    banner.innerHTML += ` <button onclick="tfRecEntryConfirm()" style="margin-left:auto;background:color-mix(in srgb, var(--accent-warning) 10%, transparent);border:1px solid color-mix(in srgb, var(--accent-warning) 30%, transparent);border-radius:6px;padding:4px 12px;color:var(--amber);font-size:11px;font-weight:500;cursor:pointer;">Salvage my day →</button>`;
                }
            } else {
                banner.style.display = 'none';
            }
        }

        // ── PRIORITY ALERTS (Fix 1: today-focused, MAX 3, old overdue collapsed) ──
        const alertsContainer = document.getElementById('cc-alerts');
        if (alertsContainer) {
            const todayStr = now.toDateString();
            let alerts = [];
            let oldMissed = 0;
            activeTasks.forEach(t => {
                const dl = formatDeadline(t.deadline);
                if (!dl) return;
                const dlDate = new Date(t.deadline);
                if (isNaN(dlDate.getTime())) return;
                const overdueDays = (now - dlDate) / 86400000;
                const isHard = t.deadline_type === 'hard';
                const dueToday = dlDate.toDateString() === todayStr;
                // Collapse anything overdue by more than 3 days into one summary line
                if (dl.isOverdue && overdueDays > 3) { oldMissed++; return; }
                if (isHard && dueToday && dl.isOverdue) {
                    alerts.push({title:t.title, meta:'Hard deadline · due today, overdue', icon:'⚠ HARD DEADLINE TODAY', color:'var(--red)', sort:0});
                } else if (isHard && dueToday && dl.pressureLevel >= 2) {
                    alerts.push({title:t.title, meta:dl.text, icon:'⚡ HARD DEADLINE APPROACHING', color:'var(--amber)', sort:1});
                } else if (isHard && dl.isOverdue) {
                    alerts.push({title:t.title, meta:'Was due: '+dl.text.replace(/OVERDUE [·—]\s*/, ''), icon:'⚠ HARD DEADLINE MISSED', color:'var(--red)', sort:1.5});
                } else if ((t.postpone_count||0) >= 3) {
                    const severe = t.postpone_count >= 5;
                    alerts.push({title:t.title, meta:'Postponed '+t.postpone_count+'×'+(severe?' ⚠⚠':' ⚠'), icon: severe?'🚨 REPEATEDLY DEFERRED':'↩ REPEATEDLY DEFERRED', color: severe?'var(--red)':'var(--amber)', sort:2});
                }
            });
            alerts.sort((a,b) => a.sort - b.sort);
            alerts = alerts.slice(0, 3);

            let html = '';
            if (alerts.length > 0) {
                html = alerts.map(a => `<div class="alert-card">
                        <div class="alert-type" style="color:${a.color}">${a.icon}</div>
                        <div class="alert-title">${escapeHtml(a.title)}</div>
                        <div class="alert-meta">${a.meta}</div>
                    </div>`).join('');
            } else if (oldMissed === 0) {
                html = '<div style="color:var(--green); font-size:13px;">✓ All systems nominal.</div>';
            }
            if (oldMissed > 0) {
                html += `<div style="margin-top:8px;background:color-mix(in srgb, var(--accent-danger) 4%, transparent);border:1px solid color-mix(in srgb, var(--accent-danger) 10%, transparent);color:var(--red);font-size:12px;border-radius:8px;padding:8px 14px;">⚠ ${oldMissed} older missed deadline${oldMissed!==1?'s':''} pending review<br><span style="opacity:0.7;">Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span> to address them</span></div>`;
            }
            alertsContainer.innerHTML = html;

            // Entry point 4 — Recovery activation/exit from Priority Alerts
            if (recoveryActive) {
                alertsContainer.innerHTML += `<div class="rec-alerts-zone"><button class="rec-alerts-btn active" onclick="tfRecExitConfirm()">⚡ Recovery Mode Active · Exit</button></div>`;
            } else if (alerts.length > 0 || oldMissed > 0) {
                alertsContainer.innerHTML += `<div class="rec-alerts-zone"><button class="rec-alerts-btn" onclick="tfRecEntryConfirm()">⚡  ACTIVATE RECOVERY MODE</button></div>`;
            }
        }

        // S10: refresh the Daily Execution Path panel alongside the control center
        try { loadPath(); } catch (e) {}
        // S11: keep the focus-lock UI (deploy button + queue badge) in sync
        try { tfSyncFocusLock(); } catch (e) {}

        // helper: is a task within the ±45-min NOW window
        function isInNowWindow(t) {
            if (!t.deadline) return false;
            const d = new Date(t.deadline);
            if (isNaN(d.getTime())) return false;
            const m = (d - now) / 60000;
            return m >= -45 && m <= 45;
        }

        // ── NOW WINDOW (S13-A BLOCK 2: the single task to work on right now) ──
        const nowEl = document.getElementById('cc-now');
        if (nowEl) {
            const inWindow = activeTasks.filter(isInNowWindow).sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
            const futureNow = activeTasks.filter(t => t.deadline && new Date(t.deadline) > now).sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
            const nowTimeStr = now.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'});
            if (inWindow.length > 0) {
                const t = inWindow[0];
                const durStr = t.duration ? (' · ' + t.duration) : '';
                const endsStr = t.deadline ? (' · ends ~' + new Date(t.deadline).toLocaleTimeString([], {hour:'numeric', minute:'2-digit'})) : '';
                nowEl.innerHTML = `<div style="background:color-mix(in srgb, var(--accent-info) 5%, transparent);border:1px solid color-mix(in srgb, var(--accent-info) 20%, transparent);border-left:3px solid var(--blue);border-radius:10px;padding:14px 16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-size:10px;color:var(--blue);letter-spacing:2px;font-weight:500;">▶ NOW — YOU ARE HERE</div>
                        <div style="font-family:'DM Mono',monospace;color:var(--text-disabled);font-size:11px;">${nowTimeStr}</div>
                    </div>
                    <div style="font-size:15px;color:var(--text-hero);font-weight:500;margin-top:6px;">${escapeHtml(t.title)}</div>
                    <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${t.priority}${durStr}${endsStr}</div>
                    <button onclick="tfStartFocus(${t.id})" style="background:linear-gradient(135deg,var(--blue-dark),var(--blue-mid));border:none;border-radius:8px;height:34px;padding:0 14px;color:#fff;font-size:12px;font-weight:600;cursor:pointer;margin-top:10px;">Start Focus →</button>
                </div>`;
            } else {
                let sub;
                if (futureNow.length > 0) {
                    const t = futureNow[0];
                    const mins = Math.round((new Date(t.deadline) - now) / 60000);
                    sub = `<div style="color:var(--text-muted);font-size:12px;margin-top:4px;">Next: ${escapeHtml(t.title)} · in ${mins} min</div>`;
                } else if (activeTasks.some(t => t.deadline && new Date(t.deadline) < now)) {
                    sub = `<div style="color:var(--red);font-size:12px;margin-top:4px;">All scheduled missions overdue.<br>Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span></div>`;
                } else {
                    sub = `<div style="color:var(--text-muted);font-size:12px;margin-top:4px;">Nothing due soon.</div>`;
                }
                nowEl.innerHTML = `<div style="background:color-mix(in srgb, var(--text-primary) 2%, transparent);border:1px solid var(--border-subtle);border-radius:10px;padding:12px 16px;">
                    <div style="font-size:13px;color:var(--text-hero);">No mission in current window.</div>
                    ${sub}
                </div>`;
            }
        }

        // ── TODAY'S MISSIONS (Fix 1: strictly today — never weeks-old overdue) ──
        const upcomingContainer = document.getElementById('cc-upcoming');
        if (upcomingContainer) {
            const todayIso = now.toISOString().slice(0, 10);
            const todayStr2 = now.toDateString();
            const pathIds = window.tfPathIds || [];
            const todays = activeTasks.filter(t => {
                if (t.deadline) {
                    const d = new Date(t.deadline);
                    if (!isNaN(d.getTime()) && d.toDateString() === todayStr2) return true;
                }
                if (t.scheduled_date && t.scheduled_date === todayIso) return true;
                if (pathIds.indexOf(t.id) !== -1) return true;
                if (!t.deadline && t.created_at && String(t.created_at).slice(0, 10) === todayIso) return true;
                return false;
            });
            todays.sort((a, b) => {
                const aw = isInNowWindow(a), bw = isInNowWindow(b);
                if (aw !== bw) return aw ? -1 : 1;
                if (a.deadline && b.deadline) return new Date(a.deadline) - new Date(b.deadline);
                if (a.deadline) return -1;
                if (b.deadline) return 1;
                return 0;
            });

            if (todays.length === 0) {
                upcomingContainer.innerHTML = `<div style="opacity:0.6;font-size:13px;">No missions for today.</div>
                    <button onclick="toggleCreateMission()" style="margin-top:10px;background:color-mix(in srgb, var(--accent-info) 10%, transparent);border:1px solid color-mix(in srgb, var(--accent-info) 20%, transparent);color:var(--blue);border-radius:8px;padding:8px 14px;font-size:12px;cursor:pointer;">+ Create Mission</button>`;
            } else {
                upcomingContainer.innerHTML = todays.slice(0, 6).map(t => {
                    const np = normalizePriority(t.priority);
                    const isNow = isInNowWindow(t);
                    const borderColor = isNow ? 'var(--blue)' : (np === 'high' ? 'var(--red)' : np === 'medium' ? 'var(--amber)' : 'var(--blue)');
                    const dlInfo = formatDeadline(t.deadline);
                    const dlStr = dlInfo ? `<span style="font-size:10px;color:${dlInfo.color};margin-left:8px;font-family:'DM Mono',monospace;">${dlInfo.text}</span>` : '';
                    const nowBadge = isNow ? `<span style="background:color-mix(in srgb, var(--accent-info) 20%, transparent);color:var(--blue);font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;margin-right:6px;letter-spacing:0.5px;">NOW</span>` : '';
                    // Fix 3: only show a duration line when one is actually set
                    const durLine = t.duration ? `<div style="font-size:11px;color:var(--text-disabled);margin-top:6px;font-family:'DM Mono',monospace;">Est. ${t.duration}</div>` : '';
                    return `<div style="padding:12px;background:color-mix(in srgb, var(--text-primary) 2%, transparent);border-radius:8px;border-left:3px solid ${borderColor};">
                        <div style="display:flex;align-items:center;flex-wrap:wrap;">${nowBadge}${escapeHtml(t.title)}${dlStr}</div>
                        ${durLine}
                    </div>`;
                }).join('');

                // Fix 3: Next = earliest deadline >= now; if all overdue → taskflow missed (not "Next: overdue")
                const future2 = todays.filter(t => t.deadline && new Date(t.deadline) >= now).sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
                if (future2.length > 0) {
                    const nt = future2[0];
                    const mins = Math.round((new Date(nt.deadline) - now) / 60000);
                    upcomingContainer.innerHTML += `<div style="margin-top:10px;font-size:12px;color:var(--blue);">Next: ${escapeHtml(nt.title)} · in ${mins} min</div>`;
                } else if (todays.some(t => t.deadline && new Date(t.deadline) < now)) {
                    upcomingContainer.innerHTML += `<div style="margin-top:10px;font-size:12px;color:var(--amber);">All scheduled missions overdue. Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span></div>`;
                }
            }
        }

        // ── PERFORMANCE: Overdue + Deferred counts ──
        const overdueCount = activeTasks.filter(t => { const dl = formatDeadline(t.deadline); return dl && dl.isOverdue; }).length;
        const deferredCount = activeTasks.filter(t => (t.postpone_count || 0) >= 2).length;
        const ccOverdue = document.getElementById('cc-overdue-count');
        const ccDeferred = document.getElementById('cc-deferred-count');
        if (ccOverdue) ccOverdue.textContent = overdueCount;
        if (ccDeferred) ccDeferred.textContent = deferredCount;

        // ── INSIGHT ──
        const highPriority = activeTasks.filter(t => normalizePriority(t.priority) === 'high');
        const insight = document.getElementById('cc-insight');
        if (insight && highPriority.length > 0) {
            insight.textContent = `CRITICAL: ${highPriority.length} high-threat missions require immediate execution.`;
            insight.style.color = "var(--red)";
        } else if (insight) {
            insight.textContent = "System stable. High-priority execution recommended to maintain optimal momentum.";
            insight.style.color = "var(--text-body)";
        }
    }

    function updateIntegrityMeter() {
        const total = allTasks.length;
        const done = allTasks.filter(t => t.completed === true || t.status === 'completed' || t.status === 'done').length;
        const pct = total === 0 ? 0 : Math.round((done / total) * 100);

        const fill    = document.getElementById('integrity-fill');
        const pctEl   = document.getElementById('integrity-percent');
        const victory = document.getElementById('integrity-victory');

        if (fill)  fill.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${pct}% (${done}/${total})`;
        
        const ccPct = document.getElementById('cc-completion-pct');
        const ccActive = document.getElementById('cc-active-count');
        if (ccPct) ccPct.textContent = `${pct}%`;
        if (ccActive) ccActive.textContent = total - done;

        if (victory) {
            let msg = '';
            if (total === 0)     msg = 'Fresh start. Add your first win.';
            else if (done === 0) msg = 'Momentum building. Pick one.';
            else if (pct < 100)  msg = `${pct}% complete · ${total - done} missions remaining`;
            else                 msg = 'All missions complete. Outstanding execution.';
            
            victory.style.opacity = '0';
            setTimeout(() => { 
                victory.textContent = msg; 
                if (pct === 100 && total > 0) victory.style.color = 'var(--green)';
                else victory.style.color = '';
                victory.style.opacity = '1'; 
            }, 300);
        }
    }

    let currentTagFilter = null;

    // ═══════════════════════════════════════════════════════════
    // TASK ENRICHMENT — card row (E10), inline expand (E11), create panel (E12)
    // ═══════════════════════════════════════════════════════════
    const NL = String.fromCharCode(10);
    window.tfOpenSet = window.tfOpenSet || new Set();
    window.pendingLinks = window.pendingLinks || [];
    window.pendingChecklist = window.pendingChecklist || [];
    window.tfLinkType = window.tfLinkType || 'url';

    function tfEsc(s) {
        return (s == null ? '' : String(s))
            .split('&').join('&amp;')
            .split('<').join('&lt;')
            .split('>').join('&gt;')
            .split('"').join('&quot;')
            .split("'").join('&#39;');
    }
    function tfTrunc(s, n) { s = s || ''; return s.length > n ? s.slice(0, n - 1) + '…' : s; }
    function tfOneLine(s) { return (s || '').split(NL).join(' '); }
    function tfTypeIcon(type) {
        if (type === 'map') return '📍';
        if (type === 'reference') return '📄';
        if (type === 'file') return '📁';
        return '🔗';
    }

    // ── E10: pill row ──
    function tfEnrichmentRow(t) {
        const desc = t.description;
        const links = Array.isArray(t.links) ? t.links : [];
        const checklist = Array.isArray(t.checklist) ? t.checklist : [];
        const regLinks = links.filter(l => l.type !== 'map');
        const mapLinks = links.filter(l => l.type === 'map');
        let pills = '';
        if (desc) {
            pills += `<span class="enrich-pill ep-notes" title="${tfEsc(tfTrunc(tfOneLine(desc), 200))}"><span class="ep-ico">📝</span>Notes</span>`;
        }
        if (regLinks.length) {
            pills += `<span class="enrich-pill ep-links"><span class="ep-ico">🔗</span>${regLinks.length} link${regLinks.length > 1 ? 's' : ''}</span>`;
        }
        if (mapLinks.length) {
            pills += `<span class="enrich-pill ep-map" title="${tfEsc(tfTrunc(tfOneLine(mapLinks[0].title || mapLinks[0].url), 120))}"><span class="ep-ico">📍</span>Location</span>`;
        }
        if (checklist.length) {
            const done = checklist.filter(c => c.done).length;
            const total = checklist.length;
            const pct = total ? Math.round(done / total * 100) : 0;
            const cls = (done === total) ? 'all-done' : (done > 0 ? 'in-progress' : '');
            pills += `<span class="enrich-pill ep-check ${cls}"><span class="ep-ico">✓</span>${done}/${total}<span class="ep-bar"><i style="width:${pct}%"></i></span></span>`;
        }
        if (!pills) return '';
        return `<div class="enrich-row" onclick="event.stopPropagation(); tfToggleExpand(${t.id})">${pills}<span class="enrich-hint">View details <span class="chev">▾</span></span></div>`;
    }

    // ── E11: expanded detail ──
    function tfEnrichmentExpand(t) {
        const desc = t.description;
        const links = Array.isArray(t.links) ? t.links : [];
        const checklist = Array.isArray(t.checklist) ? t.checklist : [];
        if (!desc && !links.length && !checklist.length) return '';
        let html = '';
        if (desc) {
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Notes</span>` +
                    `<div class="enrich-notes-text">${tfEsc(desc)}</div></div>`;
        }
        if (links.length) {
            let rows = '';
            links.forEach(l => {
                const icoCls = 't-' + (l.type || 'url');
                const label = tfEsc(tfTrunc(l.title || l.url || '', 40));
                const isOpenable = (l.type === 'url' || l.type === 'map');
                const btn = isOpenable
                    ? `<button class="enrich-link-btn open" onclick="event.stopPropagation(); tfOpenLink(${t.id}, '${l.id}')">Open →</button>`
                    : `<button class="enrich-link-btn copy" onclick="event.stopPropagation(); tfCopyLink(${t.id}, '${l.id}', this)">Copy</button>`;
                rows += `<div class="enrich-link-row"><span class="elr-ico ${icoCls}">${tfTypeIcon(l.type)}</span>` +
                        `<span class="elr-label" title="${tfEsc(l.url || '')}">${label}</span>` +
                        `<span class="elr-id">${tfEsc(l.id)}</span>${btn}</div>`;
            });
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Links &amp; References</span>${rows}</div>`;
        }
        if (checklist.length) {
            const done = checklist.filter(c => c.done).length;
            const total = checklist.length;
            const pct = total ? Math.round(done / total * 100) : 0;
            const fillCls = (done === total) ? ' complete' : '';
            let items = '';
            checklist.forEach(c => {
                const checked = c.done ? ' checked' : '';
                const doneRow = c.done ? ' done' : '';
                items += `<div class="enrich-chk-row${doneRow}">` +
                         `<span class="enrich-cbx${checked}" onclick="event.stopPropagation(); tfToggleChecklist(${t.id}, '${c.id}', this)">` +
                         `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>` +
                         `</span><span class="enrich-chk-text">${tfEsc(c.text || '')}</span></div>`;
            });
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Checklist (${done}/${total})</span>` +
                    `<div class="enrich-prog-track"><div class="enrich-prog-fill${fillCls}" style="width:${pct}%"></div></div>${items}</div>`;
        }
        html += `<button class="enrich-collapse" onclick="event.stopPropagation(); tfToggleExpand(${t.id})">▲ Hide details</button>`;
        const openCls = window.tfOpenSet.has(t.id) ? ' open' : '';
        return `<div class="enrich-expand${openCls}" onclick="event.stopPropagation()">${html}</div>`;
    }

    function tfBuildEnrichZone(t) {
        const row = tfEnrichmentRow(t);
        if (!row) return '';
        const openCls = window.tfOpenSet.has(t.id) ? ' open' : '';
        return `<div class="enrich-zone${openCls}" data-eid="${t.id}">${row}${tfEnrichmentExpand(t)}</div>`;
    }

    // Enrichment shown inside the Mission Briefing modal (always-expanded, interactive)
    function tfBriefEnrichment(t) {
        const desc = t.description;
        const links = Array.isArray(t.links) ? t.links : [];
        const checklist = Array.isArray(t.checklist) ? t.checklist : [];
        if (!desc && !links.length && !checklist.length) return '';
        let html = '';
        if (desc) {
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Notes</span>` +
                    `<div class="enrich-notes-text" style="background:var(--bg-primary);border:1px solid var(--border-subtle);border-radius:8px;padding:12px 14px;max-height:160px;">${tfEsc(desc)}</div></div>`;
        }
        if (links.length) {
            let rows = '';
            links.forEach(l => {
                const icoCls = 't-' + (l.type || 'url');
                const label = tfEsc(tfTrunc(l.title || l.url || '', 40));
                const isOpenable = (l.type === 'url' || l.type === 'map');
                const btn = isOpenable
                    ? `<button class="enrich-link-btn open" onclick="tfOpenLink(${t.id}, '${l.id}')">Open →</button>`
                    : `<button class="enrich-link-btn copy" onclick="tfCopyLink(${t.id}, '${l.id}', this)">Copy</button>`;
                rows += `<div class="enrich-link-row"><span class="elr-ico ${icoCls}">${tfTypeIcon(l.type)}</span>` +
                        `<span class="elr-label" title="${tfEsc(l.url || '')}">${label}</span>` +
                        `<span class="elr-id">${tfEsc(l.id)}</span>${btn}</div>`;
            });
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Links &amp; References</span>${rows}</div>`;
        }
        if (checklist.length) {
            const done = checklist.filter(c => c.done).length;
            const total = checklist.length;
            const pct = total ? Math.round(done / total * 100) : 0;
            const fillCls = (done === total) ? ' complete' : '';
            let items = '';
            checklist.forEach(c => {
                const checked = c.done ? ' checked' : '';
                const doneRow = c.done ? ' done' : '';
                items += `<div class="enrich-chk-row${doneRow}">` +
                         `<span class="enrich-cbx${checked}" onclick="tfToggleChecklist(${t.id}, '${c.id}', this)">` +
                         `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>` +
                         `</span><span class="enrich-chk-text">${tfEsc(c.text || '')}</span></div>`;
            });
            html += `<div class="enrich-sub"><span class="enrich-sub-label">Checklist (${done}/${total})</span>` +
                    `<div class="enrich-prog-track"><div class="enrich-prog-fill${fillCls}" style="width:${pct}%"></div></div>${items}</div>`;
        }
        return html;
    }
    window.tfRefreshBriefEnrichment = function() {
        if (!window._briefTaskId) return;
        const box = document.getElementById('brief-enrich');
        if (!box) return;
        const t = allTasks.find(x => x.id === window._briefTaskId);
        if (t) box.innerHTML = tfBriefEnrichment(t);
    };

    window.tfToggleExpand = function(taskId) {
        const zone = document.querySelector(`.enrich-zone[data-eid="${taskId}"]`);
        if (!zone) return;
        const expand = zone.querySelector('.enrich-expand');
        const isOpen = zone.classList.toggle('open');
        if (expand) expand.classList.toggle('open', isOpen);
        if (isOpen) window.tfOpenSet.add(taskId); else window.tfOpenSet.delete(taskId);
    };

    function tfRefreshEnrichZone(taskId) {
        const zone = document.querySelector(`.enrich-zone[data-eid="${taskId}"]`);
        if (!zone) return null;
        const t = allTasks.find(x => x.id === taskId);
        if (!t) return null;
        const tmp = document.createElement('div');
        tmp.innerHTML = tfBuildEnrichZone(t);
        const fresh = tmp.firstElementChild;
        if (fresh) zone.replaceWith(fresh);
        return fresh;
    }

    window.tfToggleChecklist = async function(taskId, chkId, cbxEl) {
        try {
            const res = await fetch(`/api/tasks/${taskId}/checklist/${chkId}/toggle`, { method: 'PATCH' });
            if (!res.ok) { showToast('Could not update checklist', 'var(--red)'); return; }
            const updated = await res.json();
            const idx = allTasks.findIndex(x => x.id === taskId);
            const wasAllDone = idx >= 0 && allTasks[idx].checklist_total > 0 && allTasks[idx].checklist_done === allTasks[idx].checklist_total;
            if (idx >= 0) allTasks[idx] = Object.assign({}, allTasks[idx], updated);
            const nowAllDone = updated.checklist_total > 0 && updated.checklist_done === updated.checklist_total;
            const fresh = tfRefreshEnrichZone(taskId);
            if (window._briefTaskId === taskId && window.tfRefreshBriefEnrichment) tfRefreshBriefEnrichment();
            if (nowAllDone && !wasAllDone) {
                let track = null;
                const briefBox = document.getElementById('brief-enrich');
                if (window._briefTaskId === taskId && briefBox) track = briefBox.querySelector('.enrich-prog-track');
                if (!track && fresh) track = fresh.querySelector('.enrich-prog-track');
                if (track) {
                    tfConfetti(track);
                    const csub = track.closest('.enrich-sub');
                    if (csub) { csub.classList.add('enrich-flash'); setTimeout(() => csub.classList.remove('enrich-flash'), 400); }
                }
            }
        } catch (e) { showToast('Network error', 'var(--red)'); }
    };

    window.tfOpenLink = function(taskId, linkId) {
        const t = allTasks.find(x => x.id === taskId); if (!t) return;
        const l = (t.links || []).find(x => x.id === linkId); if (!l) return;
        const href = safeHref(l.url);   // SEC-01: block javascript:/data: link execution
        if (href === '#') { showToast('Blocked unsafe link', 'var(--red)'); return; }
        window.open(href, '_blank', 'noopener,noreferrer');
    };
    window.tfCopyLink = function(taskId, linkId, btn) {
        const t = allTasks.find(x => x.id === taskId); if (!t) return;
        const l = (t.links || []).find(x => x.id === linkId); if (!l) return;
        const done = () => { const o = btn.textContent; btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = o; }, 1500); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(l.url).then(done).catch(() => showToast('Copy failed', 'var(--red)'));
        else showToast(l.url, 'var(--blue)');
    };

    function tfConfetti(anchorEl) {
        const colors = ['var(--green)', 'var(--blue)'];
        const host = anchorEl.parentElement || anchorEl;
        if (getComputedStyle(host).position === 'static') host.style.position = 'relative';
        for (let i = 0; i < 6; i++) {
            const p = document.createElement('span');
            p.className = 'enrich-confetti-piece';
            p.style.background = colors[i % 2];
            p.style.left = (10 + Math.random() * 80) + '%';
            p.style.top = '0px';
            p.style.setProperty('--cx', (Math.random() * 40 - 20) + 'px');
            p.style.setProperty('--cy', -(30 + Math.random() * 20) + 'px');
            p.style.setProperty('--cr', (Math.random() * 360) + 'deg');
            p.style.animation = 'enrichConfetti 550ms ease-out forwards';
            host.appendChild(p);
            setTimeout(() => p.remove(), 600);
        }
    }

    // ── E12: create-mission panel helpers ──
    window.tfSelectLinkType = function(btn, type) {
        window.tfLinkType = type;
        btn.parentElement.querySelectorAll('.enrich-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const input = document.getElementById('mission-link-input');
        const ph = { url: 'https://...', map: 'Maps link or location name...', reference: 'Document title, book, person...', file: '/path/to/file or filename...' };
        if (input) input.placeholder = ph[type] || 'https://...';
    };
    window.tfAddLink = function() {
        const input = document.getElementById('mission-link-input');
        const titleInput = document.getElementById('mission-link-title');
        if (!input) return;
        const val = input.value.trim();
        if (!val) return;
        if (window.pendingLinks.length >= 10) { showToast('Maximum 10 links', 'var(--amber)'); return; }
        window.pendingLinks.push({ type: window.tfLinkType, url: val, title: (titleInput && titleInput.value.trim()) || null });
        input.value = ''; if (titleInput) titleInput.value = '';
        tfRenderLinkChips(); input.focus();
    };
    window.tfRemoveLink = function(idx) {
        const chips = document.getElementById('mission-links-list');
        const chip = chips ? chips.children[idx] : null;
        if (chip) { chip.classList.add('removing'); setTimeout(() => { window.pendingLinks.splice(idx, 1); tfRenderLinkChips(); }, 150); }
        else { window.pendingLinks.splice(idx, 1); tfRenderLinkChips(); }
    };
    function tfRenderLinkChips() {
        const box = document.getElementById('mission-links-list');
        if (!box) return;
        box.innerHTML = window.pendingLinks.map((l, i) =>
            `<span class="enrich-chip"><span class="ec-ico t-${l.type}">${tfTypeIcon(l.type)}</span>` +
            `<span class="ec-val" title="${tfEsc(l.url)}">${tfEsc(tfTrunc(l.title || l.url, 40))}</span>` +
            `<span class="ec-x" onclick="tfRemoveLink(${i})">×</span></span>`
        ).join('');
        if (window.tfUpdateProgressDots) tfUpdateProgressDots();
    }
    window.tfAddChecklistItem = function() {
        const input = document.getElementById('mission-checklist-input');
        if (!input) return;
        const val = input.value.trim();
        if (!val) return;
        if (window.pendingChecklist.length >= 20) { showToast('Maximum 20 items', 'var(--amber)'); return; }
        window.pendingChecklist.push(val);
        input.value = ''; tfRenderChecklistBuild(); input.focus();
    };
    window.tfRemoveChecklistItem = function(idx) { window.pendingChecklist.splice(idx, 1); tfRenderChecklistBuild(); };
    function tfRenderChecklistBuild() {
        const box = document.getElementById('mission-checklist-list');
        if (!box) return;
        box.innerHTML = window.pendingChecklist.map((txt, i) =>
            `<div class="enrich-build-item" draggable="true" data-idx="${i}" ` +
            `ondragstart="tfDragStart(event,${i})" ondragover="tfDragOver(event,${i})" ondragleave="tfDragLeave(event)" ondrop="tfDrop(event,${i})" ondragend="tfDragEnd(event)">` +
            `<span class="ebi-grip">⋮⋮</span><span class="ebi-box"></span>` +
            `<span class="ebi-text">${tfEsc(txt)}</span><span class="ebi-x" onclick="tfRemoveChecklistItem(${i})">×</span></div>`
        ).join('');
        if (window.tfUpdateProgressDots) tfUpdateProgressDots();
    }
    window._tfDragIdx = null;
    window.tfDragStart = function(e, i) { window._tfDragIdx = i; if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'; };
    window.tfDragOver = function(e, i) { e.preventDefault(); if (e.currentTarget) e.currentTarget.classList.add('drag-over'); };
    window.tfDragLeave = function(e) { if (e.currentTarget) e.currentTarget.classList.remove('drag-over'); };
    window.tfDrop = function(e, i) {
        e.preventDefault();
        const from = window._tfDragIdx;
        if (from == null || from === i) { window.tfDragEnd(e); return; }
        const arr = window.pendingChecklist;
        const moved = arr.splice(from, 1)[0];
        arr.splice(i, 0, moved);
        window._tfDragIdx = null;
        tfRenderChecklistBuild();
    };
    window.tfDragEnd = function(e) { document.querySelectorAll('.enrich-build-item').forEach(el => el.classList.remove('drag-over')); window._tfDragIdx = null; };

    window.tfAutoGrow = function(el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px'; };
    window.tfNotesCounter = function(el) {
        const c = document.getElementById('mission-notes-counter');
        if (!c) return;
        const n = el.value.length;
        if (n > 0) { c.textContent = n + ' chars'; c.classList.add('show'); }
        else { c.textContent = ''; c.classList.remove('show'); }
    };
    window.tfResetEnrichmentPanel = function() {
        const notes = document.getElementById('mission-notes');
        if (notes) { notes.value = ''; notes.style.height = 'auto'; }
        const counter = document.getElementById('mission-notes-counter'); if (counter) { counter.textContent = ''; counter.classList.remove('show'); }
        const li = document.getElementById('mission-link-input'); if (li) li.value = '';
        const lt = document.getElementById('mission-link-title'); if (lt) lt.value = '';
        const ci = document.getElementById('mission-checklist-input'); if (ci) ci.value = '';
        window.pendingLinks = []; window.pendingChecklist = []; window.tfLinkType = 'url';
        document.querySelectorAll('.enrich-type-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-ltype') === 'url'));
        tfRenderLinkChips(); tfRenderChecklistBuild();
    };

    function renderTaskList() {
        try {
            const container = document.getElementById('task-list-container');
            if (!container) {
                console.error("task-list-container not found!");
                return;
            }

            // 1. Record current positions (First)
            const oldWraps = Array.from(container.querySelectorAll('.task-card-wrap'));
            const rects = new Map();
            oldWraps.forEach(wrap => {
                const card = wrap.querySelector('.task-card');
                if (card) rects.set(wrap.dataset.id, card.getBoundingClientRect());
            });

            const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);
            const filtered = activeTasks.filter(t => {
                const p = normalizePriority(t.priority);
                
                let tTags = [];
                if (t.tags) {
                    if (Array.isArray(t.tags)) tTags = t.tags;
                    else if (typeof t.tags === 'string') tTags = t.tags.split(',').map(s=>s.trim());
                }

                if (currentFilter === 'tagged' && currentTagFilter) return tTags.includes(currentTagFilter);
                if (currentFilter === 'all')    return true;
                if (currentFilter === 'high')   return p === 'high' || t.deadline_type === 'hard';
                if (currentFilter === 'medium') return p === 'medium' && t.deadline_type !== 'hard';
                if (currentFilter === 'low')    return p === 'low';
                return true;
            });


            // Sort tasks
            filtered.sort((a, b) => {
                if (currentSortMode === 'urgency') {
                    const pa = getPressureLevel(a), pb = getPressureLevel(b);
                    if (pa !== pb) return pb - pa;
                    const priOrder = {high:0, medium:1, low:2};
                    return (priOrder[normalizePriority(a.priority)]||1) - (priOrder[normalizePriority(b.priority)]||1);
                } else if (currentSortMode === 'priority') {
                    const priOrder = {high:0, medium:1, low:2};
                    return (priOrder[normalizePriority(a.priority)]||1) - (priOrder[normalizePriority(b.priority)]||1);
                } else {
                    return (b.id || 0) - (a.id || 0);
                }
            });

            renderTagSignals();
            updateFilterCounts();
            const countEl = document.getElementById('header-task-count');
            if (countEl) countEl.textContent = `${filtered.length} ACTIVE`;

            // 2. Render new DOM with Phase 1 card layout
            container.innerHTML = filtered.map((t) => {
                const np = normalizePriority(t.priority);
                const dl = formatDeadline(t.deadline);
                const pressure = dl ? dl.pressureLevel : 0;
                const isOverdue = dl ? dl.isOverdue : false;

                // Duration badge
                const durBadge = t.duration ? `<span class="duration-badge">[${t.duration}]</span>` : '';

                // Overdue chip
                const overdueChip = isOverdue ? `<span class="overdue-chip">OVERDUE</span>` : '';

                // Postpone badge
                let postponeBadge = '';
                if ((t.postpone_count || 0) >= 2) {
                    const pc = t.postpone_count;
                    const cls = pc >= 3 ? 'warn' : 'mild';
                    const warn = pc >= 5 ? ' ⚠⚠' : pc >= 3 ? ' ⚠' : '';
                    
                    // Hover relative time tooltip helper
                    let tooltip = '';
                    if (t.postpone_history && t.postpone_history.length > 0) {
                        try {
                            const lastEntry = t.postpone_history[t.postpone_history.length - 1];
                            let dateStr = lastEntry;
                            if (lastEntry.startsWith('{')) {
                                const parsed = JSON.parse(lastEntry);
                                dateStr = parsed.date;
                            }
                            const lastDate = new Date(dateStr);
                            if (!isNaN(lastDate.getTime())) {
                                const diffMs = new Date() - lastDate;
                                const diffMin = Math.floor(diffMs / 60000);
                                const diffHr = Math.floor(diffMs / 3600000);
                                const diffDays = Math.floor(diffMs / 86400000);
                                if (diffMin < 1) tooltip = 'just now';
                                else if (diffMin < 60) tooltip = `${diffMin}m ago`;
                                else if (diffHr < 24) tooltip = `${diffHr}h ago`;
                                else tooltip = `${diffDays}d ago`;
                                tooltip = `Last postponed: ${tooltip}`;
                            }
                        } catch(err) {}
                    }
                    
                    postponeBadge = `<span class="postpone-badge ${cls}" title="${tooltip}">postponed ×${pc}${warn}</span>`;
                }

                // Deadline row
                let deadlineRow = '';
                if (dl) {
                    const hardTag = t.deadline_type === 'hard' ? '<span class="hard-tag">⚠ HARD</span>' : '';
                    deadlineRow = `<div class="deadline-row" style="color:${dl.color}">⏰ ${dl.text} ${hardTag}</div>`;
                }

                // Event badge
                let eventBadge = '';
                if (t.mission_type === 'Event') {
                    const timeRange = (t.start_time && t.end_time) ? ` · ${t.start_time} – ${t.end_time}` : '';
                    const dateStr = t.date ? ` · ${t.date}` : '';
                    eventBadge = `<span class="badge" style="background:color-mix(in srgb, var(--accent-ai) 15%, transparent);color:var(--ai-purple);border:1px solid color-mix(in srgb, var(--accent-ai) 30%, transparent);">📅 EVENT${dateStr}${timeRange}</span>`;
                }

                // Pressure + overdue CSS classes
                let pressureClass = pressure > 0 ? ` pressure-${pressure}` : '';
                let overdueClass = isOverdue ? ' overdue-card' : '';
                let wrapExtra = (pressure >= 3 && t.deadline_type === 'hard') ? ' hard-deadline-urgent' : '';

                // Recovery mode classes
                let recoveryClass = '';
                if (recoveryActive) {
                    if (recoveryTaskIds.includes(t.id)) recoveryClass = ' recovery-highlighted';
                    else recoveryClass = ' recovery-suppressed';
                }
                const recoveryBadge = (recoveryActive && recoveryTaskIds.includes(t.id))
                    ? `<span class="rec-focus-badge">FOCUS NOW</span>` : '';
                const recoveryComplete = (recoveryActive && recoveryTaskIds.includes(t.id))
                    ? `<button class="rec-card-complete" onclick="event.stopPropagation(); tfRecMarkComplete(${t.id})">✓ Mark as complete</button>` : '';

                return `
                <div class="task-card-wrap priority-${np}${wrapExtra}" data-id="${t.id}">
                    <div class="task-card priority-${np}${pressureClass}${overdueClass}${recoveryClass}" data-id="${t.id}"
                         onclick="openModal(${t.id}, this)">
                        <div class="card-top">
                            <div class="cb" onclick="event.stopPropagation(); completeTask(${t.id}, this)"></div>
                            <div class="task-title">${escapeHtml(t.title)}</div>
                            ${durBadge}${overdueChip}${recoveryBadge}
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px;padding-left:28px;">
                            <span class="badge ${np}">${(t.priority||'Medium').toUpperCase()}</span>
                            ${(t.tags||[]).map(tg => {
                                const tgArg = String(tg).replace(/[^a-zA-Z0-9_\- ]/g, '');   // BUG-04: JS-string-safe
                                return '<span class="badge tag" onclick="event.stopPropagation(); filterByTag(\'' + tgArg + '\')">#' + escapeHtml(tg) + '</span>';
                            }).join('')}
                            ${postponeBadge}
                        </div>
                        ${deadlineRow ? '<div style="padding-left:28px;">' + deadlineRow + '</div>' : ''}
                        ${tfBuildEnrichZone(t)}${recoveryComplete}
                    </div>
                        <div class="task-action-strip">
                            <div class="action-icon" onclick="event.stopPropagation(); startFocusFromCard(${t.id}, this)" title="Deploy Focus Protocol">
                                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                            <div class="action-icon purge" onclick="event.stopPropagation(); purgeTask(${t.id}, this)" title="Purge Mission Records">
                                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // 3. FLIP Playback
            const newWraps = Array.from(container.querySelectorAll('.task-card-wrap'));
            newWraps.forEach((wrap, i) => {
                const card = wrap.querySelector('.task-card');
                const id = wrap.dataset.id;
                const oldRect = rects.get(id);
                if (oldRect) {
                    const newRect = card.getBoundingClientRect();
                    const dy = oldRect.top - newRect.top;
                    card.style.transform = `translateY(${dy}px)`;
                    card.style.transition = 'none';
                    card.style.opacity = '1'; // Keep existing cards fully visible

                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            card.style.transition = 'transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)';
                            card.style.transform = 'translateY(0)';
                        });
                    });
                } else {
                    card.style.transitionDelay = `${(i % 10) * 50}ms`;
                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            card.classList.add('cascade-visible');
                            // Reset transition delay after cascade so it doesn't delay future interactions
                            setTimeout(() => { card.style.transitionDelay = '0ms'; }, ((i % 10) * 50) + 450);
                        });
                    });
                }
            });

            // Cleanup inline transitions so hover effect still works
            setTimeout(() => {
                container.querySelectorAll('.task-card').forEach(card => {
                    if (card.style.transition) card.style.transition = '';
                });
            }, 450);
        } catch(e) {
            console.error("renderTaskList failed:", e);
            showToast('TaskList Render Error: ' + e.message, 'var(--red)');
        }
    }

    function filterTasks(crit, element) {
        currentFilter = crit;
        currentTagFilter = null;
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        if (element) element.classList.add('active');
        renderTaskList();
    }

    function updateFilterCounts() {
        const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);
        const all = activeTasks.length;
        const high = activeTasks.filter(t => normalizePriority(t.priority)==='high' || t.deadline_type==='hard').length;
        const med = activeTasks.filter(t => normalizePriority(t.priority)==='medium' && t.deadline_type!=='hard').length;
        const low = activeTasks.filter(t => normalizePriority(t.priority)==='low').length;
        const el = (id, v) => { const e = document.getElementById(id); if(e) e.textContent = v; };
        el('fc-count-all', all); el('fc-count-high', high); el('fc-count-medium', med); el('fc-count-low', low);
    }

    window.setSortMode = function(mode, el) {
        currentSortMode = mode;
        document.querySelectorAll('.sort-chip').forEach(c => c.classList.remove('active'));
        if (el) el.classList.add('active');
        renderTaskList();
    };

    // ── PHASE 1: LIVE PRESSURE UPDATES ────────────────────────────────
    function updateAllPressureLevels() {
        document.querySelectorAll('.task-card').forEach(card => {
            const id = card.dataset.id;
            const task = allTasks.find(t => String(t.id) === String(id));
            if (!task) return;
            const pressure = getPressureLevel(task);
            card.classList.remove('pressure-1','pressure-2','pressure-3','overdue-card');
            const wrap = card.closest('.task-card-wrap');
            if (wrap) wrap.classList.remove('hard-deadline-urgent');
            const dl = formatDeadline(task.deadline);
            if (dl && dl.isOverdue) card.classList.add('overdue-card');
            if (pressure > 0) card.classList.add('pressure-' + pressure);
            if (pressure >= 3 && task.deadline_type === 'hard' && wrap) wrap.classList.add('hard-deadline-urgent');
            // Update deadline text if exists
            const dlRow = card.querySelector('.deadline-row');
            if (dlRow && dl) { dlRow.style.color = dl.color; dlRow.innerHTML = '⏰ ' + dl.text + (task.deadline_type==='hard'?' <span class="hard-tag">⚠ HARD</span>':''); }
        });
    }

    // ── PHASE 1: RECOVERY MODE ────────────────────────────────────────
    let tfRecWasActive = false;
    async function checkRecoveryStatus() {
        try {
            const res = await fetch('/api/recovery-status');
            if (!res.ok) return;
            const state = await res.json();
            const nowActive = !!state.active;
            recoveryActive = nowActive;
            recoveryTaskIds = (state.session_tasks || []).map(t => typeof t === 'object' ? t.id : t);
            window.tfRecCompleted = (state.completed_in_recovery || []).length;
            const banner = document.getElementById('recovery-banner');
            if (recoveryActive) {
                if (banner) banner.classList.add('active');
                document.body.style.background = 'var(--bg-deep)';
            } else {
                if (banner) banner.classList.remove('active');
                document.body.style.background = '';
            }
            // T5: dim sidebar nav (except Control Center + Missions) while in recovery
            document.querySelectorAll('.nav-item').forEach(el => {
                const keep = el.id === 'nav-dashboard' || el.id === 'nav-tasks';
                el.style.opacity = (recoveryActive && !keep) ? '0.35' : '';
            });
            tfRecApplyState();
            if (nowActive !== tfRecWasActive) {
                tfRecWasActive = nowActive;
                try { renderTaskList(); } catch(e) {}
            }
        } catch(e) { /* recovery endpoint not available yet, ignore */ }
    }

    // ═══════════════════════════════════════════════════════════
    // RECOVERY MODE — UI LAYER (entry points, dialogs, auto-trigger)
    // ═══════════════════════════════════════════════════════════
    function tfRecApplyState() {
        const active = !!recoveryActive;
        const navItem = document.getElementById('rec-nav-item');
        if (navItem) {
            navItem.classList.toggle('active', active);
            const txt = document.getElementById('rec-nav-text');
            if (txt) txt.textContent = active ? 'Recovery · ACTIVE' : 'Recovery';
            navItem.title = active ? 'Recovery Mode active' : 'Activate Recovery Mode';
        }
        const salv = document.getElementById('rec-salvage-btn');
        if (salv) {
            salv.classList.toggle('active', active);
            const st = document.getElementById('rec-salvage-text');
            if (st) st.textContent = active ? 'RECOVERY ACTIVE · EXIT' : 'SALVAGE MY DAY';
        }
        const ctx = document.getElementById('rec-context-box');
        if (ctx) ctx.style.display = active ? 'block' : 'none';
    }

    function tfRecBackdrop() {
        let b = document.getElementById('rec-backdrop');
        if (!b) {
            b = document.createElement('div');
            b.id = 'rec-backdrop'; b.className = 'rec-backdrop';
            b.addEventListener('click', e => { if (e.target === b) tfRecCloseDialog(); });
            document.body.appendChild(b);
        }
        return b;
    }
    window.tfRecCloseDialog = function() { const b = document.getElementById('rec-backdrop'); if (b) b.remove(); };

    async function tfRecPreviewRows() {
        try {
            const res = await fetch('/api/recovery-preview');
            const data = await res.json();
            const tasks = data.preview_tasks || [];
            if (!tasks.length) return '<div style="color:var(--text-disabled);font-size:12px;margin-top:8px;">No actionable tasks found.</div>';
            return tasks.map(t => {
                const np = normalizePriority(t.priority);
                const dur = t.duration ? `<span class="rec-prow-dur">[${t.duration}]</span>` : '';
                return `<div class="rec-preview-row"><span class="rec-pdot ${np}"></span><span class="rec-prow-title">${tfEsc(t.title)}</span>${dur}</div>`;
            }).join('');
        } catch(e) { return ''; }
    }

    window.tfRecEntryConfirm = async function() {
        if (recoveryActive) { tfRecExitConfirm(); return; }
        const b = tfRecBackdrop();
        b.innerHTML = '<div class="rec-dialog"><div class="rec-d-icon" style="color:var(--amber);">⚡</div><div class="rec-d-title">Activate Recovery Mode?</div><div class="rec-d-desc">Loading…</div></div>';
        const rows = await tfRecPreviewRows();
        b.innerHTML = `<div class="rec-dialog">
            <div class="rec-d-icon" style="color:var(--amber);">⚡</div>
            <div class="rec-d-title">Activate Recovery Mode?</div>
            <div class="rec-d-desc">This will simplify your view to focus on your 2 most important incomplete tasks. Everything else will fade out. You can exit anytime.</div>
            <div class="rec-d-label">Focusing on:</div>
            ${rows}
            <button class="rec-btn-primary" onclick="tfRecActivate('D')">Yes, salvage my day</button>
            <button class="rec-btn-secondary" onclick="tfRecCloseDialog()">Not now</button>
        </div>`;
    };

    window.tfRecExitConfirm = function() {
        const b = tfRecBackdrop();
        b.innerHTML = `<div class="rec-dialog">
            <div class="rec-d-icon" style="color:var(--text-muted);">←</div>
            <div class="rec-d-title">Exit Recovery Mode?</div>
            <div class="rec-d-desc">All tasks will become visible again. You'll lose the simplified view.</div>
            <button class="rec-btn-primary rec-btn-exit" onclick="tfRecExit(false)">Yes, exit recovery</button>
            <button class="rec-btn-secondary rec-btn-stay" onclick="tfRecCloseDialog()">Keep going — stay focused</button>
        </div>`;
    };

    window.tfRecActivate = async function(reason) {
        tfRecCloseDialog();
        try {
            const res = await fetch('/api/recovery-activate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({trigger_reason: reason})});
            if (res.ok) { await checkRecoveryStatus(); try { renderTaskList(); } catch(e) {} if (typeof showToast === 'function') showToast('Recovery Mode active.', 'var(--amber)'); }
        } catch(e) { if (typeof showToast === 'function') showToast('Could not activate recovery', 'var(--red)'); }
    };

    window.tfRecExit = async function(isAuto) {
        tfRecCloseDialog();
        try {
            const res = await fetch('/api/recovery-exit', {method:'POST'});
            let wasSuccessful = false;
            if (res.ok) { const d = await res.json().catch(()=>({})); wasSuccessful = !!d.was_successful; }
            const completed = window.tfRecCompleted || 0;
            await checkRecoveryStatus();
            try { renderTaskList(); } catch(e) {}
            if (wasSuccessful || completed > 0) tfRecSetBadge(completed);
        } catch(e) {}
    };

    window.tfRecSidebarClick = function() {
        if (recoveryActive) { if (typeof showView === 'function') showView('tasks'); }
        else tfRecEntryConfirm();
    };
    window.tfRecSalvageClick = function() { recoveryActive ? tfRecExitConfirm() : tfRecEntryConfirm(); };

    window.tfRecMarkComplete = async function(taskId) {
        try { await fetch(`/api/tasks/${taskId}/complete`, {method:'POST'}); } catch(e) {}
        const before = recoveryActive;
        try { await loadTasks(); } catch(e) {}
        await checkRecoveryStatus();
        try { renderTaskList(); } catch(e) {}
        if (before && !recoveryActive) { tfRecCelebrate(); tfRecSetBadge(window.tfRecCompleted || 0); }
    };

    function tfRecCelebrate() {
        const o = document.createElement('div');
        o.className = 'rec-celebrate';
        o.innerHTML = '<div class="rc-check">✓</div><div class="rc-big">You saved the day.</div><div class="rc-sub">Day recovered.</div>';
        document.body.appendChild(o);
        setTimeout(() => o.remove(), 2600);
    }

    function tfRecSetBadge(n) {
        const now = new Date();
        const hhmm = now.toTimeString().slice(0, 5);
        const today = now.toISOString().split('T')[0];
        localStorage.setItem('recovery_completed_today', today + '|' + hhmm + '|' + n);
        tfRecRenderBadge(hhmm, n);
    }
    function tfRecRenderBadge(hhmm, n) {
        const badge = document.getElementById('post-rec-badge');
        if (!badge) return;
        badge.style.display = 'flex';
        const sub = document.getElementById('post-rec-badge-sub');
        if (sub) sub.textContent = hhmm + ' · ' + n + ' completed in recovery';
    }
    function tfRecRestoreBadge() {
        try {
            const v = localStorage.getItem('recovery_completed_today');
            if (!v) return;
            const parts = v.split('|');
            const today = new Date().toISOString().split('T')[0];
            if (parts[0] === today) tfRecRenderBadge(parts[1], parts[2]);
        } catch(e) {}
    }

    function tfRecShowPrewarn() {
        if (document.getElementById('rec-prewarn')) return;
        const main = document.querySelector('.col-main') || document.body;
        const el = document.createElement('div');
        el.id = 'rec-prewarn'; el.className = 'rec-prewarn';
        el.innerHTML = '<span style="color:var(--amber);font-size:14px;">⏳</span>' +
            '<span class="rec-pw-mid"><span style="color:var(--amber);">You haven\'t completed anything today.</span> <span style="color:var(--text-muted);">Focus window closing.</span></span>' +
            '<button class="rec-pw-link" onclick="tfRecActivate(\'D\')">Salvage my day →</button>' +
            '<button class="rec-pw-x" onclick="tfRecDismissPrewarn()">×</button>';
        main.insertBefore(el, main.firstChild);
        localStorage.setItem('recovery_warned_date', new Date().toISOString().split('T')[0]);
    }
    window.tfRecDismissPrewarn = function() {
        const el = document.getElementById('rec-prewarn'); if (el) el.remove();
        localStorage.setItem('recovery_warned_date', new Date().toISOString().split('T')[0]);
    };

    async function tfRecShowSheet() {
        if (document.getElementById('rec-sheet')) return;
        const incomplete = allTasks.filter(t => !t.completed && !t.dropped_at && !t.offloaded_at).length;
        const rows = await tfRecPreviewRows();
        const el = document.createElement('div');
        el.id = 'rec-sheet'; el.className = 'rec-sheet';
        el.innerHTML = '<div class="rec-sheet-handle"></div>' +
            '<div style="display:flex;justify-content:space-between;align-items:center;">' +
            '<span style="color:var(--amber);font-size:20px;">⚡</span>' +
            '<button class="rec-pw-x" onclick="tfRecDismissSheet(true)">×</button></div>' +
            '<div style="font-size:20px;color:var(--text-hero);margin-top:8px;">Today\'s been difficult.</div>' +
            '<div style="font-size:14px;color:var(--text-muted);margin-top:4px;">You have ' + incomplete + ' incomplete tasks. Want to simplify?</div>' +
            rows +
            '<button class="rec-btn-primary" onclick="tfRecDismissSheet(false); tfRecActivate(\'auto_6pm\')">Activate Recovery Mode</button>' +
            '<button class="rec-btn-secondary" onclick="tfRecDismissSheet(true)">Not now</button>';
        document.body.appendChild(el);
    }
    window.tfRecDismissSheet = function(setDismiss) {
        const el = document.getElementById('rec-sheet'); if (el) el.remove();
        if (setDismiss !== false) localStorage.setItem('recovery_auto_dismissed_date', new Date().toISOString().split('T')[0]);
    };

    async function checkAutoTrigger() {
        try {
            const now = new Date();
            const hour = now.getHours();
            const day = now.getDay();
            if (day === 0 || day === 6) return;      // weekend
            if (recoveryActive) return;               // already active
            const today = now.toISOString().split('T')[0];
            const warned = localStorage.getItem('recovery_warned_date');
            const dismissed = localStorage.getItem('recovery_auto_dismissed_date');
            const incomplete = allTasks.filter(t => !t.completed && !t.dropped_at && !t.offloaded_at).length;
            if (incomplete < 1) return;               // nothing to salvage
            if (hour >= 17 && warned !== today) {
                const r = await fetch('/api/tasks/completed-today'); const d = await r.json();
                if ((d.count || 0) === 0) tfRecShowPrewarn();
            }
            if (hour >= 18 && dismissed !== today && warned !== today) {
                const r = await fetch('/api/tasks/completed-today'); const d = await r.json();
                if ((d.count || 0) === 0) tfRecShowSheet();
            }
        } catch(e) {}
    }

    // ── PHASE 1: REMINDER TOASTS ──────────────────────────────────────
    function checkReminders() {
        const stack = document.getElementById('reminder-stack');
        if (!stack) return;
        const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);
        const due = activeTasks.filter(t => t.reminder_fired && !t.reminder_dismissed);
        stack.innerHTML = '';
        due.slice(0, 3).forEach(t => {
            const dl = formatDeadline(t.deadline);
            const isHard = t.deadline_type === 'hard';
            const dlText = dl ? dl.text : '';
            const dlColor = dl ? dl.color : 'var(--text-muted)';
            stack.innerHTML += `
            <div class="reminder-toast${isHard?' hard-reminder':''}" id="reminder-${t.id}">
                <div class="toast-header">
                    <span class="toast-label${isHard?' hard':''}">🔔 REMINDER</span>
                    <button class="toast-close" onclick="dismissReminder(${t.id})">&times;</button>
                </div>
                <div class="toast-title">${escapeHtml(t.title)}</div>
                ${dl ? '<div class="toast-deadline" style="color:'+dlColor+'">Due: '+dlText+'</div>' : ''}
                <div class="toast-meta">${(t.priority||'Medium').toUpperCase()}${t.duration ? ' · '+t.duration : ''}</div>
                <div class="toast-actions">
                    <button class="btn-toast-focus" onclick="dismissReminder(${t.id});startFocus(${t.id})">Start Focus</button>
                    <button class="btn-toast-dismiss" onclick="dismissReminder(${t.id})">Dismiss</button>
                </div>
            </div>`;
        });
        if (due.length > 3) {
            stack.innerHTML += `<div style="font-size:12px;color:var(--text-muted);text-align:right;margin-top:4px;">and ${due.length-3} more reminders</div>`;
        }
    }

    window.dismissReminder = async function(taskId) {
        const el = document.getElementById('reminder-' + taskId);
        if (el) { el.style.opacity = '0'; el.style.transform = 'translateY(20px)'; setTimeout(() => el.remove(), 200); }
        try { await fetch('/api/reminder-dismiss/' + taskId, {method:'POST'}); } catch(e) {}
        const t = allTasks.find(x => x.id === taskId);
        if (t) t.reminder_dismissed = true;
    };

    // ── PHASE 1: DEADLINE TYPE + DURATION MODAL CONTROLS ──────────────
    window.setDeadlineType = function(type) {
        selectedDeadlineType = type;
        document.getElementById('dl-soft').classList.toggle('selected', type === 'soft');
        document.getElementById('dl-hard').classList.toggle('selected', type === 'hard');
        document.getElementById('hard-warning').classList.toggle('visible', type === 'hard');
    };

    // S1-H: Duration pill single-select with bounce animation
    window.selectDurationPill = function(el, value) {
        document.querySelectorAll('[data-dur]').forEach(b => b.classList.remove('selected'));
        el.classList.add('selected');
        const inp = document.getElementById('mission-duration');
        if (inp) inp.value = value;
    };

    // S2-H: Deadline quick-select pills
    window.selectDeadlinePill = function(el, value) {
        document.querySelectorAll('[data-dl-preset]').forEach(b => b.classList.remove('selected'));
        el.classList.add('selected');
        const inp = document.getElementById('mission-deadline');
        if (inp) { inp.value = value; inp.dispatchEvent(new Event('input')); }
    };

    // ── S12: PERFORMANCE TELEMETRY (real behavioral analytics) ─────────────
    function _statsDow(d) {
        try { return new Date(d + 'T00:00:00').toLocaleDateString([], { weekday: 'long' }); }
        catch (e) { return d || ''; }
    }
    function _statsHourRange(h) {
        if (h == null) return '—';
        const lab = x => { x = ((x % 24) + 24) % 24; const ap = x < 12 ? 'am' : 'pm'; const hh = x % 12; return `${hh === 0 ? 12 : hh}${ap}`; };
        return `${lab(h)}–${lab(h + 1)}`;
    }
    // S14-F: DAY OF WEEK PATTERNS card — horizontal bars + best/watch chips
    async function loadDayOfWeek() {
        try {
            const res = await fetch('/api/stats/day-of-week');
            const d = await res.json();
            const byDay = (d && d.by_day) || {};
            const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            const color = tfScoreColor;   // CODE-HEALTH: single source (see tfScoreColor)
            const barsEl = document.getElementById('dow-bars');
            if (barsEl) {
                barsEl.innerHTML = names.map((nm, i) => {
                    const row = byDay[i] || byDay[String(i)] || { avg_tis: null, sample_size: 0 };
                    const tis = row.avg_tis;
                    const has = row.sample_size >= 2 && tis != null;
                    const w = has ? Math.max(2, Math.round(tis)) : 0;
                    const bar = has ? `<div style="height:8px;width:${w}%;background:${color(tis)};border-radius:4px;"></div>` : '';
                    return `<div style="display:flex;align-items:center;gap:10px;">
                        <div style="width:32px;color:var(--text-muted);font-size:11px;">${nm}</div>
                        <div style="flex:1;height:8px;background:var(--border-subtle);border-radius:4px;overflow:hidden;">${bar}</div>
                        <div style="width:28px;text-align:right;font-family:'DM Mono',monospace;font-size:11px;color:${has ? color(tis) : 'var(--text-disabled)'};">${has ? tis : '—'}</div>
                    </div>`;
                }).join('');
            }
            const chipsEl = document.getElementById('dow-chips');
            if (chipsEl) {
                let chips = '';
                if (d && d.best_day_name) {
                    chips += `<div style="flex:1;background:color-mix(in srgb, var(--accent-success) 8%, transparent);border:1px solid color-mix(in srgb, var(--accent-success) 15%, transparent);border-radius:8px;padding:8px 12px;">
                        <div style="color:var(--text-disabled);font-size:9px;text-transform:uppercase;letter-spacing:1px;">BEST DAY</div>
                        <div style="color:var(--green);font-size:14px;font-weight:500;">${d.best_day_name}</div>
                        <div style="color:var(--text-muted);font-size:11px;">avg ${d.best_day_avg_tis} TIS</div>
                    </div>`;
                }
                if (d && d.worst_day_name && d.worst_day_avg_tis != null && d.worst_day_avg_tis < 65 && d.worst_day_name !== d.best_day_name) {
                    chips += `<div style="flex:1;background:color-mix(in srgb, var(--accent-warning) 8%, transparent);border:1px solid color-mix(in srgb, var(--accent-warning) 15%, transparent);border-radius:8px;padding:8px 12px;">
                        <div style="color:var(--text-disabled);font-size:9px;text-transform:uppercase;letter-spacing:1px;">WATCH OUT</div>
                        <div style="color:var(--amber);font-size:14px;font-weight:500;">${d.worst_day_name}</div>
                        <div style="color:var(--text-muted);font-size:11px;">avg ${d.worst_day_avg_tis} TIS</div>
                    </div>`;
                }
                if (!chips) chips = `<div style="color:var(--text-disabled);font-size:11px;">Building pattern… complete tasks across more days for day-of-week insights.</div>`;
                chipsEl.innerHTML = chips;
            }
        } catch (e) { console.error('dow', e); }
    }

    async function loadStats() {
        loadDayOfWeek();
        try {
            const [wRes, dRes] = await Promise.all([fetch('/api/stats/weekly'), fetch('/api/stats/daily-summaries')]);
            const w = await wRes.json();
            const d = await dRes.json();
            const days = (w && w.days) || (d && d.summaries) || [];

            const building = document.getElementById('stats-building');
            const content = document.getElementById('stats-content');
            if (!days || days.length < 3) {
                if (building) { building.style.display = 'block'; building.textContent = `Building your execution profile… ${days.length}/3 days. Keep using TaskFlow — analytics populate automatically.`; }
                if (content) content.style.opacity = '0.35';
                return;
            }
            if (building) building.style.display = 'none';
            if (content) content.style.opacity = '1';

            const color = tfScoreColor;   // CODE-HEALTH: single source (see tfScoreColor)
            const avg = Math.round(w.avg_score || 0);

            // Section 1 — gauge
            const ring = document.getElementById('tis-ring');
            const CIRC = 2 * Math.PI * 78;
            if (ring) { ring.setAttribute('stroke-dasharray', CIRC.toFixed(1)); ring.setAttribute('stroke-dashoffset', (CIRC * (1 - avg / 100)).toFixed(1)); ring.setAttribute('stroke', color(avg)); }
            const num = document.getElementById('tis-num'); if (num) { num.textContent = avg; num.setAttribute('fill', color(avg)); }
            const trend = document.getElementById('tis-trend');
            if (trend) { const t = w.trend || 'stable'; const tc = t === 'improving' ? 'var(--green)' : (t === 'declining' ? 'var(--red)' : 'var(--amber)'); const ar = t === 'improving' ? '↑' : (t === 'declining' ? '↓' : '→'); trend.innerHTML = `<span style="color:${tc};">${ar} ${t}</span> · 7-day average`; }
            const bw = document.getElementById('tis-bestworst');
            if (bw && w.best_day && w.worst_day) bw.textContent = `Best ${_statsDow(w.best_day.date)} (${w.best_day.score}) · Watch ${_statsDow(w.worst_day.date)} (${w.worst_day.score})`;

            // Section 2 — week bars
            const bars = document.getElementById('tis-bars');
            const today = new Date().toISOString().slice(0, 10);
            if (bars) {
                bars.innerHTML = days.map(dd => {
                    const sc = dd.time_integrity_score || 0;
                    const h = Math.max(4, Math.round(sc / 100 * 150));
                    const isToday = dd.date === today;
                    return `<div title="${_statsDow(dd.date)}: ${sc} · ${dd.tasks_completed || 0} done" style="flex:1; display:flex; flex-direction:column; align-items:center; gap:6px;">
                        <div style="width:100%; height:${h}px; background:${color(sc)}; border-radius:4px 4px 0 0; ${isToday ? 'outline:2px solid var(--text-hero); outline-offset:1px;' : ''}"></div>
                        <div style="font-size:9px; color:var(--text-disabled);">${_statsDow(dd.date).slice(0, 3)}</div>
                    </div>`;
                }).join('');
            }

            // Section 3 — breakdown chips
            const sum = k => days.reduce((a, x) => a + (x[k] || 0), 0);
            const chips = [
                ['Completed', sum('tasks_completed'), 'var(--green)'],
                ['Missed', sum('tasks_missed'), 'var(--red)'],
                ['Postponed', sum('tasks_postponed'), 'var(--amber)'],
                ['Dropped', sum('tasks_dropped'), 'var(--text-muted)'],
                ['Focus sessions', sum('focus_sessions'), 'var(--blue)'],
                ['Focus minutes', sum('focus_minutes_total'), 'var(--blue)'],
                ['Streak', (w.execution_streak || 0) + 'd', 'var(--amber)'],
                ['Hard misses', w.hard_deadlines_missed_week || 0, 'var(--red)'],
            ];
            const chipsEl = document.getElementById('stats-chips');
            if (chipsEl) chipsEl.innerHTML = chips.map(([label, val, c]) =>
                `<div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:8px; padding:10px 14px;">
                    <div style="font-family:'DM Mono',monospace; font-size:24px; color:${c};">${val}</div>
                    <div style="color:var(--text-disabled); font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-top:4px;">${label}</div>
                </div>`).join('');

            // Section 4 — patterns
            const pat = document.getElementById('stats-patterns');
            if (pat) {
                const drift = w.avg_start_drift;
                const driftStr = drift == null ? '—' : `${drift > 0 ? '+' : ''}${Math.round(drift)} min`;
                const driftColor = drift == null ? 'var(--text-muted)' : (drift > 0 ? 'var(--amber)' : 'var(--green)');
                pat.innerHTML = `
                    <div>PEAK HOUR <span style="float:right; color:var(--blue); font-family:'DM Mono',monospace;">${_statsHourRange(w.most_productive_hour)}</span></div>
                    <div>MOST AVOIDED <span style="float:right; color:var(--amber);">${w.most_avoided_tag ? ('#' + w.most_avoided_tag) : '—'}</span></div>
                    <div>AVG START DRIFT <span style="float:right; color:${driftColor}; font-family:'DM Mono',monospace;">${driftStr}</span></div>
                    <div>RECOVERY (week) <span style="float:right; color:var(--text-hero); font-family:'DM Mono',monospace;">${w.recovery_sessions || 0}</span></div>`;
            }

            // Section 5 — recovery history
            const rec = document.getElementById('stats-recovery');
            if (rec) {
                const hist = w.recovery_history || [];
                rec.innerHTML = hist.length ? hist.map(h => {
                    const ok = h.was_successful;
                    return `<div style="display:flex; justify-content:space-between; border-left:3px solid ${ok ? 'var(--green)' : 'var(--red)'}; padding:6px 10px; background:color-mix(in srgb, var(--text-primary) 2%, transparent); border-radius:6px;">
                        <span>${h.date || ''} · ${h.trigger_reason || '—'}</span>
                        <span style="color:${ok ? 'var(--green)' : 'var(--red)'};">${h.tasks_completed || 0} done ${ok ? '✓' : '✗'}</span>
                    </div>`;
                }).join('') : '<div style="opacity:0.5;">No recovery sessions yet.</div>';
            }
        } catch (e) { console.error('stats', e); }
    }

    function filterByTag(tag) {
        currentFilter = 'tagged';
        currentTagFilter = tag;
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        renderTaskList();
    }

    // ── TIMELINE CALENDAR SYSTEM ──────────────────────────────────────────
    const DAYS_SHORT = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    let timelineState = {
        view: 'week',
        currentDate: new Date(),
        isDropdownOpen: false
    };

    function initTimelineControls() {
        initTimelineScroll();
        const btn = document.getElementById('timeline-view-btn');

        const dropdown = document.getElementById('timeline-dropdown');
        const nav = document.getElementById('timeline-nav');
        
        if (!btn) return;

        btn.onclick = (e) => {
            e.stopPropagation();
            timelineState.isDropdownOpen = !timelineState.isDropdownOpen;
            dropdown.classList.toggle('show', timelineState.isDropdownOpen);
            btn.classList.toggle('active', timelineState.isDropdownOpen);
        };

        document.addEventListener('click', () => {
            timelineState.isDropdownOpen = false;
            dropdown.classList.remove('show');
            btn.classList.remove('active');
        });

        document.querySelectorAll('.dropdown-item').forEach(item => {
            item.onclick = () => {
                const view = item.dataset.view;
                setTimelineView(view);
                document.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            };
        });

        document.getElementById('prev-btn').onclick = () => navigateTimeline(-1);
        document.getElementById('next-btn').onclick = () => navigateTimeline(1);
    }

    function initTimelineScroll() {
        const vp = document.getElementById('timeline-viewport');
        if (!vp) return;

        let isDown = false, startX, scrollLeft;
        let velX = 0, lastX = 0, momentumID;

        const startMomentum = () => {
            const glide = () => {
                vp.scrollLeft += velX;
                velX *= 0.95; // Friction
                updateEdgeSignals();
                if (Math.abs(velX) > 0.5) momentumID = requestAnimationFrame(glide);
            };
            momentumID = requestAnimationFrame(glide);
        };

        vp.onmousedown = (e) => {
            if (e.target.closest('.timeline-task')) return;
            isDown = true;
            cancelAnimationFrame(momentumID);
            vp.classList.add('grabbing');
            startX = e.pageX - vp.offsetLeft;
            scrollLeft = vp.scrollLeft;
            lastX = e.pageX;
            velX = 0;
        };

        vp.onmouseleave = () => { if (isDown) startMomentum(); isDown = false; vp.classList.remove('grabbing'); };
        vp.onmouseup = () => { if (isDown) startMomentum(); isDown = false; vp.classList.remove('grabbing'); };
        
        vp.onmousemove = (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - vp.offsetLeft;
            const walk = (x - startX) * 1.5;
            vp.scrollLeft = scrollLeft - walk;
            
            velX = (lastX - e.pageX) * 0.8;
            lastX = e.pageX;
            updateEdgeSignals();
        };

        vp.onscroll = updateEdgeSignals;
        window.addEventListener('resize', updateEdgeSignals);
    }


    function updateEdgeSignals() {
        const vp = document.getElementById('timeline-viewport');
        if (!vp) return;
        const sigLeft = document.getElementById('signal-left');
        const sigRight = document.getElementById('signal-right');
        
        const sl = vp.scrollLeft;
        const sw = vp.scrollWidth;
        const cl = vp.clientWidth;

        if (sigLeft) sigLeft.classList.toggle('active', sl > 10);
        if (sigRight) sigRight.classList.toggle('active', sl + cl < sw - 10);
    }

    function handleAutoPan(clientX) {
        const vp = document.getElementById('timeline-viewport');
        if (!vp) return;
        const rect = vp.getBoundingClientRect();
        const threshold = 100;
        
        if (clientX < rect.left + threshold) {
            vp.scrollBy({ left: -20, behavior: 'auto' });
        } else if (clientX > rect.right - threshold) {
            vp.scrollBy({ left: 20, behavior: 'auto' });
        }
        updateEdgeSignals();
    }

    function setTimelineView(view) {
        timelineState.view = view;
        document.getElementById('current-view-label').textContent = view.toUpperCase().replace('WEEK', 'THIS WEEK').replace('MONTH', 'THIS MONTH').replace('CALENDAR', 'FULL CALENDAR');
        
        const nav = document.getElementById('timeline-nav');
        const grid = document.getElementById('timeline-grid');
        
        if (view === 'calendar') nav.classList.add('show');
        else nav.classList.remove('show');

        if (view === 'month' || view === 'calendar') grid.classList.add('month-mode');
        else grid.classList.remove('month-mode');

        renderTimeline();
    }

    function navigateTimeline(dir) {
        const d = timelineState.currentDate;
        if (timelineState.view === 'calendar') {
            d.setMonth(d.getMonth() + dir);
        } else if (timelineState.view === 'week') {
            d.setDate(d.getDate() + (dir * 7));
        }
        renderTimeline();
    }

    function getStartOfWeek(d) {
        const date = new Date(d);
        const day = date.getDay(); // 0 is Sun, 1 is Mon
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(date.setDate(diff));
    }

    function formatDateISO(d) {
        const offset = d.getTimezoneOffset() * 60000;
        return (new Date(d.getTime() - offset)).toISOString().split('T')[0];
    }

    function renderTimeline() {
        try {
            const grid = document.getElementById('timeline-grid');
            const pool = document.getElementById('unscheduled-dropzone');
            if (!grid || !pool) return;

            let mapping = timelineMapping || {};

            // Migration: handle old day name keys
            const oldDays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
            let migrated = false;
            for (let tid in mapping) {
                if (oldDays.includes(mapping[tid])) {
                    const dayIdx = oldDays.indexOf(mapping[tid]);
                    const start = getStartOfWeek(new Date());
                    start.setDate(start.getDate() + dayIdx);
                    mapping[tid] = formatDateISO(start);
                    migrated = true;
                }
            }
            if (migrated) {
                timelineMapping = mapping;
                fetch('/api/timeline', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ mapping: timelineMapping }) });
            }

            grid.innerHTML = '';
            const todayStr = formatDateISO(new Date());
            
            let dates = [];
            if (timelineState.view === 'week') {
                const start = getStartOfWeek(timelineState.currentDate);
                for (let i = 0; i < 7; i++) {
                    const d = new Date(start);
                    d.setDate(start.getDate() + i);
                    dates.push({ date: d, label: DAYS_SHORT[i] });
                }
                document.getElementById('timeline-period-label').textContent = "CURRENT WEEK";
            } else {
                // Month / Calendar View
                const d = timelineState.currentDate;
                const year = d.getFullYear();
                const month = d.getMonth();
                const firstDay = new Date(year, month, 1);
                const lastDay = new Date(year, month + 1, 0);
                
                document.getElementById('timeline-period-label').textContent = firstDay.toLocaleString('default', { month: 'long', year: 'numeric' }).toUpperCase();

                // Pad start
                let startPad = firstDay.getDay(); // 0 (Sun) to 6 (Sat)
                startPad = startPad === 0 ? 6 : startPad - 1; // Adjust to Mon start
                
                const start = new Date(firstDay);
                start.setDate(firstDay.getDate() - startPad);
                
                // Show 6 weeks fixed for smooth transitions
                for (let i = 0; i < 42; i++) {
                    const cur = new Date(start);
                    cur.setDate(start.getDate() + i);
                    dates.push({ 
                        date: cur, 
                        label: i < 7 ? DAYS_SHORT[i] : '',
                        isOtherMonth: cur.getMonth() !== month
                    });
                }
            }

            dates.forEach((item, idx) => {
                const dateStr = formatDateISO(item.date);
                const isToday = dateStr === todayStr;
                const isWeekend = (item.date.getDay() === 0 || item.date.getDay() === 6);
                
                const dayEl = document.createElement('div');
                dayEl.className = `timeline-day ${isToday ? 'today' : ''} ${item.isOtherMonth ? 'other-month' : ''} ${isWeekend ? 'weekend-col' : ''}`;
                dayEl.innerHTML = `
                    <div class="timeline-day-header">
                        <span class="day-label">${item.label || ''}</span>
                        <span class="date-number">${item.date.getDate()}</span>
                    </div>
                    ${timelineState.view !== 'month' && timelineState.view !== 'calendar' ? `
                    <div class="prime-target-slot" data-date="${dateStr}_prime" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                        <div class="prime-target-label">[ PRIME TARGET ]</div>
                    </div>` : ''}
                    <div class="timeline-dropzone" data-date="${dateStr}" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                    </div>
                `;
                grid.appendChild(dayEl);

            });


            pool.innerHTML = '';
            
            const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);

            activeTasks.forEach(task => {
                const np = normalizePriority(task.priority);
                const el = document.createElement('div');
                el.className = `timeline-task tl-chip p-${np}`;
                el.draggable = true;
                el.dataset.id = task.id;

                const dl = formatDeadline(task.deadline);
                const timeStr = dl ? dl.text.split('·')[0].trim() : '';
                const durStr = task.duration ? ' · [' + task.duration + ']' : '';
                const hardIcon = task.deadline_type === 'hard' ? '⚠ ' : '';

                el.innerHTML = `<div class="tl-chip-title">${hardIcon}${escapeHtml(task.title)}</div>` +
                    (timeStr || durStr ? `<div class="tl-chip-meta">${timeStr}${durStr}</div>` : '');

                let _chipDragging = false;
                el.ondragstart = (e) => {
                    // Fix 2: starting to drag an unscheduled chip scrolls up so the calendar is visible
                    if (el.closest('#unscheduled-dropzone')) {
                        try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (err) {}
                    }
                    _chipDragging = true;
                    e.dataTransfer.setData('application/task-id', task.id.toString());
                    setTimeout(() => el.classList.add('dragging'), 0);
                };
                el.ondragend = () => {
                    el.classList.remove('dragging');
                    document.querySelectorAll('.drag-over').forEach(d => d.classList.remove('drag-over'));
                };
                // Fix 2: a click (not a drag) opens the Mission Briefing modal
                el.addEventListener('mousedown', () => { _chipDragging = false; });
                el.addEventListener('click', () => { if (!_chipDragging) { try { openModal(task.id, el); } catch (err) {} } });

                // Place task: check mapping first, then deadline date, then unscheduled
                const dateKey = mapping[task.id];
                let isScheduled = !!dateKey || !!task.deadline;
                let placed = false;
                
                let targetDateStr = '';
                if (dateKey) {
                    targetDateStr = dateKey.replace('_prime', '');
                } else if (task.deadline) {
                    try {
                        targetDateStr = formatDateISO(new Date(task.deadline));
                    } catch(err) {}
                }
                
                if (targetDateStr) {
                    // Check if this date is visible in our current grid
                    const hasZone = grid.querySelector(`.timeline-dropzone[data-date="${targetDateStr}"]`);
                    if (hasZone) {
                        // Find exact slot (prime or standard)
                        const primeZone = grid.querySelector(`[data-date="${dateKey}"]`);
                        if (primeZone && dateKey && dateKey.endsWith('_prime')) {
                            primeZone.appendChild(el);
                            placed = true;
                        } else {
                            const dropzone = grid.querySelector(`.timeline-dropzone[data-date="${targetDateStr}"]`);
                            if (dropzone) {
                                dropzone.appendChild(el);
                                placed = true;
                            }
                        }
                    } else {
                        // It is off-screen. Skip rendering.
                        placed = true; // Prevents showing in unscheduled pool
                    }
                }

                if (!placed && !isScheduled) {
                    pool.appendChild(el);
                }
            });

            // Update column headers with mission counts
            grid.querySelectorAll('.timeline-day').forEach(dayEl => {
                const dropzone = dayEl.querySelector('.timeline-dropzone');
                if (!dropzone) return;
                const count = dropzone.querySelectorAll('.timeline-task').length;
                
                // prime targets count placeholder
                const primeSlot = dayEl.querySelector('.prime-target-slot');
                if (primeSlot) {
                    const label = primeSlot.querySelector('.prime-target-label');
                    const hasPrime = primeSlot.querySelectorAll('.timeline-task').length > 0;
                    if (label) {
                        if (hasPrime) {
                            label.textContent = '★ PRIME TARGET';
                        } else {
                            label.textContent = '[ PRIME TARGET ]';
                        }
                    }
                }
                
                // Show standard mission count in header
                const header = dayEl.querySelector('.timeline-day-header');
                if (header) {
                    const existingBadge = header.querySelector('.header-count-badge');
                    if (existingBadge) existingBadge.remove();
                    if (count > 0) {
                        const badge = document.createElement('span');
                        badge.className = 'header-count-badge';
                        badge.style.cssText = 'background: color-mix(in srgb, var(--text-primary) 10%, transparent); color: var(--text-muted); font-size: 9px; padding: 2px 6px; border-radius: 10px; margin-left: 6px;';
                        badge.textContent = count;
                        header.appendChild(badge);
                    }
                }
            });
        } catch(e) {
            console.error("renderTimeline failed:", e);
            showToast('Timeline Render Error: ' + e.message, 'var(--red)');
        }
    }

    window.handleDragOver = (e) => {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
        handleAutoPan(e.clientX);
    };

    window.handleDragLeave = (e) => {
        e.currentTarget.classList.remove('drag-over');
    };
    window.handleDrop = (e) => {
        e.preventDefault();
        const zone = e.currentTarget;
        zone.classList.remove('drag-over');
        
        const taskId = e.dataTransfer.getData('application/task-id');
        if (!taskId) return;
        const dateKey = zone.dataset.date;

        if (zone.classList.contains('prime-target-slot') && zone.querySelectorAll('.timeline-task').length > 0) {
            showToast("Only ONE Prime Target allowed per day. Re-evaluate.", "var(--amber)");
            return;
        }

        if (zone.id === 'unscheduled-dropzone') {
            delete timelineMapping[taskId];
        } else {
            timelineMapping[taskId] = dateKey;
        }
        
        fetch('/api/timeline', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ mapping: timelineMapping })
        }).catch(e => console.error(e));

        renderTimeline();
    };

    // (Pass-2 schedule-overlay system removed — unscheduled chips drag directly onto the
    //  real timeline day columns, exactly as the original behavior.)

    function renderTagSignals() {
        const discovery = document.getElementById('tag-signal-discovery');
        if (!discovery) return;
        const activeTasks = allTasks.filter(t => !t.completed && t.status !== 'completed' && t.status !== 'done' && !t.dropped_at && !t.offloaded_at);
        const uniqueTags = [...new Set(activeTasks.flatMap(t => {
            if (!t.tags) return [];
            if (Array.isArray(t.tags)) return t.tags;
            if (typeof t.tags === 'string') return t.tags.split(',').map(s=>s.trim());
            return [];
        }))];
        if (uniqueTags.length === 0) {
            discovery.innerHTML = `<div style="font-size:10px; color:var(--text-disabled); font-style:italic;">No signals discovered.</div>`;
            return;
        }
        discovery.innerHTML = uniqueTags.map(tg => {
            const isActive = (currentFilter === 'tagged' && currentTagFilter === tg) ? ' active' : '';
            // SEC-01: sanitise the onclick arg (JS-string context) + escape the visible label
            const tgArg = String(tg).replace(/[^a-zA-Z0-9_\- ]/g, '');
            return `<div class="filter-chip${isActive}" onclick="filterByTag('${tgArg}', this)">#${escapeHtml(String(tg).toUpperCase())}</div>`;
        }).join('');
    }

    // ── MODAL SYSTEM ──────────────────────────────────────────────────────
    const modal = document.getElementById('modal-overlay');
    let _modalKeyHandler = null;

    function openModal(id, el) {
        const task = allTasks.find(t => t.id === id);
        if (!task) return;
        const r = el.getBoundingClientRect();
        const mc = document.getElementById('mission-brief-modal');
        mc.style.setProperty('--origin-x', `${r.left + r.width/2}px`);
        mc.style.setProperty('--origin-y', `${r.top + r.height/2}px`);

        const np = normalizePriority(task.priority);
        const dl = formatDeadline(task.deadline);
        const dlInfo = dl ? `<div class="modal-deadline" style="color:${dl.color}">⏰ ${dl.text}${task.deadline_type==='hard'?' <span class="hard-tag">⚠ HARD</span>':''}</div>` : '';
        const durBadge = task.duration ? `<span class="duration-badge">[${task.duration}]</span>` : '';
        const postponeBadge = (task.postpone_count||0) >= 2 ? `<span class="postpone-badge ${task.postpone_count>=3?'warn':'mild'}">postponed ×${task.postpone_count}</span>` : '';
        const tagBadges = (task.tags||[]).map(tg => `<span class="badge tag">#${escapeHtml(tg)}</span>`).join('');
        const pc = task.postpone_count || 0;
        const canPostpone = pc < 5;
        let postponeWarn = '';
        if (pc >= 5) postponeWarn = '<div style="color:var(--red);font-size:11px;margin-top:8px;padding:6px 10px;background:color-mix(in srgb, var(--accent-danger) 6%, transparent);border-radius:6px;">⚠ Maximum postpones reached. Execute or Drop this mission.</div>';
        else if (pc >= 3) postponeWarn = '<div style="color:var(--amber);font-size:11px;margin-top:8px;padding:6px 10px;background:color-mix(in srgb, var(--accent-warning) 6%, transparent);border-radius:6px;">⚠ Postponed ' + pc + '× — the mirror doesn\'t lie. Consider dropping.</div>';
        else if (pc >= 2) postponeWarn = '<div style="color:var(--text-muted);font-size:11px;margin-top:8px;">Postponed ' + pc + '× — be honest with yourself.</div>';

        const createdDate = task.created_at ? new Date(task.created_at).toLocaleDateString([], {day:'numeric', month:'short', year:'numeric'}) : 'Unknown';

        let fMin = 25;
        if (typeof task.duration_minutes === 'number') { fMin = task.duration_minutes; }   // CODE-HEALTH: server-computed
        else if (task.duration) { const mm = String(task.duration).match(/([0-9]+) *(h|m)/i); if (mm) fMin = mm[2].toLowerCase() === 'h' ? parseInt(mm[1]) * 60 : parseInt(mm[1]); }
        const focusClock = (fMin < 10 ? '0' : '') + fMin + ':00';

        document.getElementById('modal-content').innerHTML = `
            <div class="brief-header">
                <div class="brief-h-label">MISSION BRIEFING</div>
                <h2 class="brief-title">${escapeHtml(task.title)}</h2>
                <div class="brief-badges">
                    <span class="badge ${np}">${(task.priority||'MEDIUM').toUpperCase()}</span>
                    ${durBadge}
                    ${tagBadges}
                    ${postponeBadge}
                </div>
                ${dlInfo ? `<div class="brief-deadline">${dlInfo}</div>` : ''}
            </div>

            <div class="brief-body" id="brief-body">
                <div class="brief-enrich-block" id="brief-enrich" data-bid="${task.id}">${tfBriefEnrichment(task)}</div>

                <div style="background:color-mix(in srgb, var(--text-primary) 2%, transparent); padding:18px; border-radius:14px; border:1px solid color-mix(in srgb, var(--text-primary) 5%, transparent);">
                    <div class="section-label" style="margin-bottom:12px;font-size:9px;">FOCUS PROTOCOL</div>
                    <div style="font-size:34px; font-family:var(--font-mono); margin-bottom:14px; color:var(--text-hero); text-align:center; opacity:0.8;">${focusClock}</div>
                    <button class="btn-execute" style="width:100%; margin-bottom:10px; padding:13px;" onclick="startFocus(${task.id})">DEPLOY FOCUS SESSION</button>
                    <div style="display:flex;gap:8px;">
                        <button class="epdo-btn-util complete" onclick="completeTaskFromModal(${task.id})">✓ COMPLETE</button>
                        <button class="epdo-btn-util ai" onclick="showToast('Querying Intelligence Core...', 'var(--ai-purple)')">✦ ASK AI</button>
                    </div>
                </div>

                <div class="brief-meta">
                    <span>ID: #${task.id}</span>
                    <span>Created: ${createdDate}</span>
                </div>
            </div>

            <div class="brief-footer">
                <div class="epdo-sub-panel" id="postpone-panel" style="display:none; margin-bottom:10px;">
                    <div class="epdo-sub-label">PUSH DEADLINE →</div>
                    <div class="postpone-options">
                        <button class="postpone-opt" onclick="executePostpone(${task.id}, '+15m')">+15 min</button>
                        <button class="postpone-opt" onclick="executePostpone(${task.id}, '+1h')">+1 hour</button>
                        <button class="postpone-opt" onclick="executePostpone(${task.id}, '+3h')">+3 hours</button>
                        <button class="postpone-opt" onclick="executePostpone(${task.id}, 'tomorrow')">Tomorrow 9AM</button>
                    </div>
                    <div class="postpone-custom-row">
                        <input type="text" id="postpone-custom-input" class="input-system" style="width:100%;" placeholder="Custom time (e.g. 'next fri 3pm')" autocomplete="off">
                        <textarea id="postpone-reason" class="postpone-reason" rows="2" placeholder="Why are we postponing this? Be honest..."></textarea>
                        <button class="epdo-btn postpone" style="width:100%; margin-top:8px; padding:10px;" onclick="executePostpone(${task.id}, 'custom')">
                            <span class="epdo-icon">⏳</span> CONFIRM DELAY
                        </button>
                    </div>
                </div>

                <div class="epdo-sub-panel" id="offload-panel" style="display:none; margin-bottom:10px;">
                    <div class="epdo-sub-label">DELEGATE TO →</div>
                    <div style="display:flex;gap:8px;">
                        <input type="text" id="offload-note-input" class="input-system" style="flex:1;" placeholder="Who takes ownership?" autocomplete="off">
                        <button class="epdo-btn offload" style="width:auto;padding:10px 20px;" onclick="executeOffload(${task.id})">
                            <span class="epdo-icon">→</span> CONFIRM
                        </button>
                    </div>
                </div>

                <div class="epdo-section" style="margin:0;">
                    <div class="epdo-label">COMMAND MATRIX</div>
                    <div class="epdo-grid">
                        <button class="epdo-btn execute" onclick="startFocus(${task.id}); closeModal();" title="Start Focus Protocol">
                            <span class="epdo-icon">▶</span>
                            <span class="epdo-text">EXECUTE</span>
                            <span class="epdo-key">E</span>
                        </button>
                        <button class="epdo-btn postpone${!canPostpone?' disabled':''}" onclick="togglePostponePanel(${task.id})" title="Postpone deadline"${!canPostpone?' disabled':''}>
                            <span class="epdo-icon">⏳</span>
                            <span class="epdo-text">POSTPONE</span>
                            <span class="epdo-key">P</span>
                        </button>
                        <button class="epdo-btn drop" onclick="dropTaskFromModal(${task.id})" title="Purge mission">
                            <span class="epdo-icon">✕</span>
                            <span class="epdo-text">DROP</span>
                            <span class="epdo-key">D</span>
                        </button>
                        <button class="epdo-btn offload" onclick="toggleOffloadPanel(${task.id})" title="Delegate to someone">
                            <span class="epdo-icon">→</span>
                            <span class="epdo-text">OFFLOAD</span>
                            <span class="epdo-key">O</span>
                        </button>
                    </div>
                    ${postponeWarn}
                </div>
            </div>
        `;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
        window._briefTaskId = task.id;

        // Keyboard shortcuts for EPDO
        if (_modalKeyHandler) document.removeEventListener('keydown', _modalKeyHandler);
        const _taskId = task.id;
        const _canPostpone = canPostpone;
        _modalKeyHandler = (e) => {
            if (!modal.classList.contains('show')) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            const key = e.key.toUpperCase();
            if (key === 'E') { startFocus(_taskId); closeModal(); }
            else if (key === 'P' && _canPostpone) { e.preventDefault(); togglePostponePanel(_taskId); }
            else if (key === 'D') { e.preventDefault(); dropTaskFromModal(_taskId); }
            else if (key === 'O') { e.preventDefault(); toggleOffloadPanel(_taskId); }
            else if (key === 'ESCAPE') { closeModal(); }
        };
        document.addEventListener('keydown', _modalKeyHandler);
    }

    function closeModal() {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        window._briefTaskId = null;
        if (_modalKeyHandler) { document.removeEventListener('keydown', _modalKeyHandler); _modalKeyHandler = null; }
    }
    document.getElementById('btn-modal-close').onclick = closeModal;
    (function(){ const ov = document.getElementById('modal-overlay'); if (ov && !ov._tfBackdrop) { ov._tfBackdrop = true; ov.addEventListener('click', e => { if (e.target === ov) closeModal(); }); } })();

    // ── EPDO HANDLERS ──────────────────────────────────────────────────
    window.togglePostponePanel = function(taskId) {
        const pp = document.getElementById('postpone-panel');
        const op = document.getElementById('offload-panel');
        if (op) op.style.display = 'none';
        if (pp) pp.style.display = pp.style.display === 'none' ? 'block' : 'none';
    };

    window.toggleOffloadPanel = function(taskId) {
        const op = document.getElementById('offload-panel');
        const pp = document.getElementById('postpone-panel');
        if (pp) pp.style.display = 'none';
        if (op) {
            op.style.display = op.style.display === 'none' ? 'block' : 'none';
            if (op.style.display === 'block') {
                setTimeout(() => { const inp = document.getElementById('offload-note-input'); if(inp) inp.focus(); }, 100);
            }
        }
    };

    window.executePostpone = async function(taskId, increment) {
        const reasonInput = document.getElementById('postpone-reason');
        const reason = reasonInput ? reasonInput.value.trim() : '';
        
        let finalIncrement = increment;
        if (increment === 'custom') {
            const customInput = document.getElementById('postpone-custom-input');
            const customVal = customInput ? customInput.value.trim() : '';
            if (!customVal) { showToast('Enter a custom time to postpone.', 'var(--amber)'); return; }
            const parsed = parseDeadlineInput(customVal);
            if (!parsed) { showToast('Could not parse custom time.', 'var(--red)'); return; }
            finalIncrement = parsed.toISOString();
        }

        try {
            const res = await fetch(`/api/tasks/${taskId}/postpone`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ increment: finalIncrement, reason: reason })
            });
            if (res.ok) {
                const data = await res.json();
                const pc = data.postpone_count || 0;
                let msg = `Mission postponed. `;
                if (pc >= 5) msg += `⚠ Postponed ${pc}× — no more delays.`;
                else if (pc >= 3) msg += `⚠ Postponed ${pc}× — the mirror speaks.`;
                else msg += `Postponed ${pc}×.`;
                showToast(msg, pc >= 3 ? 'var(--red)' : 'var(--amber)');
                closeModal();
                await loadTasks();
            } else { showToast('Failed to postpone.', 'var(--red)'); }
        } catch(e) { console.error(e); showToast('Postpone error.', 'var(--red)'); }
    };

    window.dropTaskFromModal = function(taskId) {
        const task = allTasks.find(t => t.id === taskId);
        if (!task) return;
        
        const overlay = document.getElementById('drop-overlay');
        const taskName = document.getElementById('drop-modal-task-name');
        const btnCancel = document.getElementById('drop-btn-cancel');
        const btnConfirm = document.getElementById('drop-btn-confirm');
        
        if (overlay && taskName && btnCancel && btnConfirm) {
            taskName.textContent = task.title;
            overlay.classList.add('active');
            
            const cleanup = () => {
                overlay.classList.remove('active');
                btnCancel.removeEventListener('click', onCancel);
                btnConfirm.removeEventListener('click', onConfirm);
            };
            
            const onCancel = () => { cleanup(); };
            const onConfirm = async () => {
                cleanup();
                try {
                    await fetch(`/api/tasks/${taskId}/delete`, {method: 'POST'});
                    showToast('Mission dropped. Sometimes letting go is the right call.', 'var(--red)');
                    closeModal();
                    await loadTasks();
                } catch(e) { console.error(e); showToast('Drop failed.', 'var(--red)'); }
            };
            
            btnCancel.addEventListener('click', onCancel);
            btnConfirm.addEventListener('click', onConfirm);
        }
    };

    window.executeOffload = async function(taskId) {
        const noteInput = document.getElementById('offload-note-input');
        const note = noteInput ? noteInput.value.trim() : '';
        if (!note) { showToast('Enter who takes ownership.', 'var(--amber)'); if(noteInput) noteInput.focus(); return; }
        try {
            const res = await fetch(`/api/tasks/${taskId}/offload`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ note })
            });
            if (res.ok) {
                showToast(`Mission offloaded → ${note}. Ownership transferred.`, 'var(--ai-purple)');
                closeModal();
                await loadTasks();
            } else { showToast('Offload failed.', 'var(--red)'); }
        } catch(e) { console.error(e); showToast('Offload error.', 'var(--red)'); }
    };

    window.completeTaskFromModal = async function(taskId) {
        try {
            const res = await fetch(`/api/tasks/${taskId}/complete`, {method: 'POST'});
            if (res.ok) {
                const data = await res.json();
                if (data.velocity) {
                    const dayWord = data.streak === 1 ? 'Day' : 'Days';
                    showToast(`✦ MISSION SUCCESS  +${data.velocity}% Velocity | Streak: ${data.streak} ${dayWord}`, 'var(--green)');
                } else {
                    showToast('Mission execution successful.', 'var(--green)');
                }
            }
        } catch(e) { console.error(e); showToast('Complete failed.', 'var(--red)'); }
        closeModal();
        setTimeout(loadTasks, 400);
    };

    // ── OMNIBAR DEADLINE TYPE ─────────────────────────────────────────
    let omniDeadlineType = 'soft';
    window.setOmniDeadlineType = function(type) {
        omniDeadlineType = type;
        const soft = document.getElementById('omni-dl-soft');
        const hard = document.getElementById('omni-dl-hard');
        if (soft) soft.classList.toggle('selected', type === 'soft');
        if (hard) hard.classList.toggle('selected', type === 'hard');
    };

    function startFocusFromCard(taskId, btnEl) {
        // High-fidelity feedback pulse
        if (btnEl) {
            const core = btnEl.querySelector('.control-node-core');
            if (core) {
                core.style.transform = 'scale(0.8)';
                core.style.boxShadow = '0 0 40px var(--blue)';
            }
            btnEl.style.background = 'color-mix(in srgb, var(--accent-info) 20%, transparent)';
            setTimeout(() => { 
                if (core) {
                    core.style.transform = ''; 
                    core.style.boxShadow = '';
                }
                btnEl.style.background = '';
            }, 300);
        }
        // Deploy focus protocol
        setTimeout(() => startFocus(taskId), 150);
    }

    async function startFocus(taskId) {
        const task = allTasks.find(t => t.id === taskId);
        if (!task) return;
        
        try {
            const res = await fetch('/api/focus/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ task_id: taskId, minutes: 25, mode: 'gentle' })
            });
            
            if (res.ok) {
                closeModal();
                setSystemState('deep-work');
                // Immediate lock for responsiveness
                activateFocusLock({ focus_active: true, task_title: task.title, remaining_minutes: 25, remaining_seconds: 0 });
                if (typeof startSimulation === 'function') startSimulation('focus');
                showToast("Focus sequence initiated.", "var(--blue)");
            } else {
                showToast("Failed to initiate focus sequence.", "var(--red)");
            }
        } catch(e) { console.error(e); }
    }

    function endFocus(taskId) {
        document.getElementById('focus-overlay').classList.remove('active');
        setSystemState('idle');
        const activeNav = document.querySelector('.nav-item.active').id;
        if (typeof startSimulation === 'function') {
            if (activeNav === 'nav-dashboard') startSimulation('execution');
            else if (activeNav === 'nav-tasks') startSimulation('missions');
            else if (activeNav === 'nav-timeline') startSimulation('focus');
        }
    }

    // SUCCESS RIPPLE on completion
    window.completeTask = async (id, cbEl) => {
        cbEl.classList.add('checked');
        const card = cbEl.closest('.task-card');
        if (card) card.classList.add('completing');
        
        try {
            const res = await fetch(`/api/tasks/${id}/complete`, {method: 'POST'});
            if (res.ok) {
                const data = await res.json();
                if (data.velocity) {
                    const dayWord = data.streak === 1 ? 'Day' : 'Days';
                    showToast(`✦ MISSION SUCCESS  +${data.velocity}% Velocity | Streak: ${data.streak} ${dayWord} | Today: ${data.daily_completions}`, "var(--green)");
                } else {
                    showToast("Mission execution successful.", "var(--green)");
                }
            }
        } catch (e) {
            console.error(e);
            showToast("Mission execution successful.", "var(--green)");
        }
        setTimeout(loadTasks, 750);
    };

    window.purgeTask = async (id, el) => {
        if (!confirm("Are you sure you want to purge this mission?")) return;
        const card = el.closest('.task-card');
        if (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateX(100px)';
        }
        await fetch(`/api/tasks/${id}/delete`, {method: 'POST'});
        showToast("Mission purged from reality.", "var(--red)");
        setTimeout(loadTasks, 400);
    };

    window.onload = () => {
        initThreeJS();
        initTimelineControls();
        loadTasks();
        
        // Start Focus Sync Engine
        checkFocusState();
        setInterval(checkFocusState, 5000);

        // ── PHASE 1: Duration pill clicks ──
        document.querySelectorAll('.dur-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.dur-pill').forEach(p => p.classList.remove('selected'));
                if (selectedDuration === pill.dataset.dur) { selectedDuration = null; }
                else { pill.classList.add('selected'); selectedDuration = pill.dataset.dur; }
            });
        });

        // ── PHASE 1: Deadline input parsing ──
        let dlDebounce = null;
        const dlInput = document.getElementById('mission-deadline');
        if (dlInput) {
            dlInput.addEventListener('input', () => {
                clearTimeout(dlDebounce);
                dlDebounce = setTimeout(() => {
                    const disp = document.getElementById('deadline-parsed-display');
                    const section = document.getElementById('deadline-type-section');
                    const val = dlInput.value.trim();
                    if (!val) { parsedDeadlineISO = null; if(disp){disp.textContent='';disp.classList.remove('visible');} if(section)section.style.display='none'; if(window.tfUpdateProgressDots) tfUpdateProgressDots(); return; }
                    const parsed = parseDeadlineInput(val);
                    if (parsed) {
                        parsedDeadlineISO = parsed.toISOString();
                        const nice = parsed.toLocaleDateString([], {weekday:'long',day:'numeric',month:'short',year:'numeric'}) + ' at ' + parsed.toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
                        if(disp){disp.textContent='→ ' + nice; disp.style.color='var(--green)'; disp.classList.add('visible');}
                        if(section) section.style.display='block';
                    } else {
                        parsedDeadlineISO = null;
                        if(disp){disp.textContent="→ Could not understand. Try: 'Friday 3pm'"; disp.style.color='var(--red)'; disp.classList.add('visible');}
                        if(section)section.style.display='none';
                    }
                    if(window.tfUpdateProgressDots) tfUpdateProgressDots();
                }, 800);
            });
        }

        // ── PHASE 1: Recovery banner exit ──
        const exitBtn = document.getElementById('btn-exit-recovery');
        if (exitBtn) {
            exitBtn.addEventListener('click', async () => {
                if (!confirm('Exit Recovery Mode? You can re-enter from the CLI.')) return;
                await fetch('/api/recovery-exit', {method:'POST'});
                recoveryActive = false; recoveryTaskIds = [];
                document.getElementById('recovery-banner').classList.remove('active');
                document.body.style.background = '';
                renderTaskList();
            });
        }

        // ── PHASE 1: Start pressure, recovery, reminder intervals ──
        checkRecoveryStatus();
        tfRecRestoreBadge();
        setTimeout(() => { checkAutoTrigger(); }, 2500);
        setInterval(() => {
            updateAllPressureLevels();   // S2 deadline text + S3 pressure card states
            updateControlCenter();       // S3-G approaching banner + Upcoming/Next refresh
            checkReminders();
            checkRecoveryStatus();       // S9 recovery status
            checkAutoTrigger();          // S9 5pm/6pm auto-trigger
        }, 60000);
        setTimeout(() => { checkReminders(); }, 2000);

        // ── OMNIBAR (FRICTIONLESS CAPTURE) INIT ────────
        const omniOverlay = document.getElementById('omnibar-overlay');
        const omniInput = document.getElementById('omnibar-input');

        function openOmnibar() {
            if (!omniOverlay || !omniInput) return;
            omniOverlay.classList.add('active');
            omniInput.value = '';
            omniInput.disabled = false;
            setTimeout(() => omniInput.focus(), 80);
        }
        function closeOmnibar() {
            if (!omniOverlay) return;
            omniOverlay.classList.remove('active');
            omniInput.blur();
        }

        if (omniOverlay && omniInput) {
            // Global Ctrl+K Listener — works from ANY view
            document.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    openOmnibar();
                }
            });

            // Escape to dismiss
            omniInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') { e.preventDefault(); closeOmnibar(); }
            });

            // Click backdrop to dismiss
            omniOverlay.addEventListener('click', (e) => {
                if (e.target === omniOverlay) closeOmnibar();
            });

            // Enter key — fire capture with time management
            omniInput.addEventListener('keydown', async (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const text = omniInput.value.trim();
                    if (!text) return;
                    omniInput.disabled = true;
                    // Gather time management data
                    const omniDurSel = document.querySelector('.omni-dur.selected');
                    const omniDur = omniDurSel ? omniDurSel.dataset.dur : null;
                    const omniDlInput = document.getElementById('omni-deadline');
                    const omniDlVal = omniDlInput ? omniDlInput.value.trim() : '';
                    let omniDlISO = null;
                    if (omniDlVal) { const p = parseDeadlineInput(omniDlVal); if (p) omniDlISO = p.toISOString(); }
                    const payload = { title: text };
                    if (omniDur) payload.duration = omniDur;
                    if (omniDlISO) { payload.deadline = omniDlISO; payload.deadline_type = omniDeadlineType || 'soft'; }
                    try {
                        const res = await fetch('/api/tasks/create-full', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(payload)
                        });
                        if (res.ok) {
                            const data = await res.json();
                            const savedTitle = (data.task && data.task.title) ? data.task.title : text;
                            closeOmnibar();
                            if (omniDurSel) omniDurSel.classList.remove('selected');
                            if (omniDlInput) omniDlInput.value = '';
                            omniDeadlineType = 'soft'; setOmniDeadlineType('soft');
                            const dlTypeRow = document.getElementById('omni-dl-type-row'); if(dlTypeRow) dlTypeRow.style.display='none';
                            loadTasks();
                            showToast(`Captured: "${savedTitle}"`, "var(--ai-purple)");
                        } else { omniInput.disabled = false; showToast("Failed to capture thought", "var(--red)"); }
                    } catch (err) { console.error(err); omniInput.disabled = false; showToast("Capture transmission failed", "var(--red)"); }
                }
            });
        }
        // Omnibar duration pill clicks
        document.querySelectorAll('.omni-dur').forEach(pill => {
            pill.addEventListener('click', () => {
                document.querySelectorAll('.omni-dur').forEach(p => p.classList.remove('selected'));
                pill.classList.add('selected');
            });
        });
        // Omnibar deadline live parse
        const omniDlIn = document.getElementById('omni-deadline');
        if (omniDlIn) {
            let omniDlTimer = null;
            omniDlIn.addEventListener('input', () => {
                clearTimeout(omniDlTimer);
                omniDlTimer = setTimeout(() => {
                    const disp = document.getElementById('omni-dl-parsed');
                    const typeRow = document.getElementById('omni-dl-type-row');
                    const val = omniDlIn.value.trim();
                    if (!val) { if(disp){disp.style.opacity='0';} if(typeRow) typeRow.style.display='none'; return; }
                    const parsed = parseDeadlineInput(val);
                    if (parsed && disp) {
                        const nice = parsed.toLocaleDateString([], {weekday:'short',day:'numeric',month:'short'}) + ' ' + parsed.toLocaleTimeString([],{hour:'numeric',minute:'2-digit'});
                        disp.textContent = '→ ' + nice; disp.style.color = 'var(--green)'; disp.style.opacity = '1';
                        if (typeRow) typeRow.style.display = 'flex';
                    } else if (disp) { disp.textContent = '→ Could not parse'; disp.style.color = 'var(--red)'; disp.style.opacity = '1'; if(typeRow) typeRow.style.display='none'; }
                }, 600);
            });
        }
    };

    // ── FOCUS PROTOCOL SYNC (SOFT LOCK) ────────────────────────
    let focusTickInterval = null;
    let focusStatusInterval = null;
    let focusDefenseInterval = null;
    let currentFocusMinutesLeft = 0;
    let totalFocusSecondsInitial = 0;
    let deflections = 0;
    let isPaused = false;
    let activeBlockedSites = [];

    async function checkFocusState() {
        try {
            const res = await fetch('/api/focus_state');
            if (res.ok) {
                const data = await res.json();
                if (data.focus_active) {
                    if (data.paused && !isPaused) {
                        isPaused = true;
                        updatePauseUI();
                    } else if (!data.paused && isPaused) {
                        isPaused = false;
                        updatePauseUI();
                    }
                    activateFocusLock(data);
                } else {
                    if (focusTickInterval) deactivateFocusLock();
                }
            }
        } catch (e) { console.error("Focus sync error:", e); }
    }

    function activateFocusLock(data) {
        if (!focusTickInterval && !document.getElementById('focus-overlay').classList.contains('active')) {
            document.body.classList.add('state-deep-work');
            const overlay = document.getElementById('focus-overlay');
            overlay.classList.add('active');
            
            const titleEl = document.getElementById('focus-task-title');
            if (titleEl) titleEl.innerText = data.task_title || '[★ PRIME TARGET]';
            
            const notesEl = document.getElementById('focus-task-notes');
            if (notesEl) notesEl.innerText = data.task_notes || 'No tactical notes provided for this mission.';

            const blockEl = document.getElementById('focus-blocked-list');
            if (blockEl && data.blocked_items && data.blocked_items.sites) {
                activeBlockedSites = data.blocked_items.sites;
                blockEl.innerHTML = activeBlockedSites.map(s => 
                    `<div class="badge tag" style="background:color-mix(in srgb, var(--accent-danger) 10%, transparent); border-color:color-mix(in srgb, var(--accent-danger) 30%, transparent); color:var(--red);">${s}</div>`
                ).join('');
            } else {
                activeBlockedSites = [];
            }
            
            const cycles = data.cycles_completed || 0;
            const cycleText = document.getElementById('focus-cycle-text');
            if (cycleText) cycleText.innerText = `${(cycles % 4) + 1} / 4`;
            const cycleBar = document.getElementById('focus-cycle-bar');
            if (cycleBar) cycleBar.style.width = `${(((cycles % 4) + 1)/4)*100}%`;

            currentFocusMinutesLeft = data.minutes_left || data.remaining_minutes || 0;
            const currentSecs = data.remaining_seconds || 0;
            totalFocusSecondsInitial = (currentFocusMinutesLeft * 60) + currentSecs;
            
            updateFocusTimerDisplay(currentFocusMinutesLeft, currentSecs);

            let totalSeconds = totalFocusSecondsInitial;
            focusTickInterval = setInterval(() => {
                if (isPaused) return;
                if (totalSeconds > 0) {
                    totalSeconds--;
                    const m = Math.floor(totalSeconds / 60);
                    const s = totalSeconds % 60;
                    updateFocusTimerDisplay(m, s);
                    updateProgressAndGlow(totalSeconds, totalFocusSecondsInitial);
                } else {
                    completeFocusSession();
                }
            }, 1000);
            
            startMentalSupportFeed();
            startDefenseFeed();

            document.addEventListener('keydown', focusKeydownHandler);
        }
    }

    function updateProgressAndGlow(remaining, initial) {
        if (initial === 0) return;
        const passedData = initial - remaining;
        const progressPct = (passedData / initial) * 100;
        document.getElementById('focus-progress-bar').style.width = `${progressPct}%`;

        const timerEl = document.getElementById('focus-timer');
        const overlay = document.getElementById('focus-overlay');
        
        if (remaining <= 60) {
            timerEl.style.color = 'var(--red)';
            timerEl.style.textShadow = '0 0 50px color-mix(in srgb, var(--accent-danger) 50%, transparent)';
        } else if (remaining <= 300) {
            timerEl.style.color = '#f0a030';
            timerEl.style.textShadow = '0 0 50px rgba(240,160,48,0.5)';
        } else {
            timerEl.style.color = 'var(--blue)';
        }

        const elapsedMins = Math.floor(passedData / 60);
        if (elapsedMins >= 20) overlay.style.boxShadow = 'inset 0 0 100px color-mix(in srgb, var(--accent-ai) 30%, transparent)';
        else if (elapsedMins >= 10) overlay.style.boxShadow = 'inset 0 0 80px color-mix(in srgb, var(--accent-info) 20%, transparent)';
        else if (elapsedMins >= 5) overlay.style.boxShadow = 'inset 0 0 50px color-mix(in srgb, var(--accent-info) 10%, transparent)';
        else overlay.style.boxShadow = 'none';
    }

    function startMentalSupportFeed() {
        const statuses = [
            { t: 0, text: "Stabilizing focus..." },
            { t: 5, text: "Momentum building..." },
            { t: 10, text: "Deep focus detected..." },
            { t: 20, text: "Peak performance zone..." }
        ];
        const statusEl = document.getElementById('focus-status-text');
        
        focusStatusInterval = setInterval(() => {
            if (isPaused) {
                statusEl.innerText = "Session paused — discipline maintained.";
                return;
            }
            const elapsedMins = Math.floor((totalFocusSecondsInitial / 60) - currentFocusMinutesLeft);
            let currentText = statuses[0].text;
            for (let s of statuses) {
                if (elapsedMins >= s.t) currentText = s.text;
            }
            statusEl.innerText = currentText;
        }, 10000);
    }

    function startDefenseFeed() {
        deflections = 0;
        const feedEl = document.getElementById('focus-defense-feed');
        const counterEl = document.getElementById('focus-defense-counter');
        
        focusDefenseInterval = setInterval(() => {
            if (isPaused || activeBlockedSites.length === 0) return;
            
            if (Math.random() > 0.4) {
                const site = activeBlockedSites[Math.floor(Math.random() * activeBlockedSites.length)];
                feedEl.innerText = `✦ ${site} access neutralized.`;
                feedEl.style.opacity = '1';
                deflections++;
                counterEl.innerText = `✦ ${deflections} breach attempts deflected`;
                
                setTimeout(() => { feedEl.style.opacity = '0'; }, 3000);
            }
        }, 40000);
    }

    window.assistExecution = () => {
        const title = document.getElementById('focus-task-title').innerText;
        const btn = document.getElementById('btn-focus-ai');
        if(btn) btn.classList.remove('pulsing');
        
        const tips = [
            `Step 1: Define the exact deliverable for "${title}"`,
            `Step 2: Write the ugliest first draft. Perfection kills momentum.`,
            `Step 3: Set a micro-deadline: finish one section in the next 5 mins.`,
            `⚡ Power move: Close every tab except the one you need right now.`,
            `🎯 Focus anchor: What is the ONE thing that moves this forward?`
        ];
        const tip = tips[Math.floor(Math.random() * tips.length)];
        showToast(`✦ AI ADVISOR: ${tip}`, "var(--ai-purple)");
    }

    function deactivateFocusLock() {
        document.body.classList.remove('state-deep-work');
        document.getElementById('focus-overlay').classList.remove('active');
        document.removeEventListener('keydown', focusKeydownHandler);
        if (focusTickInterval) clearInterval(focusTickInterval);
        if (focusStatusInterval) clearInterval(focusStatusInterval);
        if (focusDefenseInterval) clearInterval(focusDefenseInterval);
        focusTickInterval = null; focusStatusInterval = null; focusDefenseInterval = null;
        isPaused = false;
        document.getElementById('focus-progress-bar').style.width = '0%';
        document.getElementById('focus-overlay').style.boxShadow = 'none';
        document.getElementById('focus-timer').style.color = 'var(--blue)';
        document.getElementById('focus-timer').style.textShadow = '';
    }

    function updateFocusTimerDisplay(m, s = 0) {
        currentFocusMinutesLeft = m; 
        const timerEl = document.getElementById('focus-timer');
        if (timerEl) {
            timerEl.innerText = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
    }

    window.showAbortModal = () => {
        document.getElementById('focus-overlay').classList.add('blur-heavy');
        document.getElementById('abort-modal').classList.add('active');
    }
    window.hideAbortModal = () => {
        document.getElementById('focus-overlay').classList.remove('blur-heavy');
        document.getElementById('abort-modal').classList.remove('active');
    }
    window.confirmAbortFocus = async () => {
        hideAbortModal();
        try {
            await fetch('/api/focus_end', {method: 'POST'});
            deactivateFocusLock();
            showToast("Focus sequence aborted.", "var(--red)");
            loadTasks();
        } catch(e) { console.error(e); }
    };
    
    window.promptCompleteMission = () => {
        const remaining = document.getElementById('focus-timer').innerText;
        document.getElementById('complete-modal-time').innerText = `Remaining time: ${remaining}`;
        document.getElementById('focus-overlay').classList.add('blur-heavy');
        document.getElementById('complete-modal').classList.add('active');
    };
    window.hideCompleteModal = () => {
        document.getElementById('focus-overlay').classList.remove('blur-heavy');
        document.getElementById('complete-modal').classList.remove('active');
    };
    window.submitMissionComplete = async () => {
        const timeUsedSecs = totalFocusSecondsInitial - (currentFocusMinutesLeft * 60 + currentFocusSecondsLeft);
        const timeSavedMins = currentFocusMinutesLeft;
        const timeUsedMins = Math.floor(timeUsedSecs / 60);
        const effScore = Math.floor((totalFocusSecondsInitial / (timeUsedSecs > 0 ? timeUsedSecs : 1)) * 100);
        const finalEffScore = effScore > 500 ? 500 : effScore;
        
        hideCompleteModal();
        deactivateFocusLock();
        
        try {
            const res = await fetch('/api/focus/complete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    efficiency_score: finalEffScore, 
                    time_saved: timeSavedMins,
                    time_used: timeUsedMins
                })
            });
            loadTasks();
            
            // Show live Dopamine toast from response
            try {
                if (res.ok) {
                    const dopa = await res.json();
                    if (dopa.velocity) {
                        const dayWord = dopa.streak === 1 ? 'Day' : 'Days';
                        showToast(`✦ FOCUS COMPLETE  +${dopa.velocity}% Velocity | Streak: ${dopa.streak} ${dayWord} | Today: ${dopa.daily_completions}`, "var(--green)");
                    }
                }
            } catch(te) {}
            
            // Also show reward screen
            document.getElementById('reward-minutes').innerText = timeUsedMins;
            const cycleText = document.getElementById('focus-cycle-text');
            const cText = cycleText ? `Focus Cycle ${cycleText.innerText} Completed` : 'Focus Cycle Completed';
            document.getElementById('reward-cycle-text').innerText = cText;
            document.getElementById('reward-screen').classList.add('active');

        } catch(e) { console.error(e); }
    };

    async function openMomentumDeployment(usedMins, savedMins, effScore, cycleText) {
        // Set stats in unified modal
        document.getElementById('momentum-cycle-text').innerText = cycleText;
        document.getElementById('momentum-reward-minutes').innerText = usedMins;
        const effEl = document.getElementById('momentum-efficiency');
        if (effScore > 100) {
            effEl.innerHTML = `Execution Efficiency <span style="color:var(--emerald);">+${effScore - 100}% ↑</span>`;
        } else {
            effEl.innerHTML = `Execution Efficiency <span style="color:var(--emerald);">Validated</span>`;
        }

        try {
            const res = await fetch('/api/focus/next');
            if (res.ok) {
                const data = await res.json();
                renderMomentumTargets(data.targets || []);
            }
        } catch(e) { console.error(e); }
    }
    
    function renderMomentumTargets(targets) {
        const container = document.getElementById('momentum-targets-container');
        if (!targets || targets.length === 0) {
            container.innerHTML = `
                <div style="text-align:center; padding: 20px; color: var(--text-muted); font-style: italic;">
                    No pending missions remain.<br>Sequence complete.
                </div>
            `;
        } else {
            container.innerHTML = targets.map((t, idx) => `
                <div class="task-card" style="padding: 20px; cursor: default; transition:all 0.3s;" onmouseenter="this.style.boxShadow='0 0 20px color-mix(in srgb, var(--accent-info) 20%, transparent)'; this.style.transform='translateX(4px)'" onmouseleave="this.style.boxShadow='none'; this.style.transform='none'">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-weight:700; color:var(--text-hero); font-size: 18px; margin-bottom: 8px;">${escapeHtml(t.title)}</div>
                            <div style="display:flex; gap:8px;">
                                <span class="badge ${t.priority.toLowerCase()}">${t.priority.toUpperCase()}</span>
                                ${idx===0 ? '<span class="badge tag" style="color:var(--emerald); border-color:var(--emerald);">#1 Optimal</span>' : ''}
                            </div>
                        </div>
                        <button class="btn-execute" onclick="launchSuggestedTask(${t.id})" style="background:var(--blue); min-width: 120px;">DEPLOY ▶</button>
                    </div>
                </div>
            `).join('');
        }
        
        // Blur background UI and show modal
        document.body.classList.add('state-deep-work'); // reuses background blur
        document.getElementById('momentum-modal').classList.add('active');
    }
    
    window.launchSuggestedTask = (taskId) => {
        hideMomentumModal();
        startFocus(taskId);
    };

    window.hideMomentumModal = () => {
        document.getElementById('momentum-modal').classList.remove('active');
        document.body.classList.remove('state-deep-work');
    };

    window.togglePauseFocus = async () => {
        const resumeBtn = document.getElementById('btn-focus-resume');
        
        if (!isPaused) {
            isPaused = true;
            try { await fetch('/api/focus/pause', {method: 'POST'}); } catch(e) { console.error(e); }
            updatePauseUI();
            
            resumeBtn.disabled = true;
            resumeBtn.style.opacity = '0.5';
            let cd = 5;
            const cdEl = document.getElementById('resume-cooldown');
            cdEl.innerText = `(${cd}s)`;
            const cdInt = setInterval(() => {
                cd--;
                if (cd > 0) { cdEl.innerText = `(${cd}s)`; } 
                else { 
                    clearInterval(cdInt); 
                    cdEl.innerText = ''; 
                    resumeBtn.disabled = false; 
                    resumeBtn.style.opacity = '1'; 
                }
            }, 1000);
        } else {
            if (resumeBtn.disabled) return;
            isPaused = false;
            try { await fetch('/api/focus/resume', {method: 'POST'}); } catch(e) { console.error(e); }
            updatePauseUI();
        }
    };

    function updatePauseUI() {
        if (isPaused) {
            document.getElementById('focus-timer').classList.remove('timer-running');
            document.getElementById('focus-controls').style.display = 'none';
            document.getElementById('focus-resume-controls').style.display = 'flex';
            document.getElementById('focus-paused-indicator').style.display = 'block';
            document.getElementById('focus-timer').style.opacity = '0.3';
        } else {
            document.getElementById('focus-timer').classList.add('timer-running');
            document.getElementById('focus-controls').style.display = 'flex';
            document.getElementById('focus-resume-controls').style.display = 'none';
            document.getElementById('focus-paused-indicator').style.display = 'none';
            document.getElementById('focus-timer').style.opacity = '1';
        }
    }

    function completeFocusSession() {
        // Natural end of timer - trigger submission
        window.submitMissionComplete();
    }
    window.closeRewardScreen = () => {
        document.getElementById('reward-screen').classList.remove('active');
    };

    function focusKeydownHandler(e) {
        if (document.getElementById('abort-modal').classList.contains('active')) return;
        
        if (e.code === 'Space') {
            e.preventDefault();
            window.togglePauseFocus();
        } else if (e.code === 'Escape') {
            e.preventDefault();
            window.showAbortModal();
        } else if (e.code === 'KeyA') {
            e.preventDefault();
            window.assistExecution();
        }
    }


    // ── 3D PARTICLE SIMULATION (THREE.JS) ─────────────────────────────
    let scene, camera, renderer;
    let currentParticles = null;
    let animationId = null;
    let activeSimType = null;
    let clock = null;

    // THEME: particle colour follows --particle-color so it adapts per theme
    // (e.g. subtle dark dots on Paper instead of invisible blue-on-white).
    function tfParticleRGB() {
        try {
            const v = getComputedStyle(document.documentElement).getPropertyValue('--particle-color').trim();
            const m = v.match(/(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
            if (m) return (parseInt(m[1]) << 16) | (parseInt(m[2]) << 8) | parseInt(m[3]);
        } catch (e) {}
        return 0x58A6FF;
    }
    function tfUpdateParticleTheme() {
        const c = tfParticleRGB();
        if (currentParticles && currentParticles.traverse) {
            currentParticles.traverse(o => { if (o.material && o.material.color) o.material.color.setHex(c); });
        }
    }
    window.tfUpdateParticleTheme = tfUpdateParticleTheme;

    // ── Fix 3: Operator particle settings (toggle + opacity + why), persisted ──
    function tfApplyParticleSettings(fade) {
        const c = document.getElementById('threejs-canvas');
        if (c) {
            if (fade) c.style.transition = 'opacity 500ms ease';
            c.style.opacity = (window.tfParticlesEnabled === false) ? '0' : String(window.tfParticlesOpacity || 0.25);
        }
        if (window.tfParticlesEnabled === false) {
            if (animationId) { cancelAnimationFrame(animationId); animationId = null; }
        } else if (!animationId && typeof activeSimType === 'string' && activeSimType) {
            animateSimulation(activeSimType);
        }
    }
    function tfSyncOperatorPanel() {
        const tog = document.getElementById('op-particle-toggle');
        const wrap = document.getElementById('op-opacity-wrap');
        const sl = document.getElementById('op-opacity-slider');
        const val = document.getElementById('op-opacity-val');
        const on = window.tfParticlesEnabled !== false;
        if (tog) tog.classList.toggle('on', on);
        if (wrap) wrap.classList.toggle('open', on);
        const pct = Math.round((window.tfParticlesOpacity || 0.25) * 100);
        if (sl) sl.value = String(pct);
        if (val) val.textContent = pct + '%';
    }
    function tfOpOutside(ev) {
        const bar = document.getElementById('operator-bar');
        if (bar && !bar.contains(ev.target)) tfCloseOperatorPanel();
    }
    function tfOpEsc(ev) { if (ev.key === 'Escape') tfCloseOperatorPanel(); }
    function tfCloseOperatorPanel() {
        const p = document.getElementById('operator-panel');
        if (p) p.classList.remove('open');
        document.removeEventListener('click', tfOpOutside);
        document.removeEventListener('keydown', tfOpEsc);
    }
    window.tfToggleOperatorPanel = function(e) {
        if (e) e.stopPropagation();
        const p = document.getElementById('operator-panel');
        if (!p) return;
        if (p.classList.contains('open')) { tfCloseOperatorPanel(); return; }
        tfSyncOperatorPanel();
        tfSyncThemeUI();
        p.classList.add('open');
        setTimeout(() => { document.addEventListener('click', tfOpOutside); document.addEventListener('keydown', tfOpEsc); }, 0);
    };
    window.tfToggleParticles = function() {
        window.tfParticlesEnabled = !(window.tfParticlesEnabled !== false);
        localStorage.setItem('tf_particles_enabled', window.tfParticlesEnabled ? 'true' : 'false');
        tfSyncOperatorPanel();
        tfApplyParticleSettings(true);
    };
    window.tfParticleOpacityInput = function(v) {
        window.tfParticlesOpacity = (parseInt(v, 10) || 25) / 100;
        const val = document.getElementById('op-opacity-val');
        if (val) val.textContent = (parseInt(v, 10) || 25) + '%';
        const c = document.getElementById('threejs-canvas');
        if (c && window.tfParticlesEnabled !== false) c.style.opacity = String(window.tfParticlesOpacity);
    };
    window.tfParticleOpacitySave = function(v) {
        localStorage.setItem('tf_particles_opacity', String(parseInt(v, 10) || 25));
    };
    window.tfToggleWhy = function() {
        const p = document.getElementById('op-why-panel');
        if (p) p.classList.toggle('open');
    };

    // ── THEME SYSTEM ──────────────────────────────────────────────────
    window.tfActiveTheme = localStorage.getItem('tf_active_theme') || 'midnight';
    const TF_THEMES = [
        { id: 'midnight', label: 'Midnight', bg: '#0D1117', accent: '#58A6FF' },
        { id: 'terminal', label: 'Terminal', bg: '#000000', accent: '#00FF9C' },
        { id: 'paper',    label: 'Paper',    bg: '#F6F5F2', accent: '#0066CC' },
        { id: 'slate',    label: 'Slate',    bg: '#1A1D23', accent: '#6B9BD1' }
    ];
    const TF_CUSTOM_VARS = ['--bg-base', '--bg-surface', '--text-primary', '--accent-info'];
    function tfClearCustomInline() { TF_CUSTOM_VARS.forEach(v => document.documentElement.style.removeProperty(v)); }
    function tfToHex(s) {
        s = (s || '').trim();
        if (s.startsWith('#')) return s.length === 4 ? '#' + s.slice(1).split('').map(c => c + c).join('') : s.slice(0, 7);
        const m = s.match(/(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
        if (m) return '#' + [1, 2, 3].map(i => parseInt(m[i]).toString(16).padStart(2, '0')).join('');
        return '';
    }
    function tfSyncThemeSwatches() {
        document.querySelectorAll('.op-swatch').forEach(s => s.classList.toggle('active', s.dataset.themeId === (window.tfActiveTheme || 'midnight')));
    }
    window.tfApplyTheme = function(name, save) {
        const root = document.documentElement;
        tfClearCustomInline();
        if (name === 'custom') {
            root.removeAttribute('data-theme');
            try { const c = JSON.parse(localStorage.getItem('tf_custom_theme') || '{}'); for (const k in c) root.style.setProperty(k, c[k]); } catch (e) {}
        } else if (name && name !== 'midnight') {
            root.setAttribute('data-theme', name);
        } else {
            root.removeAttribute('data-theme');
        }
        window.tfActiveTheme = name || 'midnight';
        if (save !== false) localStorage.setItem('tf_active_theme', window.tfActiveTheme);
        if (window.tfUpdateParticleTheme) window.tfUpdateParticleTheme();
        tfSyncThemeSwatches();
    };
    function tfRenderThemeSwatches() {
        const wrap = document.getElementById('op-theme-swatches');
        if (!wrap) return;
        const defs = TF_THEMES.slice();
        const custom = localStorage.getItem('tf_custom_theme');
        if (custom) { try { const c = JSON.parse(custom); defs.push({ id: 'custom', label: 'Custom', bg: c['--bg-base'] || '#0D1117', accent: c['--accent-info'] || '#58A6FF' }); } catch (e) {} }
        wrap.innerHTML = defs.map(d =>
            '<div class="op-swatch-wrap"><button class="op-swatch" data-theme-id="' + d.id + '" title="' + d.label + '" onclick="tfApplyTheme(\'' + d.id + '\')" style="background:linear-gradient(135deg,' + d.bg + ' 0 50%,' + d.accent + ' 50% 100%);"></button><span class="op-swatch-label">' + d.label + '</span></div>'
        ).join('');
        tfSyncThemeSwatches();
    }
    function tfSeedPickers() {
        try {
            const cs = getComputedStyle(document.documentElement);
            const set = (id, v) => { const el = document.getElementById(id); if (el) { const h = tfToHex(cs.getPropertyValue(v)); if (h) el.value = h; } };
            set('tf-pick-bg', '--bg-base'); set('tf-pick-surface', '--bg-surface'); set('tf-pick-text', '--text-primary'); set('tf-pick-accent', '--accent-info');
        } catch (e) {}
    }
    function tfSyncThemeUI() { tfRenderThemeSwatches(); tfSeedPickers(); }
    window.tfPickVar = function(v, val) {
        document.documentElement.style.setProperty(v, val);
        if (window.tfUpdateParticleTheme) window.tfUpdateParticleTheme();
    };
    window.tfToggleCustomize = function() { const p = document.getElementById('op-custom-panel'); if (p) p.classList.toggle('open'); };
    window.tfSaveCustomTheme = function() {
        const g = id => { const el = document.getElementById(id); return el ? el.value : null; };
        const c = { '--bg-base': g('tf-pick-bg'), '--bg-surface': g('tf-pick-surface'), '--text-primary': g('tf-pick-text'), '--accent-info': g('tf-pick-accent') };
        localStorage.setItem('tf_custom_theme', JSON.stringify(c));
        localStorage.setItem('tf_active_theme', 'custom');
        window.tfApplyTheme('custom');
        tfRenderThemeSwatches();
        try { showToast('Custom theme saved', 'var(--accent-success)'); } catch (e) {}
    };
    window.tfResetTheme = function() {
        localStorage.removeItem('tf_active_theme'); localStorage.removeItem('tf_custom_theme');
        tfClearCustomInline();
        document.documentElement.removeAttribute('data-theme');
        window.tfActiveTheme = 'midnight';
        if (window.tfUpdateParticleTheme) window.tfUpdateParticleTheme();
        tfSyncThemeUI();
        try { showToast('Reset to Midnight', 'var(--accent-info)'); } catch (e) {}
    };

    function initThreeJS() {
        const container = document.getElementById('threejs-canvas');
        if (!container || typeof THREE === 'undefined') return;

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.z = 5;

        renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);
        // Fix 3: load persisted particle settings (default ON @ 25%) and apply
        window.tfParticlesEnabled = (localStorage.getItem('tf_particles_enabled') !== 'false');
        window.tfParticlesOpacity = (parseInt(localStorage.getItem('tf_particles_opacity') || '25', 10) || 25) / 100;
        tfApplyParticleSettings(false);

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        clock = new THREE.Clock();
        startSimulation('execution'); // Default on load
    }

    function cleanupParticles() {
        if (currentParticles) {
            scene.remove(currentParticles);
            if (currentParticles.geometry) currentParticles.geometry.dispose();
            if (currentParticles.material) {
                if (currentParticles.material.map) currentParticles.material.map.dispose();
                currentParticles.material.dispose();
            }
            currentParticles = null;
        }
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
    }

    function startSimulation(type) {
        if (activeSimType === type || typeof THREE === 'undefined') return;
        cleanupParticles();
        activeSimType = type;

        if (type === 'execution') currentParticles = createNeuralMesh();
        else if (type === 'missions') currentParticles = createEmbers();
        else if (type === 'focus') currentParticles = createFlowState();

        if (currentParticles) {
            scene.add(currentParticles);
            animateSimulation(type);
        }
    }

    // Concept 1: "The Neural Mesh" (Execution tab)
    function createNeuralMesh() {
        const group = new THREE.Group();
        const particleCount = 150;
        const positions = new Float32Array(particleCount * 3);
        const pts = [];
        for (let i = 0; i < particleCount; i++) {
            const x = (Math.random() - 0.5) * 12;
            const y = (Math.random() - 0.5) * 12;
            const z = (Math.random() - 0.5) * 12;
            positions[i*3] = x; positions[i*3+1] = y; positions[i*3+2] = z;
            pts.push(new THREE.Vector3(x, y, z));
        }
        const pGeo = new THREE.BufferGeometry();
        pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const pMat = new THREE.PointsMaterial({color: tfParticleRGB(), size: 0.04, transparent: true, opacity: 0.9});
        group.add(new THREE.Points(pGeo, pMat));

        // Connect nodes
        const linePos = [];
        for(let i=0; i<particleCount; i++) {
            for(let j=i+1; j<particleCount; j++) {
                if(pts[i].distanceTo(pts[j]) < 2.0) {
                    linePos.push(pts[i].x, pts[i].y, pts[i].z);
                    linePos.push(pts[j].x, pts[j].y, pts[j].z);
                }
            }
        }
        const lGeo = new THREE.BufferGeometry();
        lGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePos, 3));
        const lMat = new THREE.LineBasicMaterial({color: tfParticleRGB(), transparent: true, opacity: 0.15});
        group.add(new THREE.LineSegments(lGeo, lMat));
        return group;
    }

    // Concept 2: "Deep Work Embers" (Missions tab)
    function createEmbers() {
        const canvas = document.createElement('canvas');
        canvas.width = 32; canvas.height = 32;
        const ctx = canvas.getContext('2d');
        const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
        grad.addColorStop(0, 'rgba(255,255,255,1)');            // canvas 2D can't parse var()/color-mix — keep literal
        grad.addColorStop(0.2, 'rgba(210,153,34,0.8)');         // warm ember sprite (material colour themed via tfParticleRGB)
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0,0,32,32);
        const sprite = new THREE.CanvasTexture(canvas);

        const count = 60;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        const phases = new Float32Array(count);
        for (let i = 0; i < count; i++) {
            pos[i*3] = (Math.random() - 0.5) * 15;
            pos[i*3+1] = (Math.random() - 0.5) * 15;
            pos[i*3+2] = (Math.random() - 0.5) * 15;
            phases[i] = Math.random() * Math.PI * 2;
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({
            size: 0.4, map: sprite, transparent: true, opacity: 0.5,
            color: 0xffddaa, blending: THREE.AdditiveBlending, depthWrite: false
        });
        const points = new THREE.Points(geo, mat);
        points.userData.phases = phases;
        return points;
    }

    // Concept 3: "The Flow State" (Focus / Deep Work tab)
    function createFlowState() {
        const count = 400;
        const linePos = new Float32Array(count * 6); // 2 vertices per line
        const velocities = new Float32Array(count);
        for (let i = 0; i < count; i++) {
            const x = (Math.random() - 0.5) * 15;
            const y = (Math.random() - 0.5) * 15;
            const z = (Math.random() - 0.5) * 20;
            const v = 0.02 + Math.random() * 0.05;
            const length = v * 20; // Trail length
            
            linePos[i*6] = x; linePos[i*6+1] = y; linePos[i*6+2] = z;     // start
            linePos[i*6+3] = x; linePos[i*6+4] = y; linePos[i*6+5] = z - length; // end
            velocities[i] = v;
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
        const mat = new THREE.LineBasicMaterial({color: tfParticleRGB(), transparent: true, opacity: 0.4});
        const lines = new THREE.LineSegments(geo, mat);
        lines.userData.velocities = velocities;
        return lines;
    }

    function animateSimulation(type) {
        if (activeSimType !== type) return;
        if (window.tfParticlesEnabled === false) { animationId = null; return; }   // OPERATOR M off-switch (only control)
        animationId = requestAnimationFrame(() => animateSimulation(type));
        if (!currentParticles) return;

        if (type === 'execution') {
            currentParticles.rotation.y += 0.0008;
            currentParticles.rotation.x += 0.0004;
        } else if (type === 'missions') {
            const pos = currentParticles.geometry.attributes.position.array;
            const phases = currentParticles.userData.phases;
            const time = Date.now() * 0.001;
            
            for (let i = 0; i < 60; i++) {
                pos[i*3 + 1] += 0.003; // Slowly drift up
                pos[i*3] += Math.sin(time + phases[i]) * 0.001; // Gentle sway
                if (pos[i*3+1] > 7) pos[i*3+1] = -7;
            }
            currentParticles.geometry.attributes.position.needsUpdate = true;
            // Pulse opacity slightly
            if (currentParticles.material) {
                currentParticles.material.opacity = 0.3 + 0.2 * Math.sin(time * 0.5);
            }
        } else if (type === 'focus') {
            const pos = currentParticles.geometry.attributes.position.array;
            const velocities = currentParticles.userData.velocities;
            for (let i = 0; i < 400; i++) {
                pos[i*6 + 2] += velocities[i];
                pos[i*6 + 5] += velocities[i];
                if (pos[i*6 + 2] > 10) {
                    const length = velocities[i] * 20;
                    pos[i*6 + 2] = -10;
                    pos[i*6 + 5] = -10 - length;
                }
            }
            currentParticles.geometry.attributes.position.needsUpdate = true;
        }
        renderer.render(scene, camera);
    }



    