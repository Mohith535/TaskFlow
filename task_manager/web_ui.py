HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow | Mission Control</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400&family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <style>
        /* ─── RESET ─────────────────────────────── */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        /* ─── SCROLLBAR ─────────────────────────── */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #30363D; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #6E7681; }

        /* ─── DESIGN TOKENS ─────────────────────── */
        :root {
            --bg-deep:     #060A0F;
            --bg-primary:  #0D1117;
            --bg-surface:  #161B22;
            --bg-hover:    #1C2128;
            --border-subtle:  #21262D;
            --border-neutral: #30363D;

            --blue:        #58A6FF;
            --blue-dark:   #1F6FEB;
            --blue-mid:    #388BFD;

            --ai-purple:   #A371F7;
            --ai-dark:     #7C3AED;

            --green:       #3FB950;
            --red:         #F85149;
            --amber:       #D29922;

            --text-hero:      #E6EDF3;
            --text-body:      #C9D1D9;
            --text-muted:     #8B949E;
            --text-disabled:  #6E7681;

            --font-mono: 'DM Mono', monospace;
            --font-body: 'Inter', sans-serif;

            /* System States */
            --system-blur: 12px;
            --system-opacity: 0.72;
            --col-sidebar-width: 260px;
            --col-advisor-width: 320px;
        }

        /* ─── BODY ──────────────────────────────── */
        body {
            background-color: var(--bg-primary);
            color: var(--text-body);
            font-family: var(--font-body);
            font-feature-settings: 'cv02','cv03','cv04','cv11';
            line-height: 1.6;
            height: 100vh;
            overflow: hidden;
            display: flex;
            padding: 24px;
            gap: 24px;
            position: relative;
            transition: background-color 1200ms cubic-bezier(0.16, 1, 0.3, 1);
            cursor: default;
        }

        /* ─── AMBIENT LAYERS ────────────────────── */
        #bg-parallax {
            position: fixed; inset: -50px; z-index: -1;
            background: 
                radial-gradient(circle at 20% 30%, rgba(31,111,235,0.05) 0%, transparent 40%),
                radial-gradient(circle at 80% 70%, rgba(163,113,247,0.05) 0%, transparent 40%);
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }

        #bg-grid {
            position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: 0.1;
            background-image: radial-gradient(circle at 1px 1px, var(--border-neutral) 1px, transparent 0);
            background-size: 40px 40px;
            mask-image: radial-gradient(circle at 50% 50%, black, transparent 80%);
        }

        #hud-scanlines {
            position: fixed; inset: 0; z-index: 1; pointer-events: none; opacity: 0.03;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
                        linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
            background-size: 100% 4px, 3px 100%;
        }

        /* ─── COLUMNS (GLASSMORPHISM) ───────────── */
        .col-sidebar, .col-advisor {
            flex-shrink: 0; height: 100%; display: flex; flex-direction: column;
            background: rgba(13, 17, 23, 0.6);
            backdrop-filter: blur(var(--system-blur));
            -webkit-backdrop-filter: blur(var(--system-blur));
            border: 1px solid var(--border-subtle);
            border-radius: 20px; transition: all 800ms cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 10;
        }
        .col-sidebar { width: var(--col-sidebar-width); padding: 32px 20px; }
        .col-advisor { width: var(--col-advisor-width); padding: 32px 24px; }
        .col-main {
            flex-grow: 1; height: 100%; overflow-y: auto; overflow-x: hidden;
            display: flex; flex-direction: column; gap: 24px; padding: 0 10px;
            scrollbar-width: none; z-index: 5;
        }
        .col-main::-webkit-scrollbar { display: none; }

        /* System State Effects */
        body.state-deep-work .col-sidebar, 
        body.state-deep-work .col-advisor { 
            opacity: 0.15; filter: blur(8px); transform: scale(0.98); pointer-events: none;
        }

        /* ─── SIDEBAR ELEMENTS ──────────────────── */
        .logo-area { margin-bottom: 40px; display: flex; align-items: center; gap: 12px; padding: 0 12px; }
        .logo-task { font-size: 20px; font-weight: 700; color: var(--text-hero); letter-spacing: -1px; }
        .logo-flow { color: var(--blue); }
        .logo-wave { color: var(--blue); font-size: 22px; animation: glowPulse 3s infinite; }
        
        .nav-section-label { 
            font-size: 10px; font-weight: 700; color: var(--text-disabled); 
            letter-spacing: 2px; margin: 24px 0 12px 12px; text-transform: uppercase;
        }
        .nav-item {
            display: flex; align-items: center; gap: 12px; padding: 12px;
            border-radius: 10px; cursor: pointer; color: var(--text-muted);
            transition: all 200ms ease; margin-bottom: 4px; border: 1px solid transparent;
        }
        .nav-item:hover { background: var(--bg-hover); color: var(--text-body); }
        .nav-item.active { 
            background: rgba(88,166,255,0.08); color: var(--blue); 
            border-color: rgba(88,166,255,0.1); font-weight: 600;
        }
        .nav-icon { font-size: 16px; width: 20px; text-align: center; }

        /* ─── AI INPUT HUD ──────────────────────── */
        .ai-zone {
            background: var(--bg-surface);
            border-radius: 20px; border: 1px solid var(--border-neutral);
            padding: 32px; margin-bottom: 24px; position: relative;
            box-shadow: 0 16px 40px rgba(0,0,0,0.4);
        }
        .ai-zone::before {
            content: ''; position: absolute; inset: -2px; border-radius: 22px;
            background: linear-gradient(135deg, var(--blue-mid), var(--ai-purple));
            opacity: 0; transition: opacity 400ms; z-index: -1;
        }
        .ai-zone:focus-within::before { opacity: 0.15; }

        .ai-input-wrap { display: flex; gap: 16px; align-items: center; }
        .ai-input {
            background: transparent; border: none; font-size: 18px; font-weight: 500;
            color: var(--text-hero); width: 100%; outline: none;
        }
        .ai-input::placeholder { color: var(--text-disabled); font-style: italic; opacity: 0.6; }
        
        .btn-execute {
            background: var(--blue-dark); color: #fff; border: none;
            padding: 10px 24px; border-radius: 10px; font-weight: 600;
            cursor: pointer; transition: all 200ms; box-shadow: 0 4px 12px rgba(31,111,235,0.3);
        }
        .btn-execute:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(31,111,235,0.5); filter: brightness(1.1); }

        /* ─── MISSION PANEL ─────────────────────── */
        .mission-panel {
            background: rgba(22, 27, 34, 0.4); border: 1px solid var(--border-neutral);
            border-radius: 16px; padding: 24px; margin-bottom: 32px;
        }
        .section-label { 
            font-size: 11px; font-weight: 700; color: var(--text-disabled); 
            letter-spacing: 2.5px; margin-bottom: 16px; text-transform: uppercase;
        }
        .flex-row { display: flex; gap: 16px; }
        .mission-field { flex: 1; display: flex; flex-direction: column; gap: 8px; }
        .input-system {
            background: #0D1117; border: 1px solid var(--border-neutral);
            border-radius: 8px; padding: 12px 14px; color: var(--text-hero);
            outline: none; transition: all 150ms; font-size: 14px;
        }
        .input-system:focus { border-color: var(--blue); }

        .priority-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
        .pill-btn {
            border: 1px solid var(--border-neutral); background: transparent;
            padding: 10px; border-radius: 8px; font-size: 12px; font-weight: 600;
            cursor: pointer; color: var(--text-muted); transition: all 150ms;
        }
        .pill-btn:hover { border-color: var(--text-disabled); }
        .pill-btn.selected[data-priority="high"] { background: rgba(248,81,73,0.1); color: var(--red); border-color: var(--red); }
        .pill-btn.selected[data-priority="medium"] { background: rgba(210,153,34,0.1); color: var(--amber); border-color: var(--amber); }
        .pill-btn.selected[data-priority="low"] { background: rgba(88,166,255,0.1); color: var(--blue); border-color: var(--blue); }

        .btn-deploy {
            width: 100%; margin-top: 16px; height: 44px; background: var(--bg-surface);
            border: 1px solid var(--border-neutral); border-radius: 8px;
            color: var(--text-muted); font-weight: 600; cursor: pointer; transition: all 200ms;
        }
        .btn-deploy.active { background: var(--blue-dark); color: #fff; border-color: var(--blue-dark); }
        .btn-deploy.active:hover { box-shadow: 0 8px 24px rgba(31,111,235,0.4); transform: translateY(-1px); }

        /* ─── MISSION QUEUE ────────────────────── */
        .filter-hud { display: flex; gap: 12px; margin: 24px 0 16px; flex-wrap: wrap; }
        .filter-chip {
            padding: 6px 16px; border-radius: 20px; font-size: 11px; font-weight: 700;
            background: var(--bg-surface); border: 1px solid var(--border-neutral);
            color: var(--text-disabled); cursor: pointer; transition: all 250ms cubic-bezier(0.16, 1, 0.3, 1);
        }
        .filter-chip:hover { border-color: var(--blue); color: var(--blue); transform: translateY(-1px); }
        .filter-chip.active { background: var(--blue-dark); color: #fff; border-color: var(--blue-dark); box-shadow: 0 4px 16px rgba(31,111,235,0.4); }

        /* ─── TASK CARDS: MOMENTUM CASCADE ─────── */
        .task-list { display: flex; flex-direction: column; gap: 10px; position: relative; overflow: hidden; }

        @keyframes cascadeIn {
            0%   { opacity: 0; transform: translateY(18px); }
            60%  { opacity: 1; transform: translateY(-3px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes successRipple {
            0%   { box-shadow: 0 0 0 0 rgba(63,185,80,0.5); background: rgba(63,185,80,0.12); }
            60%  { box-shadow: 0 0 0 12px rgba(63,185,80,0); }
            100% { box-shadow: none; background: rgba(13,17,23,0.8); }
        }

        .task-card {
            background: rgba(13, 17, 23, 0.8);
            border: 1px solid rgba(88, 166, 255, 0.08);
            border-left: 3px solid var(--border-neutral);
            border-radius: 10px; padding: 16px 20px; cursor: pointer;
            position: relative; overflow: hidden;
            opacity: 0; /* starts invisible, cascade adds animation */
            backdrop-filter: blur(10px);
            transition: border-color 250ms ease, box-shadow 250ms ease, transform 250ms ease;
        }
        .task-card.cascade-visible {
            animation: cascadeIn 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        .task-card.priority-high  { border-left-color: var(--red); }
        .task-card.priority-medium { border-left-color: var(--amber); }
        .task-card.priority-low   { border-left-color: var(--blue); }
        .task-card:hover {
            background: rgba(22, 27, 34, 0.95);
            border-color: rgba(88,166,255,0.3);
            box-shadow: 0 0 0 1px rgba(88,166,255,0.1), 0 8px 32px rgba(0,0,0,0.5);
            transform: translateY(-2px);
        }
        .task-card.completing {
            animation: successRipple 0.6s ease forwards;
            pointer-events: none;
        }

        /* ─── INTEGRITY / COMPLETION HORIZON ───── */
        #integrity-hud {
            margin-bottom: 20px; padding: 14px 16px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;
        }
        .integrity-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .integrity-bar-bg { height: 5px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }
        .integrity-bar-fill {
            height: 100%; width: 0%;
            background: linear-gradient(90deg, #3fb950, #58a6ff);
            transition: width 1.2s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 0 8px rgba(63,185,80,0.5);
        }
        #integrity-victory {
            margin-top: 8px; font-size: 11px; font-style: italic;
            color: var(--text-muted); min-height: 16px;
            transition: opacity 400ms;
        }

        .card-top { display: flex; align-items: center; gap: 12px; }
        .cb { 
            width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid var(--border-neutral);
            transition: all 200ms; flex-shrink: 0;
        }
        .task-card:hover .cb { border-color: var(--blue); }
        .cb.checked { background: var(--green); border-color: var(--green); position: relative; }
        .cb.checked::after { content: '✓'; color: #fff; position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800; }
        
        .task-title { flex: 1; font-weight: 500; font-size: 15px; color: var(--text-body); }
        .badge { font-size: 9px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
        .badge.high { color: var(--red); background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.2); }
        .badge.medium { color: var(--amber); background: rgba(210,153,34,0.1); border: 1px solid rgba(210,153,34,0.2); }
        .badge.low { color: var(--blue); background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.2); }
        .badge.tag { color: var(--ai-purple); background: rgba(163,113,247,0.1); border: 1px solid rgba(163,113,247,0.2); }

        /* ─── MODAL EXPANSION ───────────────────── */
        #modal-overlay {
            position: fixed; inset: 0; background: rgba(6, 10, 15, 0.4);
            backdrop-filter: blur(0px); z-index: 10000; display: flex;
            align-items: center; justify-content: center; opacity: 0;
            pointer-events: none; transition: all 500ms cubic-bezier(0.16, 1, 0.3, 1);
        }
        #modal-overlay.show { opacity: 1; pointer-events: auto; backdrop-filter: blur(12px); }
        
        .modal-card {
            background: rgba(13, 17, 23, 0.85); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 24px; padding: 48px; width: 640px; max-width: 90%;
            position: relative; box-shadow: 0 64px 128px rgba(0,0,0,0.8);
            transform: scale(0.9) translateY(20px); transition: all 600ms cubic-bezier(0.16, 1, 0.3, 1);
            clip-path: circle(0% at var(--origin-x, 50%) var(--origin-y, 50%));
        }
        #modal-overlay.show .modal-card {
            transform: scale(1) translateY(0);
            clip-path: circle(150% at var(--origin-x, 50%) var(--origin-y, 50%));
        }
        .modal-close { position: absolute; top: 24px; right: 24px; font-size: 24px; cursor: pointer; color: var(--text-disabled); }

        /* ─ ADVISOR ─ */
        .advisor-badge { display: flex; align-items: center; gap: 8px; font-size: 10px; font-weight: 700; letter-spacing: 2px; color: var(--blue); margin-bottom: 24px; }
        .pulse-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--blue); animation: pulseDot 2s infinite; }
        @keyframes pulseDot { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
        .advisor-msg { font-size: 13px; font-style: italic; color: var(--text-muted); border-left: 1px solid var(--border-neutral); padding-left: 16px; min-height: 60px; line-height: 1.8; }

        /* ─── VIEW MANAGEMENT ────────────────────── */
        .view-content {
            transition: opacity 400ms ease, transform 400ms cubic-bezier(0.16, 1, 0.3, 1);
            opacity: 1; transform: translateY(0);
        }
        .view-content.hidden {
            display: none; opacity: 0; transform: translateY(10px);
        }

        /* ─── TOAST HUD ────────────────────────── */
        #toast {
            position: fixed; top: 32px; right: 32px; z-index: 20000;
            background: var(--bg-surface); border: 1px solid var(--border-neutral);
            border-left: 2px solid var(--blue); padding: 12px 24px; border-radius: 8px;
            font-size: 13px; font-weight: 600; color: var(--text-hero);
            box-shadow: 0 16px 48px rgba(0,0,0,0.6);
            opacity: 0; transform: translateY(-20px); pointer-events: none;
            transition: all 400ms cubic-bezier(0.16, 1, 0.3, 1);
        }
        #toast.show { opacity: 1; transform: translateY(0); }

        /* ─── AMBIENT PULSES ─────────────────── */
        @keyframes glowPulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
        @keyframes chipPulse {
            0%, 100% { box-shadow: 0 4px 16px rgba(31,111,235,0.2); }
            50%  { box-shadow: 0 4px 24px rgba(31,111,235,0.5); }
        }
        .filter-chip.active { animation: chipPulse 2.5s ease infinite; }
    </style>
</head>
<body class="state-idle">
    <div id="threejs-canvas" style="position: fixed; inset: 0; z-index: -2; pointer-events: none; opacity: 1;"></div>
    <div id="bg-parallax"></div>
    <div id="bg-grid"></div>
    <div id="hud-scanlines"></div>
    <div id="toast">Protocol Offline</div>

    <div id="modal-overlay">
        <div class="modal-card" id="mission-brief-modal">
            <div class="modal-close" id="btn-modal-close">×</div>
            <div id="modal-content"></div>
        </div>
    </div>

    <!-- SIDEBAR -->
    <aside class="col-sidebar">
        <div class="logo-area">
            <span class="logo-wave">✦</span>
            <span class="logo-task">task</span><span class="logo-flow">flow</span>
        </div>
        <nav>
            <div class="nav-section-label">PROTOCOL</div>
            <div class="nav-item active" id="nav-dashboard"><span class="nav-icon">⊞</span> Execution</div>
            <div class="nav-item" id="nav-tasks"><span class="nav-icon">✓</span> Missions</div>
            <div class="nav-item" id="nav-focus"><span class="nav-icon">⏱</span> Deep Work</div>
            <div class="nav-item" id="nav-ai"><span class="nav-icon">✦</span> Intelligence</div>

            <div class="nav-section-label">SYSTEM</div>
            <div class="nav-item" id="nav-stats"><span class="nav-icon">📊</span> Analytics</div>
        </nav>
        <div style="margin-top:auto; padding-top:24px; border-top:1px solid var(--border-subtle); display:flex; align-items:center; gap:12px;">
            <div style="width:32px; height:32px; background:var(--bg-surface); border-radius:50%; display:flex; align-items:center; justify-content:center;">👨‍💻</div>
            <div style="font-size:12px; font-weight:600; color:var(--text-hero);">OPERATOR M</div>
        </div>
    </aside>

    <!-- OPERATIONS CENTER -->
    <main class="col-main">
        <!-- VIEW: DASHBOARD (OPERATIONS) -->
        <div id="view-dashboard" class="view-content">
            <div class="ai-zone">
                <div class="ai-input-wrap">
                    <span style="color:var(--blue); font-size:20px;">✦</span>
                    <input type="text" id="ai-input" class="ai-input" placeholder="Initiate mission generation protocol...">
                    <button class="btn-execute" id="btn-execute">EXECUTE</button>
                </div>
            </div>

            <div class="mission-panel">
                <div class="section-label">MISSION DEPLOYMENT</div>
                <div class="flex-row">
                    <div class="mission-field">
                        <label class="section-label" style="font-size:9px;">OBJECTIVE</label>
                        <input type="text" id="mission-title" class="input-system" placeholder="Enter tactical objective...">
                    </div>
                </div>
                <div class="flex-row" style="margin-top:20px;">
                    <div class="mission-field">
                        <label class="section-label" style="font-size:9px;">PRIORITY PROTOCOL</label>
                        <div class="priority-grid">
                            <button class="pill-btn" data-priority="low">LOW</button>
                            <button class="pill-btn selected" data-priority="medium">MEDIUM</button>
                            <button class="pill-btn" data-priority="high">HIGH</button>
                        </div>
                    </div>
                </div>
                <button class="btn-deploy" id="btn-deploy" disabled>DEPLOY MISSION</button>
            </div>
        </div>

        <!-- VIEW: MISSIONS (QUEUE) -->
        <div id="view-tasks" class="view-content hidden">
            <div style="margin-top:20px;">
                <div id="integrity-hud">
                    <div class="integrity-label-row">
                        <div class="section-label" style="font-size:9px; letter-spacing:2px;">COMPLETION HORIZON</div>
                        <div style="font-size:10px; color:var(--green);" id="integrity-percent">0%</div>
                    </div>
                    <div class="integrity-bar-bg"><div id="integrity-fill" class="integrity-bar-fill"></div></div>
                    <div id="integrity-victory"></div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div class="section-label">MISSION QUEUE</div>
                    <div style="font-size:11px; color:var(--text-disabled);" id="header-task-count">0 ACTIVE</div>
                </div>
                
                <div class="mission-panel" style="padding:16px; margin-bottom:16px; border-radius:8px;">
                    <div class="section-label" style="font-size:9px; margin-bottom:12px;">PRIORITY SIGNALS</div>
                    <div class="filter-hud" style="margin:0;">
                        <div class="filter-chip active" onclick="filterTasks('all', this)">ALL</div>
                        <div class="filter-chip" onclick="filterTasks('high', this)">HIGH-THREAT</div>
                        <div class="filter-chip" onclick="filterTasks('medium', this)">STABLE</div>
                        <div class="filter-chip" onclick="filterTasks('low', this)">ROUTINE</div>
                    </div>

                    <div class="section-label" style="font-size:9px; margin:20px 0 12px;">SIGNAL DISCOVERY (TAGS)</div>
                    <div id="tag-signal-discovery" class="filter-hud" style="flex-wrap:wrap; margin:0; gap:8px;">
                        <!-- Dynamic Signals -->
                    </div>
                </div>

                <div id="task-list-container" class="task-list">
                    <div class="filament-line"></div>
                    <!-- Quantum Content -->
                </div>
            </div>
        </div>
    </main>

    <!-- ADVISOR HUD -->
    <aside class="col-advisor">
        <div class="advisor-badge"><div class="pulse-dot"></div> AI ADVISOR ACTIVE</div>
        <div style="background:rgba(255,255,255,0.02); padding:24px; border-radius:16px; border:1px solid var(--border-neutral);">
            <div class="advisor-msg" id="advisor-msg">
                System standing by. All protocols reporting nominal. Initiate deployment to begin intelligence analysis.
            </div>
        </div>

        <div style="margin-top:40px;">
            <div class="section-label">EXECUTION XP</div>
            <div style="height:6px; background:var(--bg-surface); border-radius:3px; overflow:hidden; margin-bottom:8px;">
                <div id="xp-fill" style="width:40%; height:100%; background:var(--blue); transition:width 1s ease-out;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:var(--text-disabled);">
                <span>RANK: 01</span>
                <span id="xp-text">40 / 100 XP</span>
            </div>
        </div>
    </aside>

    <script>
    let allTasks = [], currentFilter = 'all', currentActiveTaskId = null, selectedPriority = 'medium';

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
        setTimeout(() => t.classList.remove('show'), 3000);
    }

    // ── NAVIGATION PROTOCOL (VIEW SWITCHING) ─────────────────────────────
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view-content');

    function switchView(viewId) {
        views.forEach(v => v.classList.add('hidden'));
        const targetView = document.getElementById(`view-${viewId}`);
        if (targetView) targetView.classList.remove('hidden');

        navItems.forEach(item => {
            item.classList.toggle('active', item.id === `nav-${viewId}`);
        });

        if (typeof startSimulation === 'function') {
            if (viewId === 'dashboard') startSimulation('execution');
            if (viewId === 'tasks') startSimulation('missions');
        }

        if (viewId === 'tasks') {
            loadTasks();
            setSystemState('idle');
        } else if (viewId === 'dashboard') {
            setSystemState('idle');
        }
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (item.id === 'nav-dashboard') switchView('dashboard');
            else if (item.id === 'nav-tasks') switchView('tasks');
            else if (item.id === 'nav-focus') {
                switchView('dashboard');
                setSystemState('deep-work');
                if (typeof startSimulation === 'function') startSimulation('focus');
            } else if (item.id === 'nav-ai') {
                showToast("Synthesizing Intelligence... (Integration pending)", "var(--ai-purple)");
            } else if (item.id === 'nav-stats') {
                showToast("Accessing Analytics Core...", "var(--blue)");
                loadStats();
            }
        });
    });

    // ── MISSION CONTROLS ──────────────────────────────────────────────────
    const missionTitle = document.getElementById('mission-title');
    const btnDeploy = document.getElementById('btn-deploy');

    if (missionTitle) {
        missionTitle.addEventListener('input', () => {
            btnDeploy.disabled = !missionTitle.value.trim();
            btnDeploy.classList.toggle('active', !!missionTitle.value.trim());
        });
    }

    document.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedPriority = btn.dataset.priority;
        });
    });

    if (btnDeploy) {
        btnDeploy.addEventListener('click', async () => {
            const title = missionTitle.value.trim();
            if (!title) return;
            setSystemState('thinking');
            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title, priority: selectedPriority, tags: [] })
            });
            if (res.ok) {
                missionTitle.value = '';
                btnDeploy.disabled = true;
                btnDeploy.classList.remove('active');
                showToast('Mission deployed.', 'var(--green)');
                await loadTasks();
                setSystemState('idle');
            }
        });
    }

    // ── MOMENTUM CASCADE ENGINE ───────────────────────────────────────────
    async function loadTasks() {
        const [tasksRes, statsRes] = await Promise.all([
            fetch('/api/tasks'),
            fetch('/api/stats')
        ]);
        const tasksData = await tasksRes.json();
        const statsData = await statsRes.json();
        allTasks = tasksData.tasks || [];
        updateIntegrityMeter(statsData);
        renderTaskList();
    }

    function updateIntegrityMeter(stats) {
        const total = stats.total || 0;
        const done  = stats.completed || 0;
        const pct   = stats.completion_rate || 0;

        const fill    = document.getElementById('integrity-fill');
        const pctEl   = document.getElementById('integrity-percent');
        const victory = document.getElementById('integrity-victory');

        if (fill)  fill.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${Math.round(pct)}%  (${done}/${total})`;
        if (victory) {
            let msg = '';
            if (total === 0)     msg = 'Fresh start. Add your first win.';
            else if (done === 0) msg = 'Momentum building. Pick one.';
            else if (pct < 50)   msg = 'Flow state activated.';
            else if (pct < 100)  msg = "Mastery mode. Unstoppable.";

            else                 msg = 'All tasks cleared! Celebrate.';
            victory.style.opacity = '0';
            setTimeout(() => { victory.textContent = msg; victory.style.opacity = '1'; }, 300);
        }
    }

    function renderTaskList(tagFilter = null) {
        const container = document.getElementById('task-list-container');
        if (!container) return;

        const filtered = allTasks.filter(t => {
            const p = (t.priority || 'medium').toLowerCase();
            if (tagFilter) return (t.tags || []).includes(tagFilter);
            if (currentFilter === 'all')    return true;
            if (currentFilter === 'high')   return p === 'high';
            if (currentFilter === 'medium') return p === 'medium';
            if (currentFilter === 'low')    return p === 'low';
            return true;
        });

        renderTagSignals();
        document.getElementById('header-task-count').textContent = `${filtered.length} ACTIVE`;

        container.innerHTML = filtered.map((t, i) => `
            <div class="task-card priority-${(t.priority||'medium').toLowerCase()}" data-id="${t.id}"
                 onclick="openModal(${t.id}, this)">
                <div class="card-top">
                    <div class="cb" onclick="event.stopPropagation(); completeTask(${t.id}, this)"></div>
                    <div class="task-title">${t.title}</div>
                    <span class="badge ${(t.priority||'medium').toLowerCase()}">${(t.priority||'medium').toUpperCase()}</span>
                    ${(t.tags||[]).map(tg =>
                        `<span class="badge tag" onclick="event.stopPropagation(); filterByTag('${tg}')">#${tg}</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');

        // GENTLE CASCADE: stagger each card sliding up
        container.querySelectorAll('.task-card').forEach((card, i) => {
            card.style.animationDelay = `${i * 80}ms`;
            requestAnimationFrame(() => {
                requestAnimationFrame(() => card.classList.add('cascade-visible'));
            });
        });
    }

    function filterTasks(crit, element) {
        currentFilter = crit;
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        if (element) element.classList.add('active');
        renderTaskList();
    }

    function filterByTag(tag) {
        currentFilter = 'tagged';
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        renderTaskList(tag);
    }

    function renderTagSignals() {
        const discovery = document.getElementById('tag-signal-discovery');
        if (!discovery) return;
        const uniqueTags = [...new Set(allTasks.flatMap(t => t.tags || []))];
        if (uniqueTags.length === 0) {
            discovery.innerHTML = `<div style="font-size:10px; color:var(--text-disabled); font-style:italic;">No signals discovered.</div>`;
            return;
        }
        discovery.innerHTML = uniqueTags.map(tg =>
            `<div class="filter-chip" onclick="filterByTag('${tg}', this)">#${tg.toUpperCase()}</div>`
        ).join('');
    }

    // ── MODAL SYSTEM ──────────────────────────────────────────────────────
    const modal = document.getElementById('modal-overlay');
    function openModal(id, el) {
        const task = allTasks.find(t => t.id === id);
        if (!task) return;
        const r = el.getBoundingClientRect();
        const mc = document.getElementById('mission-brief-modal');
        mc.style.setProperty('--origin-x', `${r.left + r.width/2}px`);
        mc.style.setProperty('--origin-y', `${r.top + r.height/2}px`);
        document.getElementById('modal-content').innerHTML = `
            <div class="section-label" style="margin-bottom:8px;">MISSION BRIEFING</div>
            <h2 style="font-size:28px; font-weight:700; color:var(--text-hero); margin-bottom:20px;">${task.title}</h2>
            <div style="display:flex; gap:12px; margin-bottom:32px;">
                <span class="badge ${(task.priority||'medium').toLowerCase()}">${(task.priority||'MEDIUM').toUpperCase()} PROTOCOL</span>
                ${(task.tags||[]).map(tg => `<span class="badge tag">${tg}</span>`).join('')}
            </div>
            <div style="background:rgba(255,255,255,0.02); padding:32px; border-radius:16px; border:1px solid var(--border-neutral); text-align:center;">
                <div style="font-size:48px; font-family:var(--font-mono); margin-bottom:20px; color:var(--text-hero);">25:00</div>
                <button class="btn-execute" style="width:100%;" onclick="startFocus()">START FOCUS PROTOCOL</button>
            </div>
        `;
        modal.classList.add('show');
    }
    function closeModal() { modal.classList.remove('show'); setSystemState('idle'); }
    document.getElementById('btn-modal-close').onclick = closeModal;
    function startFocus() { closeModal(); setSystemState('deep-work'); }

    // SUCCESS RIPPLE on completion
    window.completeTask = async (id, cbEl) => {
        cbEl.classList.add('checked');
        const card = cbEl.closest('.task-card');
        if (card) card.classList.add('completing');
        await fetch(`/api/tasks/${id}/complete`, {method: 'POST'});
        setTimeout(loadTasks, 750);
    };

    window.onload = () => {
        initThreeJS();
        loadTasks();
    };

    // ── 3D PARTICLE SIMULATION (THREE.JS) ─────────────────────────────
    let scene, camera, renderer;
    let currentParticles = null;
    let animationId = null;
    let activeSimType = null;
    let clock = null;

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
        const particleCount = 200;
        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
        }
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const material = new THREE.PointsMaterial({
            color: 0x3b82f6, size: 0.05, transparent: true, opacity: 0.8
        });
        return new THREE.Points(geometry, material);
    }

    // Concept 2: "Deep Work Embers" (Missions tab)
    function createEmbers() {
        const canvas = document.createElement('canvas');
        canvas.width = 16; canvas.height = 16;
        const ctx = canvas.getContext('2d');
        ctx.beginPath(); ctx.arc(8, 8, 8, 0, Math.PI * 2);
        ctx.fillStyle = 'white'; ctx.fill();
        const sprite = new THREE.CanvasTexture(canvas);

        const count = 100;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            pos[i*3] = (Math.random() - 0.5) * 15;
            pos[i*3+1] = (Math.random() - 0.5) * 15;
            pos[i*3+2] = (Math.random() - 0.5) * 15;
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({
            size: 0.15, map: sprite, transparent: true, opacity: 0.4,
            color: 0xeab308, blending: THREE.AdditiveBlending, depthWrite: false
        });
        return new THREE.Points(geo, mat);
    }

    // Concept 3: "The Flow State" (Focus / Deep Work tab)
    function createFlowState() {
        const count = 1000;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        const velocities = new Float32Array(count);
        for (let i = 0; i < count; i++) {
            pos[i*3] = (Math.random() - 0.5) * 20;
            pos[i*3+1] = (Math.random() - 0.5) * 20;
            pos[i*3+2] = (Math.random() - 0.5) * 20;
            velocities[i] = 0.01 + Math.random() * 0.03;
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({
            size: 0.03, color: 0xa855f7, transparent: true, opacity: 0.6
        });
        const points = new THREE.Points(geo, mat);
        points.userData.velocities = velocities;
        return points;
    }

    function animateSimulation(type) {
        if (activeSimType !== type) return;
        animationId = requestAnimationFrame(() => animateSimulation(type));
        if (!currentParticles) return;

        if (type === 'execution') {
            currentParticles.rotation.y += 0.001;
            currentParticles.rotation.x += 0.0005;
        } else if (type === 'missions') {
            const pos = currentParticles.geometry.attributes.position.array;
            for (let i = 0; i < 100; i++) {
                pos[i*3 + 1] += 0.005;
                pos[i*3] += Math.sin(Date.now() * 0.001 + i) * 0.002;
                if (pos[i*3+1] > 5) pos[i*3+1] = -5;
            }
            currentParticles.geometry.attributes.position.needsUpdate = true;
        } else if (type === 'focus') {
            const pos = currentParticles.geometry.attributes.position.array;
            const velocities = currentParticles.userData.velocities;
            for (let i = 0; i < 1000; i++) {
                pos[i*3 + 2] += velocities[i];
                if (pos[i*3 + 2] > 10) pos[i*3 + 2] = -10;
            }
            currentParticles.geometry.attributes.position.needsUpdate = true;
        }
        renderer.render(scene, camera);
    }



    </script>
</body>
</html>
"""
