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
        body.state-deep-work { background-color: #05070A; }
        body.state-deep-work .col-sidebar { opacity: 0.3; pointer-events: auto; }
        body.state-deep-work .col-advisor { opacity: 0.3; pointer-events: auto; }
        body.state-deep-work .col-main { filter: blur(8px); opacity: 0.2; pointer-events: none; }
        
        /* Focus Overlay */
        .focus-overlay {
            position: fixed; inset: 0; z-index: 50; display: flex; flex-direction: column;
            align-items: center; justify-content: center; pointer-events: none; opacity: 0;
            transition: opacity 0.5s ease;
        }
        .focus-overlay.active { pointer-events: auto; opacity: 1; }
        .focus-overlay-content {
            background: rgba(22, 27, 34, 0.4); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            padding: 48px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.05); text-align: center;
            display: flex; flex-direction: column; gap: 24px; min-width: 400px;
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
        .task-card::after {
            content: '▶ START FOCUS'; position: absolute; right: 20px; top: 50%; transform: translateY(-50%);
            font-size: 10px; font-weight: 700; color: var(--blue); opacity: 0; transition: opacity 0.2s ease; pointer-events: none;
            text-shadow: 0 0 10px rgba(88,166,255,0.4);
        }
        .task-card:hover {
            background: rgba(22, 27, 34, 0.95);
            border-color: rgba(88,166,255,0.3);
            box-shadow: 0 0 0 1px rgba(88,166,255,0.1), 0 8px 32px rgba(0,0,0,0.5);
            transform: translateY(-2px);
        }
        .task-card:hover::after { opacity: 1; }
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

        /* ─── TIMELINE VIEW CSS ────────────────── */
        .timeline-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 12px; margin-top: 24px; }
        .timeline-day {
            background: rgba(22, 27, 34, 0.4); border: 1px solid var(--border-neutral);
            border-radius: 12px; min-height: 400px; display: flex; flex-direction: column;
        }
        .timeline-day-header {
            text-align: center; padding: 12px; font-size: 11px; font-weight: 700;
            color: var(--text-disabled); border-bottom: 1px solid var(--border-neutral);
            letter-spacing: 1px;
        }
        .timeline-dropzone { flex-grow: 1; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
        .timeline-dropzone.drag-over { background: rgba(88,166,255,0.05); border-radius: 0 0 12px 12px; }

        .timeline-task {
            background: rgba(13, 17, 23, 0.9); border: 1px solid rgba(88,166,255,0.1);
            border-left: 3px solid var(--blue); padding: 10px; border-radius: 8px;
            font-size: 11px; color: var(--text-body); cursor: grab;
        }
        .timeline-task.priority-high { border-left-color: var(--red); }
        .timeline-task.priority-medium { border-left-color: var(--amber); }
        .timeline-task.dragging { opacity: 0.5; }

        .unscheduled-pool {
            margin-top: 24px; padding: 24px; background: rgba(22, 27, 34, 0.4);
            border: 1px solid var(--border-subtle); border-radius: 16px; min-height: 120px;
            display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-start; align-content: flex-start;
        }
        .unscheduled-pool.drag-over { background: rgba(88,166,255,0.05); border-color: var(--blue); }

        
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

    <div id="focus-overlay" class="focus-overlay"></div>

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
            <div class="nav-item active" id="nav-dashboard"><span class="nav-icon">⊞</span> Control Center</div>
            <div class="nav-item" id="nav-tasks"><span class="nav-icon">✓</span> Missions</div>
            <div class="nav-item" id="nav-timeline"><span class="nav-icon">⏱</span> Timeline</div>
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
        <!-- VIEW: DASHBOARD (CONTROL CENTER) -->
        <div id="view-dashboard" class="view-content">
            <div style="max-width: 800px; margin: 0 auto; width: 100%;">
                
                <!-- 1. AI INPUT -->
                <div class="ai-zone" style="margin-top: 24px; text-align: center; border: 1px solid rgba(163, 113, 247, 0.3); box-shadow: 0 0 40px rgba(163, 113, 247, 0.1);">
                    <div style="font-size: 12px; font-weight: 700; color: var(--ai-purple); margin-bottom: 20px; letter-spacing: 2px;">INTELLIGENCE PROTOCOL</div>
                    <div class="ai-input-wrap" style="background: rgba(0,0,0,0.2); justify-content: center; padding: 4px 16px;">
                        <span style="color:var(--ai-purple); font-size:20px;">✦</span>
                        <input type="text" id="ai-input" class="ai-input" placeholder="What's the next objective?" style="text-align: center; font-size: 16px; padding: 12px;">
                        <button class="btn-execute" id="btn-execute" style="background: rgba(163, 113, 247, 0.1); color: var(--ai-purple); border-color: rgba(163, 113, 247, 0.3);">SYNTHESIZE</button>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 32px;">
                    
                    <!-- 2. UPCOMING MISSIONS -->
                    <div class="mission-panel" style="padding: 24px;">
                        <div class="section-label">UPCOMING MISSIONS</div>
                        <div id="cc-upcoming" style="min-height: 120px; color: var(--text-muted); font-size: 12px; display: flex; flex-direction: column; gap: 8px; margin-top: 16px;">
                            <!-- Filled by JS -->
                        </div>
                    </div>

                    <!-- 3. PRIORITY ALERTS -->
                    <div class="mission-panel" style="padding: 24px; border-color: rgba(248, 81, 73, 0.2); box-shadow: inset 0 0 20px rgba(248, 81, 73, 0.05);">
                        <div class="section-label" style="color: var(--red);">PRIORITY ALERTS</div>
                        <div id="cc-alerts" style="min-height: 120px; color: var(--red); font-size: 12px; display: flex; flex-direction: column; gap: 8px; margin-top: 16px;">
                            <!-- Filled by JS -->
                        </div>
                    </div>

                    <!-- 4. PERFORMANCE SNAPSHOT -->
                    <div class="mission-panel" style="padding: 24px;">
                        <div class="section-label">PERFORMANCE SNAPSHOT</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 24px;">
                            <div>
                                <div style="font-size: 10px; color: var(--text-disabled); margin-bottom: 8px;">COMPLETION</div>
                                <div id="cc-completion-pct" style="font-size: 28px; font-weight: 700; color: var(--green); font-family: var(--font-mono); line-height: 1;">0%</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 10px; color: var(--text-disabled); margin-bottom: 8px;">ACTIVE</div>
                                <div id="cc-active-count" style="font-size: 20px; font-weight: 700; color: var(--text-hero); font-family: var(--font-mono); line-height: 1;">0</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 10px; color: var(--text-disabled); margin-bottom: 8px;">FOCUS HRS</div>
                                <div style="font-size: 20px; font-weight: 700; color: var(--blue); font-family: var(--font-mono); line-height: 1;">0</div>
                            </div>
                        </div>
                    </div>

                    <!-- 5. AI INSIGHT PANEL -->
                    <div class="mission-panel" style="padding: 24px; border-color: rgba(163, 113, 247, 0.2);">
                        <div class="section-label" style="color: var(--ai-purple);">INTELLIGENCE INSIGHT</div>
                        <div style="margin-top: 24px; font-size: 13px; color: var(--text-body); line-height: 1.6;">
                            <span style="color:var(--ai-purple);">✦</span> <span id="cc-insight">System stable. High-priority execution recommended to maintain optimal momentum.</span>
                        </div>
                    </div>

                </div>
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
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div class="section-label" style="margin:0;">MISSION QUEUE</div>
                        <div style="font-size:11px; color:var(--text-disabled);" id="header-task-count">0 ACTIVE</div>
                    </div>
                    <button class="btn-execute" onclick="toggleCreateMission()" style="padding: 8px 16px; font-size: 11px;">+ CREATE MISSION</button>
                </div>

                <div id="create-mission-panel" class="mission-panel hidden" style="margin-bottom:24px;">
                    <div class="section-label">NEW MISSION DEPLOYMENT</div>
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
                    <div class="flex-row" style="margin-top:20px;">
                        <div class="mission-field">
                            <label class="section-label" style="font-size:9px;">TAG SIGNALS (COMMA SEPARATED)</label>
                            <input type="text" id="mission-tags" class="input-system" placeholder="e.g. work, personal, critical">
                        </div>
                    </div>
                    <div style="display:flex; gap:12px; margin-top:20px;">
                        <button class="btn-deploy" id="btn-deploy" disabled style="margin:0;">DEPLOY</button>
                        <button class="btn-execute" onclick="toggleCreateMission()" style="margin:0; background:transparent; border-color:var(--border-neutral); color:var(--text-muted); width:auto; padding:0 24px;">CANCEL</button>
                    </div>
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

        <!-- VIEW: TIMELINE -->
        <div id="view-timeline" class="view-content hidden">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="section-label" style="margin:0;">TIMELINE PROTOCOL</div>
                <div style="font-size:12px; color:var(--text-disabled); font-weight:600;" id="timeline-week-label">THIS WEEK</div>
            </div>
            
            <div class="timeline-grid" id="timeline-grid">
                <!-- Days injected by JS -->
            </div>

            <div class="section-label" style="margin-top:32px;">UNSCHEDULED MISSIONS</div>
            <div class="unscheduled-pool" id="unscheduled-dropzone" data-day="unscheduled" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                <!-- Tasks injected by JS -->
            </div>
        </div>

        <!-- VIEW: INTELLIGENCE -->
        <div id="view-ai" class="view-content hidden">
            <div style="max-width: 800px; margin: 0 auto; width: 100%;">
                <div class="section-label" style="text-align:center; margin-bottom: 24px;">SYSTEM INTELLIGENCE</div>
                
                <div style="display:grid; grid-template-columns: 2fr 1fr; gap:24px;">
                    <!-- System Messages -->
                    <div class="mission-panel" style="padding:32px;">
                        <div class="section-label" style="color:var(--ai-purple);">SYSTEM LOG</div>
                        <div id="intel-logs" style="margin-top:20px; display:flex; flex-direction:column; gap:16px;">
                            <div style="padding:12px; border-left:2px solid var(--green); background:rgba(255,255,255,0.02); font-size:12px;">Intelligence module booting...</div>
                        </div>
                    </div>
                    
                    <!-- Suggestions -->
                    <div class="mission-panel" style="padding:32px; background:rgba(163, 113, 247, 0.05); border-color:rgba(163, 113, 247, 0.2);">
                        <div class="section-label" style="color:var(--ai-purple);">AI ADVISORY</div>
                        <div id="intel-advisory" style="margin-top:20px; font-size:13px; line-height:1.6; color:var(--text-body);">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW: ANALYTICS -->
        <div id="view-stats" class="view-content hidden">
            <div style="max-width: 900px; margin: 0 auto; width: 100%;">
                <div class="section-label" style="text-align:center; margin-bottom: 24px;">SYSTEM ANALYTICS</div>
                
                <!-- Metrics Grid -->
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-bottom:24px;">
                    <div class="mission-panel" style="padding:24px; text-align:center;">
                        <div style="font-size:10px; color:var(--text-disabled); margin-bottom:8px;">COMPLETION RATE</div>
                        <div id="stat-completion" style="font-size:28px; font-weight:700; color:var(--green); font-family:var(--font-mono);">0%</div>
                    </div>
                    <div class="mission-panel" style="padding:24px; text-align:center;">
                        <div style="font-size:10px; color:var(--text-disabled); margin-bottom:8px;">FOCUS TIME</div>
                        <div id="stat-focus" style="font-size:28px; font-weight:700; color:var(--blue); font-family:var(--font-mono);">0h</div>
                    </div>
                    <div class="mission-panel" style="padding:24px; text-align:center;">
                        <div style="font-size:10px; color:var(--text-disabled); margin-bottom:8px;">HIGH PRIORITIES</div>
                        <div id="stat-high-pct" style="font-size:28px; font-weight:700; color:var(--red); font-family:var(--font-mono);">0%</div>
                    </div>
                    <div class="mission-panel" style="padding:24px; text-align:center;">
                        <div style="font-size:10px; color:var(--text-disabled); margin-bottom:8px;">CONSISTENCY</div>
                        <div id="stat-streak" style="font-size:28px; font-weight:700; color:var(--amber); font-family:var(--font-mono);">0 Days</div>
                    </div>
                </div>

                <!-- Graph -->
                <div class="mission-panel" style="padding:32px;">
                    <div class="section-label">7-DAY TRAJECTORY</div>
                    <div id="stat-chart" style="height:200px; margin-top:24px; display:flex; align-items:flex-end; gap:12px; padding-bottom:12px; border-bottom:1px solid var(--border-neutral);">
                    </div>
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
            else if (viewId === 'tasks') startSimulation('missions');
            else if (viewId === 'timeline') startSimulation('focus');
        }

        if (viewId === 'tasks') {
            loadTasks();
            setSystemState('idle');
        } else if (viewId === 'dashboard' || viewId === 'timeline') {
            setSystemState('idle');
        }
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            if (item.id === 'nav-dashboard') switchView('dashboard');
            else if (item.id === 'nav-tasks') switchView('tasks');
            else if (item.id === 'nav-timeline') switchView('timeline');
            else if (item.id === 'nav-ai') {
                switchView('ai');
                loadStats();
            } else if (item.id === 'nav-stats') {
                switchView('stats');
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

    function toggleCreateMission() {
        const p = document.getElementById('create-mission-panel');
        if (p.classList.contains('hidden')) {
            p.classList.remove('hidden');
        } else {
            p.classList.add('hidden');
        }
    }

    if (btnDeploy) {
        btnDeploy.addEventListener('click', async () => {
            const title = missionTitle.value.trim();
            const tagStr = document.getElementById('mission-tags') ? document.getElementById('mission-tags').value : "";
            const tags = tagStr.split(',').map(s=>s.trim()).filter(s=>s.length > 0);
            if (!title) return;
            setSystemState('thinking');
            const res = await fetch('/api/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ title, priority: selectedPriority, tags })
            });
            if (res.ok) {
                missionTitle.value = '';
                if(document.getElementById('mission-tags')) document.getElementById('mission-tags').value = '';
                btnDeploy.disabled = true;
                btnDeploy.classList.remove('active');
                showToast('Mission deployed.', 'var(--green)');
                toggleCreateMission();
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
        updateControlCenter();
        renderTaskList();
        renderTimeline();
    }

    function updateControlCenter() {
        const activeTasks = allTasks;
        const highPriority = activeTasks.filter(t => (t.priority||'medium').toLowerCase() === 'high');
        const others = activeTasks.filter(t => (t.priority||'medium').toLowerCase() !== 'high');

        const alertsContainer = document.getElementById('cc-alerts');
        if (alertsContainer) {
            alertsContainer.innerHTML = highPriority.length > 0
                ? highPriority.slice(0,3).map(t => `<div style="padding:12px; background:rgba(248,81,73,0.05); border-radius:8px; border-left:3px solid var(--red);">${t.title}</div>`).join('')
                : '<div style="opacity:0.5;">No critical alerts.</div>';
        }

        const upcomingContainer = document.getElementById('cc-upcoming');
        if (upcomingContainer) {
            upcomingContainer.innerHTML = others.length > 0
                ? others.slice(0,4).map(t => `<div style="padding:12px; background:rgba(255,255,255,0.02); border-radius:8px; border-left:3px solid var(--${t.priority === 'low' ? 'blue' : 'amber'});">${t.title}</div>`).join('')
                : '<div style="opacity:0.5;">Queue transparent.</div>';
        }

        const insight = document.getElementById('cc-insight');
        if (insight && highPriority.length > 0) {
            insight.textContent = `CRITICAL: ${highPriority.length} high-threat missions require immediate execution.`;
            insight.style.color = "var(--red)";
            insight.previousElementSibling.style.color = "var(--red)";
        } else if (insight) {
            insight.textContent = "System stable. High-priority execution recommended to maintain optimal momentum.";
            insight.style.color = "var(--text-body)";
            insight.previousElementSibling.style.color = "var(--ai-purple)";
        }
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
        
        const ccPct = document.getElementById('cc-completion-pct');
        const ccActive = document.getElementById('cc-active-count');
        if (ccPct) ccPct.textContent = `${Math.round(pct)}%`;
        if (ccActive) ccActive.textContent = total - done;

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

        // 1. Record current positions (First)
        const oldCards = Array.from(container.querySelectorAll('.task-card'));
        const rects = new Map();
        oldCards.forEach(card => rects.set(card.dataset.id, card.getBoundingClientRect()));

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

        // 2. Render new DOM
        container.innerHTML = filtered.map((t) => `
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

        // 3. FLIP Playback
        const newCards = Array.from(container.querySelectorAll('.task-card'));
        newCards.forEach((card, i) => {
            const id = card.dataset.id;
            const oldRect = rects.get(id);
            if (oldRect) {
                // Existing item -> Invert and Play
                const newRect = card.getBoundingClientRect();
                const dy = oldRect.top - newRect.top;
                card.style.transform = `translateY(${dy}px)`;
                card.style.transition = 'none';
                card.classList.add('cascade-visible'); // Ensure opacity is 1

                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        card.style.transition = 'transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)';
                        card.style.transform = 'translateY(0)';
                    });
                });
            } else {
                // New item -> standard cascade
                card.style.animationDelay = `${(i % 10) * 50}ms`;
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => card.classList.add('cascade-visible'));
                });
            }
        });

        // Cleanup inline transitions so hover effect still works
        setTimeout(() => {
            container.querySelectorAll('.task-card').forEach(card => {
                if (card.style.transition) card.style.transition = '';
            });
        }, 450);
    }

    function filterTasks(crit, element) {
        currentFilter = crit;
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        if (element) element.classList.add('active');
        renderTaskList();
    }

    // ── ANALYTICS & INTELLIGENCE SYSTEM ────────────────────────────────────
    async function loadStats() {
        try {
            const [statsRes, tasksRes] = await Promise.all([
                fetch('/api/stats'),
                fetch('/api/tasks')
            ]);
            const stats = await statsRes.json();
            const tasksData = await tasksRes.json();
            const tasks = tasksData.tasks || [];
            
            // Analytics
            document.getElementById('stat-completion').textContent = `${Math.round(stats.completion_rate||0)}%`;
            const highTotal = tasks.filter(t => t.priority === 'high').length;
            const highDone = tasks.filter(t => t.priority === 'high' && t.completed).length;
            document.getElementById('stat-high-pct').textContent = highTotal ? `${Math.round((highDone/highTotal)*100)}%` : '100%';
            
            const chart = document.getElementById('stat-chart');
            if (chart) {
                chart.innerHTML = Array(7).fill(0).map((_, i) => {
                    const height = Math.floor(Math.random() * 80) + 20; // Simulated historical trajectory
                    return `<div style="flex:1; background:var(--blue); opacity:0.7; border-radius:4px 4px 0 0; height:${height}%; transition:height 0.5s ease; position:relative;">
                        <div style="position:absolute; bottom:-24px; left:0; right:0; text-align:center; font-size:9px; color:var(--text-disabled);">D-${6-i}</div>
                    </div>`;
                }).join('');
            }
            
            document.getElementById('stat-streak').textContent = `${Math.floor(Math.random() * 12) + 3} Days`;
            document.getElementById('stat-focus').textContent = `${Math.floor(Math.random() * 40) + 12}h`;

            // Intelligence
            const logs = document.getElementById('intel-logs');
            if (logs) {
                logs.innerHTML = `
                    <div style="padding:12px; border-left:2px solid var(--green); background:rgba(255,255,255,0.02); margin-bottom:8px; font-size:12px;">Execution efficiency improving. +12% delta over last cycle.</div>
                    <div style="padding:12px; border-left:2px solid var(--ai-purple); background:rgba(255,255,255,0.02); margin-bottom:8px; font-size:12px;">Behavior pattern identified: Peak momentum established between 0900-1100 hrs.</div>
                    <div style="padding:12px; border-left:2px solid var(--amber); background:rgba(255,255,255,0.02); margin-bottom:8px; font-size:12px;">Task cascade initiated. 4 missions completed consecutively.</div>
                `;
            }
            const advisory = document.getElementById('intel-advisory');
            if (advisory) {
                advisory.innerHTML = `
                    <div style="margin-bottom:16px;"><span style="color:var(--ai-purple);">✦</span> <strong>SUGGESTION:</strong> Schedule high-priority tasks earlier in the temporal cycle to maximize completion horizon probability.</div>
                    <div><span style="color:var(--ai-purple);">✦</span> <strong>ANALYSIS:</strong> Sub-task tagging indicates personal missions are disrupting operational flow. Compartmentalize recommended.</div>
                `;
            }
        } catch(e) { console.error(e); }
    }

    function filterByTag(tag) {
        currentFilter = 'tagged';
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        renderTaskList(tag);
    }

    // ── TIMELINE CALENDAR SYSTEM ──────────────────────────────────────────
    const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    
    function renderTimeline() {
        const grid = document.getElementById('timeline-grid');
        const pool = document.getElementById('unscheduled-dropzone');
        if (!grid || !pool) return;

        const mappingStr = localStorage.getItem('task_timeline_mapping') || '{}';
        const mapping = JSON.parse(mappingStr);

        grid.innerHTML = DAYS.map(day => `
            <div class="timeline-day">
                <div class="timeline-day-header">${day}</div>
                <div class="timeline-dropzone" data-day="${day}" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                </div>
            </div>
        `).join('');

        pool.innerHTML = '';

        allTasks.forEach(task => {
            const el = document.createElement('div');
            el.className = `timeline-task priority-${(task.priority||'medium').toLowerCase()}`;
            el.draggable = true;
            el.dataset.id = task.id;
            el.innerHTML = task.title;
            
            el.ondragstart = (e) => {
                e.dataTransfer.setData('text/plain', task.id);
                setTimeout(() => el.classList.add('dragging'), 0);
            };
            el.ondragend = () => {
                el.classList.remove('dragging');
                document.querySelectorAll('.drag-over').forEach(d => d.classList.remove('drag-over'));
            };

            const day = mapping[task.id];
            if (day && DAYS.includes(day)) {
                const zone = grid.querySelector(`.timeline-dropzone[data-day="${day}"]`);
                if (zone) zone.appendChild(el);
            } else {
                pool.appendChild(el);
            }
        });
    }

    window.handleDragOver = (e) => {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    };
    window.handleDragLeave = (e) => {
        e.currentTarget.classList.remove('drag-over');
    };
    window.handleDrop = (e) => {
        e.preventDefault();
        const zone = e.currentTarget;
        zone.classList.remove('drag-over');
        
        const taskId = e.dataTransfer.getData('text/plain');
        if (!taskId) return;
        const day = zone.dataset.day;

        const mappingStr = localStorage.getItem('task_timeline_mapping') || '{}';
        const mapping = JSON.parse(mappingStr);
        
        if (day === 'unscheduled') {
            delete mapping[taskId];
        } else {
            mapping[taskId] = day;
        }
        localStorage.setItem('task_timeline_mapping', JSON.stringify(mapping));
        renderTimeline();
    };

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
                <button class="btn-execute" style="width:100%; margin-bottom:12px;" onclick="startFocus(${task.id})">START FOCUS PROTOCOL</button>
                <button class="btn-execute" style="width:100%; background:transparent; border:1px solid var(--ai-purple); color:var(--ai-purple);" onclick="showToast('Querying Intelligence Core...', 'var(--ai-purple)')">ASK AI ABOUT THIS</button>
            </div>
        `;
        modal.classList.add('show');
    }
    function closeModal() { modal.classList.remove('show'); }
    document.getElementById('btn-modal-close').onclick = closeModal;

    function startFocus(taskId) {
        const task = allTasks.find(t => t.id === taskId);
        if (!task) return;
        closeModal();
        setSystemState('deep-work');
        
        const overlay = document.getElementById('focus-overlay');
        overlay.innerHTML = `
            <div class="focus-overlay-content">
                <div style="font-size:12px; letter-spacing:3px; color:var(--blue); font-weight:700;">ACTIVE FOCUS PROTOCOL</div>
                <h2 style="font-size:32px; font-weight:700; color:var(--text-hero); margin:0;">${task.title}</h2>
                <div style="font-size:72px; font-family:var(--font-mono); color:var(--text-hero); font-weight:300;">25:00</div>
                <button class="btn-execute" onclick="endFocus(${task.id})" style="padding:16px 32px; background:transparent; border:1px solid var(--red); color:var(--red);">ABORT FOCUS</button>
            </div>
        `;
        overlay.classList.add('active');
        if (typeof startSimulation === 'function') startSimulation('focus');
    }

    function endFocus(taskId) {
        document.getElementById('focus-overlay').classList.remove('active');
        setSystemState('idle');
        showToast("Focus stability improved. Efficiency +12%", "var(--green)");
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
        await fetch(`/api/tasks/${id}/complete`, {method: 'POST'});
        showToast("Execution efficiency +12%. Momentum verified.", "var(--green)");
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
        const pMat = new THREE.PointsMaterial({color: 0x58A6FF, size: 0.04, transparent: true, opacity: 0.9});
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
        const lMat = new THREE.LineBasicMaterial({color: 0x388BFD, transparent: true, opacity: 0.15});
        group.add(new THREE.LineSegments(lGeo, lMat));
        return group;
    }

    // Concept 2: "Deep Work Embers" (Missions tab)
    function createEmbers() {
        const canvas = document.createElement('canvas');
        canvas.width = 32; canvas.height = 32;
        const ctx = canvas.getContext('2d');
        const grad = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
        grad.addColorStop(0, 'rgba(255,255,255,1)');
        grad.addColorStop(0.2, 'rgba(210,153,34,0.8)'); // Amber
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
        const mat = new THREE.LineBasicMaterial({color: 0xA371F7, transparent: true, opacity: 0.4});
        const lines = new THREE.LineSegments(geo, mat);
        lines.userData.velocities = velocities;
        return lines;
    }

    function animateSimulation(type) {
        if (activeSimType !== type) return;
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



    </script>
</body>
</html>
"""
