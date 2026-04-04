HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow | Mission Control</title>
    <script src="/static/three.min.js"></script>
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
            
            --emerald:       #4ade80;
            --emerald-glow:  rgba(74, 222, 128, 0.15);

            --font-mono: Consolas, 'Courier New', monospace;
            --font-body: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Ubuntu, 'Helvetica Neue', sans-serif;

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
        
        /* Focus Overlay (The HUD) */
        .focus-overlay {
            position: fixed; inset: 0; background: rgba(6, 10, 15, 0.92);
            backdrop-filter: blur(40px) saturate(200%);
            -webkit-backdrop-filter: blur(40px) saturate(200%);
            z-index: 50000; display: none; opacity: 0; 
            transition: all 1s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 1s linear;
            align-items: center; justify-content: center;
        }
        .focus-overlay.active { display: flex; opacity: 1; }
        .focus-overlay.blur-heavy { backdrop-filter: blur(60px) saturate(150%); }
        .focus-overlay-content {
            width: 100%; max-width: 1000px; padding: 60px;
            display: grid; grid-template-columns: 1fr 1fr; gap: 60px;
            text-align: left;
        }

        .focus-progress-bar {
            position: absolute; top: 0; left: 0;
            height: 2px; background: linear-gradient(90deg, var(--blue), var(--ai-purple));
            transition: width 1s linear; box-shadow: 0 0 10px var(--blue);
            width: 0%; z-index: 50001; display: none;
        }
        .focus-overlay.active ~ .focus-progress-bar { display: block; }
        
        @keyframes timerPulse {
            0%, 100% { text-shadow: 0 0 30px rgba(88,166,255,0.3); }
            50% { text-shadow: 0 0 60px rgba(88,166,255,0.6), 0 0 100px rgba(88,166,255,0.2); }
        }
        .timer-running { animation: timerPulse 4s ease-in-out infinite; }

        .abort-modal {
            position: fixed; inset: 0; z-index: 50002;
            display: none; align-items: center; justify-content: center;
            opacity: 0; transition: opacity 0.3s ease; pointer-events: none;
        }
        .abort-modal.active { display: flex; opacity: 1; pointer-events: auto; }
        .abort-modal-content {
            background: rgba(15, 20, 25, 0.95); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px; padding: 40px; text-align: center; max-width: 400px; width: 100%;
            transform: scale(0.95); transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }
        .abort-modal.active .abort-modal-content { transform: scale(1); }
        .abort-icon { font-size: 40px; color: var(--red); margin-bottom: 20px; animation: glowPulse 2s infinite; }

        .reward-screen {
            position: fixed; inset: 0; z-index: 50002; display: none; align-items: center; justify-content: center;
            background: rgba(6, 10, 15, 0.98); opacity: 0; transition: opacity 0.5s ease;
        }
        .reward-screen.active { display: flex; opacity: 1; }
        .reward-content { text-align: center; max-width: 500px; }
        .reward-title { font-size: 24px; font-weight: 700; color: #f0a030; letter-spacing: 6px; margin-bottom: 12px; text-shadow: 0 0 30px rgba(240,160,48,0.4); }
        .reward-subtitle { font-size: 16px; color: var(--text-hero); margin-bottom: 40px; font-weight:600; }
        .reward-stats {
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px; padding: 30px; margin-bottom: 40px; display: flex; flex-direction: column; gap: 16px;
        }
        .reward-stat-row { font-size: 18px; font-weight: 600; }

        .btn-assist {
            width:100%; background:rgba(163,113,247,0.1); border:1px solid var(--ai-purple); color:var(--ai-purple); padding:16px; border-radius:12px; font-weight:700; cursor:pointer; transition:all 0.3s; display:flex; align-items:center; justify-content:center; gap:8px;
        }
        .btn-assist:hover { background:rgba(163,113,247,0.2); box-shadow: 0 0 20px rgba(163,113,247,0.2); transform: translateY(-2px); }
        .btn-assist:active { transform: translateY(0); }
        .btn-assist.pulsing { animation: glowPulse 2s infinite; }

        .btn-focus-pause {
            flex:1; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); 
            color:var(--text-muted); padding:16px; border-radius:12px; cursor:pointer; font-weight:700; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .btn-focus-pause:hover { background:rgba(255,255,255,0.1); color:var(--text-hero); transform: translateY(-2px); box-shadow: 0 4px 15px rgba(255,255,255,0.05); }
        .btn-focus-pause:active { transform: translateY(1px); box-shadow: none; }

        .btn-focus-abort {
            flex:1; background:transparent; border:1px solid rgba(248,81,73,0.3); color:var(--red); 
            padding:16px; border-radius:12px; cursor:pointer; font-weight:700; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .btn-focus-abort-full { padding: 12px; width: 100%; }
        .btn-focus-abort:hover, .btn-focus-abort-full:hover { 
            background:rgba(248,81,73,0.1); border-color:var(--red); 
            transform: translateY(-2px); box-shadow: 0 4px 20px rgba(248,81,73,0.2); 
        }
        .btn-focus-abort:active, .btn-focus-abort-full:active { transform: translateY(1px); box-shadow: 0 0 10px rgba(248,81,73,0.1); }

        .btn-focus-resume {
            width:100%; background:var(--emerald); border:none; color:#000; padding:16px; border-radius:12px; 
            font-weight:700; font-size:16px; cursor:pointer; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow:0 0 20px rgba(74,222,128,0.4);
        }
        .btn-focus-resume:disabled { opacity: 0.5; filter: grayscale(50%); cursor: not-allowed; transform: none; box-shadow: none; }
        .btn-focus-resume:not(:disabled):hover { filter: brightness(1.1); transform: translateY(-2px) scale(1.02); box-shadow:0 10px 30px rgba(74,222,128,0.5); }
        .btn-focus-resume:not(:disabled):active { transform: translateY(1px) scale(0.98); box-shadow:0 0 10px rgba(74,222,128,0.4); }

        .btn-modal-primary { 
            width:100%; background:rgba(74,222,128,0.1); border:1px solid var(--emerald); color:var(--emerald); 
            padding:16px; border-radius:10px; font-weight:700; font-size:16px; cursor:pointer; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); 
        }
        .btn-modal-primary:hover { 
            background:rgba(74,222,128,0.2); transform: translateY(-2px); box-shadow: 0 4px 15px rgba(74,222,128,0.2); 
            text-shadow: 0 0 10px rgba(74,222,128,0.5);
        }
        .btn-modal-primary:active { transform: translateY(1px); box-shadow: none; }

        .btn-modal-danger { 
            width:100%; background:transparent; border:1px solid rgba(248,81,73,0.2); color:var(--red); 
            padding:12px; border-radius:10px; font-weight:600; cursor:pointer; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); 
        }
        .btn-modal-danger:hover { 
            background:rgba(248,81,73,0.1); border-color:var(--red); transform: translateY(-2px); 
            box-shadow: 0 4px 20px rgba(248,81,73,0.2); 
        }
        .btn-modal-danger:active { transform: translateY(1px); box-shadow: none; }

        .btn-focus-complete {
            width:100%; background:rgba(74,222,128,0.15); border:1px solid var(--emerald); color:var(--emerald); 
            padding:16px; border-radius:12px; font-weight:700; font-size:16px; cursor:pointer; 
            transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); display:flex; align-items:center; justify-content:center; gap:8px;
        }
        .btn-focus-complete:hover { background:rgba(74,222,128,0.25); transform: translateY(-2px); box-shadow: 0 8px 25px rgba(74,222,128,0.3); }
        .btn-focus-complete:active { transform: translateY(1px); box-shadow: 0 0 10px rgba(74,222,128,0.2); }

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
            transition: all 400ms cubic-bezier(0.16, 1, 0.3, 1); 
            margin-bottom: 4px; border: 1px solid transparent;
            will-change: transform, background, border-color, box-shadow;
        }
        .nav-item:hover { 
            background: var(--emerald-glow); 
            color: var(--text-hero);
            border-color: var(--emerald);
            transform: translateY(-1px) translateX(2px);
            box-shadow: 0 4px 20px rgba(74, 222, 128, 0.15);
            text-shadow: 0 0 8px rgba(74, 222, 128, 0.3);
        }
        .nav-item.active { 
            background: rgba(74, 222, 128, 0.1); 
            color: var(--emerald); 
            border-color: rgba(74, 222, 128, 0.2); 
            font-weight: 600;
            box-shadow: inset 0 0 10px rgba(74, 222, 128, 0.05);
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

        /* ─── DEPLOYMENT MODAL (PREMIUM) ───────── */
        .deploy-modal-overlay {
            position: fixed; inset: 0; background: rgba(2, 6, 23, 0.85);
            backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px); z-index: 10000;
            display: none; align-items: center; justify-content: center;
            opacity: 0; pointer-events: none; transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .deploy-modal-overlay.active { display: flex; opacity: 1; pointer-events: auto; }
        
        .deploy-modal {
            background: linear-gradient(165deg, rgba(22, 27, 34, 0.95), rgba(13, 17, 23, 1));
            box-sizing: border-box;
            border: 1px solid rgba(88, 166, 255, 0.25);
            box-shadow: 0 0 64px rgba(0, 0, 0, 0.9), inset 0 1px 1px rgba(255,255,255,0.1);
            border-radius: 28px; width: 100%; max-width: 580px; padding: 48px;
            transform: scale(0.85) translateY(60px) rotateX(-10deg); opacity: 0;
            transition: all 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative; overflow: visible;
        }
        .deploy-modal::before {
            content: ''; position: absolute; top: -1px; left: 50%; width: 60%; height: 1px;
            transform: translateX(-50%);
            background: linear-gradient(90deg, transparent, rgba(88,166,255,0.6), transparent);
        }
        .deploy-modal-overlay.active .deploy-modal {
            transform: scale(1) translateY(0) rotateX(0deg); opacity: 1;
        }
        .close-modal {
            position: absolute; top: -16px; right: -16px; width: 44px; height: 44px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            background: var(--bg-surface); color: var(--text-disabled); border: 1px solid var(--border-neutral);
            font-size: 24px; cursor: pointer; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 100; box-shadow: 0 8px 16px rgba(0,0,0,0.5);
        }
        .close-modal:hover { 
            background: rgba(248, 81, 73, 1); color: #fff; 
            transform: rotate(180deg) scale(1.1); border-color: transparent;
            box-shadow: 0 0 24px rgba(248, 81, 73, 0.6);
        }
        .pill-btn:hover { border-color: var(--blue); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }

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
        .task-list { 
            display: flex; flex-direction: column; gap: 12px; position: relative; 
            overflow: visible; padding-right: 0; /* Expanded to fill the container */
        }

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
        @keyframes focusBtnGlow {
            0%, 100% { box-shadow: 0 0 8px rgba(88,166,255,0.3), 0 0 20px rgba(88,166,255,0.1); }
            50%      { box-shadow: 0 0 16px rgba(88,166,255,0.6), 0 0 40px rgba(88,166,255,0.2); }
        }
        @keyframes focusBtnRipple {
            0%   { transform: scale(1); opacity: 0.6; }
            100% { transform: scale(2.2); opacity: 0; }
        }

        /* Wrapper enables the play button to overflow outside the card */
        .task-card-wrap {
            position: relative;
            overflow: visible;
        }

        .task-card {
            background: linear-gradient(135deg, rgba(13, 17, 23, 0.9), rgba(22, 27, 34, 0.9));
            border: 1px solid rgba(88, 166, 255, 0.12);
            border-left: 3px solid var(--border-neutral);
            border-radius: 12px; padding: 18px 22px; cursor: pointer;
            position: relative; overflow: hidden;
            width: 100%;
            opacity: 0;
            backdrop-filter: blur(var(--system-blur));
            transition: all 450ms cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
            will-change: transform, opacity, box-shadow;
        }
        .task-card.cascade-visible {
            animation: cascadeIn 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }
        .task-card.priority-high  { border-left-color: var(--red); }
        .task-card.priority-medium { border-left-color: var(--amber); }
        .task-card.priority-low   { border-left-color: var(--blue); }
        
        /* Matrix Priorities */
        .task-card.priority-critical { border-left-color: var(--red); }
        .task-card.priority-strategic { border-left-color: var(--blue-mid); }
        .task-card.priority-noise { border-left-color: var(--amber); }
        .task-card.priority-purge { border-left-color: var(--text-disabled); opacity: 0.6; }

        /* Hover: Tactical Shift */
        .task-card-wrap:hover .task-card {
            background: rgba(22, 27, 34, 0.98);
            border-color: rgba(74, 222, 128, 0.4); 
            box-shadow: 0 0 25px rgba(74, 222, 128, 0.15), 0 20px 48px rgba(0,0,0,0.6);
            transform: translateX(-8px) translateY(-2px) scale(1.002);
        }

        /* Border Beam (Premium Detail) */
        .task-card::before {
            content: ''; position: absolute; inset: 0;
            border-radius: 12px; padding: 1px;
            background: linear-gradient(90deg, transparent, var(--emerald), transparent);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            mask-composite: exclude;
            opacity: 0; transition: opacity 0.3s;
            background-size: 200% 100%; animation: borderBeam 3s linear infinite;
            pointer-events: none;
        }
        .task-card-wrap:hover .task-card::before { opacity: 0.8; }

        @keyframes borderBeam { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

        /* Tactical Scanline on Hover */
        .task-card::after {
            content: ''; position: absolute; inset: 0;
            background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(74,222,128,0.03) 3px, transparent 4px);
            opacity: 0; pointer-events: none; transition: opacity 400ms;
            z-index: 10;
        }
        
        /* ─── TACTICAL ACTION STRIP (Integrated) ─── */
        .task-action-strip {
            position: absolute; right: 0; top: 0; bottom: 0;
            width: 0; opacity: 0; overflow: hidden;
            background: linear-gradient(90deg, transparent, rgba(74, 222, 128, 0.1));
            backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
            display: flex; align-items: center; justify-content: flex-end;
            gap: 12px; padding: 0;
            transition: all 400ms cubic-bezier(0.16, 1, 0.3, 1);
            border-radius: 0 12px 12px 0;
            z-index: 20;
        }
        .task-card:hover .task-action-strip {
            width: 100px; opacity: 1; padding: 0 20px;
        }
        
        .action-icon {
            width: 32px; height: 32px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,0.03); border: 1px solid rgba(74, 222, 128, 0.2);
            color: var(--emerald); cursor: pointer; transition: all 200ms;
        }
        .action-icon:hover {
            background: var(--emerald); color: #000;
            box-shadow: 0 0 20px var(--emerald);
            transform: scale(1.1);
        }
        .action-icon svg { width: 14px; height: 14px; fill: currentColor; }
        .action-icon.purge:hover {
            background: var(--red); color: #fff; border-color: var(--red);
            box-shadow: 0 0 20px var(--red);
        }

        .task-card-wrap:hover .task-card::after {
            opacity: 1;
            animation: holographicSweep 3s linear infinite;
        }

        @keyframes holographicSweep { 0% { background-position: 0 0; } 100% { background-position: 0 40px; } }

        .task-card.completing {
            animation: successRipple 0.6s ease forwards;
            pointer-events: none;
        }

        /* ─── TACTICAL CONTROL NODE (Integrated side dock) ─── */
        .task-control-node {
            position: absolute;
            right: -60px; top: 0; bottom: 0; width: 52px;
            background: rgba(13, 17, 23, 0.6);
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(88, 166, 255, 0.3);
            border-left: 1px solid rgba(88, 166, 255, 0.6);
            border-radius: 0 12px 12px 0;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; z-index: 20; opacity: 0;
            transform: translateX(-40px);
            transition: all 450ms cubic-bezier(0.34, 1.56, 0.64, 1);
            pointer-events: none;
            overflow: hidden;
        }
        /* Dock content / Core */
        .control-node-core {
            width: 32px; height: 32px; border-radius: 50%;
            background: rgba(88, 166, 255, 0.1);
            display: flex; align-items: center; justify-content: center;
            transition: all 0.3s ease; position: relative;
            box-shadow: 0 0 15px rgba(88,166,255,0.2);
        }
        .control-node-core svg {
            width: 14px; height: 14px; fill: var(--blue);
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        /* Radar sweep effect inside the node */
        .task-control-node::before {
            content: ''; position: absolute; inset: 0;
            background: linear-gradient(0deg, transparent, rgba(88, 166, 255, 0.1), transparent);
            height: 200%; top: -100%; transition: none;
            pointer-events: none;
        }
        .task-card-wrap:hover .task-control-node::before {
            animation: radarSweep 2s linear infinite;
        }
        @keyframes radarSweep { 0% { transform: translateY(0); } 100% { transform: translateY(50%); } }

        /* Active State */
        .task-card-wrap:hover .task-control-node {
            opacity: 1; pointer-events: auto;
            transform: translateX(0);
        }
        
        /* Node Hover Detail */
        .task-control-node:hover .control-node-core {
            background: var(--blue-dark);
            transform: scale(1.1);
            box-shadow: 0 0 30px rgba(31,111,235,0.6);
        }
        .task-control-node:hover svg { fill: #fff; transform: scale(1.2); }

        /* Priority-specific Nodes */
        .task-card-wrap.priority-high .task-control-node, .task-card-wrap.priority-critical .task-control-node { 
            border-color: rgba(248, 81, 73, 0.4); 
            border-left-color: rgba(248, 81, 73, 0.6);
        }
        .task-card-wrap.priority-high .control-node-core svg, .task-card-wrap.priority-critical .control-node-core svg { fill: var(--red); }
        .task-card-wrap.priority-high:hover .task-control-node, .task-card-wrap.priority-critical:hover .task-control-node { box-shadow: 0 0 20px rgba(248,81,73,0.1); }
        .task-card-wrap.priority-high .task-control-node:hover .control-node-core, .task-card-wrap.priority-critical .task-control-node:hover .control-node-core { background: var(--red); }

        .task-card-wrap.priority-medium .task-control-node, .task-card-wrap.priority-strategic .task-control-node { 
            border-color: rgba(56, 139, 253, 0.4); 
            border-left-color: rgba(56, 139, 253, 0.6);
        }
        .task-card-wrap.priority-medium .control-node-core svg, .task-card-wrap.priority-strategic .control-node-core svg { fill: var(--blue-mid); }
        .task-card-wrap.priority-medium:hover .task-control-node, .task-card-wrap.priority-strategic:hover .task-control-node { box-shadow: 0 0 20px rgba(56,139,253,0.1); }
        .task-card-wrap.priority-medium .task-control-node:hover .control-node-core, .task-card-wrap.priority-strategic .task-control-node:hover .control-node-core { background: var(--blue-mid); }
        
        .task-card-wrap.priority-noise .task-control-node { 
            border-color: rgba(210, 153, 34, 0.4); 
            border-left-color: rgba(210, 153, 34, 0.6);
        }
        .task-card-wrap.priority-noise .control-node-core svg { fill: var(--amber); }
        .task-card-wrap.priority-noise:hover .task-control-node { box-shadow: 0 0 20px rgba(210,153,34,0.1); }
        .task-card-wrap.priority-noise .task-control-node:hover .control-node-core { background: var(--amber); }

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
        .timeline-grid { 
            display: flex; gap: 12px; margin-top: 24px; 
            transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            width: max-content; min-width: 100%;
        }
        .timeline-grid.month-mode { display: grid; grid-template-columns: repeat(7, 1fr); width: 100%; }

        .timeline-day {
            background: rgba(22, 27, 34, 0.4); border: 1px solid var(--border-neutral);
            border-radius: 12px; min-height: 400px; display: flex; flex-direction: column;
            transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
            flex: 1 1 200px; max-width: 450px;
        }
        .timeline-grid.month-mode .timeline-day { flex: none; max-width: none; }

        .timeline-day:hover { transform: translateY(-4px); border-color: rgba(88, 166, 255, 0.3); background: rgba(22, 27, 34, 0.6); }

        .timeline-day-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 10px 14px; border-bottom: 1px solid var(--border-neutral);
            min-height: 42px; width: 100%; box-sizing: border-box;
            user-select: none; -webkit-user-select: none; pointer-events: none;
        }
        .day-label { 
            font-size: 11px; font-weight: 700; color: var(--text-disabled); 
            letter-spacing: 1px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            min-width: 0; flex: 1; pointer-events: none;
        }
        .date-number { 
            font-size: 14px; color: var(--text-hero); font-weight: 700; 
            font-family: var(--font-mono); opacity: 1; margin: 0 0 0 8px; position: static;
            text-shadow: 0 0 10px rgba(88,166,255,0.4); flex-shrink: 0;
            user-select: none; -webkit-user-select: none; pointer-events: none;
        }

        .timeline-dropzone { flex-grow: 1; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
        .timeline-dropzone.drag-over { background: rgba(88,166,255,0.05); border-radius: 0 0 12px 12px; }

        .timeline-task {
            background: rgba(13, 17, 23, 0.9); border: 1px solid rgba(88,166,255,0.1);
            border-left: 3px solid var(--blue); padding: 10px; border-radius: 8px;
            font-size: 11px; color: var(--text-body); cursor: grab;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .timeline-task:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .timeline-task.priority-high { border-left-color: var(--red); }
        .timeline-task.priority-medium { border-left-color: var(--amber); }
        .timeline-task.priority-critical { border-left-color: var(--red); box-shadow: 0 0 10px rgba(248,81,73,0.2); }
        .timeline-task.priority-strategic { border-left-color: var(--blue-mid); }
        .timeline-task.priority-noise { border-left-color: var(--amber); }
        .timeline-task.priority-purge { border-left-color: var(--text-disabled); opacity: 0.5; }
        .timeline-task.dragging { opacity: 0.5; }

        /* Prime Target */
        .prime-target-slot {
            padding: 8px 12px; margin-bottom: 4px;
            border-bottom: 1px dashed rgba(210, 153, 34, 0.3);
            background: linear-gradient(180deg, rgba(210,153,34,0.05), transparent);
            min-height: 40px; display: flex; flex-direction: column; gap: 4px;
            transition: all 0.3s ease;
        }
        .prime-target-slot.drag-over { background: rgba(210, 153, 34, 0.15); }
        .prime-target-label {
            font-size: 9px; font-weight: 800; letter-spacing: 1px;
            color: var(--amber); text-align: center; opacity: 0.7;
            pointer-events: none; margin-bottom: 2px;
        }
        .prime-target-slot .timeline-task {
            border-color: var(--amber);
            background: rgba(210, 153, 34, 0.1);
        }

        /* Multi-View Components */
        .timeline-header-wrap { display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 100; }
        .timeline-selector { position: relative; }
        .timeline-btn {
            background: rgba(22, 27, 34, 0.6);
            backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-neutral);
            padding: 8px 16px; border-radius: 20px;
            color: var(--text-hero); font-size: 12px; font-weight: 600;
            cursor: pointer; display: flex; align-items: center; gap: 8px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .timeline-btn:hover { background: var(--bg-hover); border-color: var(--blue); box-shadow: 0 0 15px rgba(88,166,255,0.2); }
        .timeline-btn:active { transform: scale(0.95); }
        .timeline-btn::after {
            content: ''; position: absolute; inset: 0; border-radius: inherit;
            background: rgba(255,255,255,0.1); opacity: 0; transition: opacity 0.3s;
        }
        .timeline-btn:active::after { opacity: 1; transition: 0s; }
        .timeline-btn .chevron { transition: transform 0.3s; font-size: 10px; opacity: 0.6; }

        .timeline-btn.active .chevron { transform: rotate(180deg); }

        .timeline-dropdown {
            position: absolute; top: calc(100% + 8px); left: 0; min-width: 160px;
            background: rgba(22, 27, 34, 0.95); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-neutral); border-radius: 12px;
            padding: 6px; box-shadow: 0 16px 32px rgba(0,0,0,0.5);
            display: none; flex-direction: column; gap: 2px;
            opacity: 0; transform: translateY(-10px); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .timeline-dropdown.show { display: flex; opacity: 1; transform: translateY(0); }
        .dropdown-item {
            padding: 8px 12px; border-radius: 8px; font-size: 12px; color: var(--text-muted);
            cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between;
        }
        .dropdown-item:hover { background: rgba(88,166,255,0.1); color: var(--text-hero); }
        .dropdown-item.active { background: rgba(88,166,255,0.15); color: var(--blue); font-weight: 600; }

        .timeline-nav { display: flex; align-items: center; gap: 16px; opacity: 0; transform: translateX(20px); transition: all 0.5s; }
        .timeline-nav.show { opacity: 1; transform: translateX(0); }
        .nav-btn {
            background: transparent; border: 1px solid var(--border-neutral);
            color: var(--text-disabled); width: 28px; height: 28px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s;
        }
        .nav-btn:hover { border-color: var(--blue); color: var(--blue); background: rgba(88,166,255,0.05); }
        .current-nav-label { font-size: 14px; font-weight: 600; color: var(--text-hero); font-family: var(--font-mono); min-width: 120px; text-align: center; }

        /* Tactical Scrolling Components */
        .timeline-viewport {
            overflow-x: auto; overflow-y: hidden;
            width: 100%; position: relative; cursor: grab;
            padding-bottom: 24px;
            user-select: none; -webkit-user-select: none;
        }
        /* Premium Minimalist Scrollbar */
        .timeline-viewport::-webkit-scrollbar { height: 2px; }
        .timeline-viewport::-webkit-scrollbar-track { background: transparent; }
        .timeline-viewport::-webkit-scrollbar-thumb { 
            background: rgba(88, 166, 255, 0.1); border-radius: 1px;
            transition: all 0.3s;
        }
        .timeline-viewport:hover::-webkit-scrollbar-thumb,
        .timeline-viewport:active::-webkit-scrollbar-thumb { 
            background: var(--blue); box-shadow: 0 0 10px var(--blue);
        }
        .timeline-viewport:active { cursor: grabbing; }
        
        .view-timeline {
            user-select: none; -webkit-user-select: none; position: relative;
        }




        .timeline-container { position: relative; width: max-content; min-width: 100%; }

        /* Edge Signal Indicators */
        .view-timeline { position: relative; }
        .edge-signal {
            position: absolute; top: 0; bottom: 0; width: 60px; pointer-events: none;
            z-index: 10; opacity: 0; transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .edge-signal-left {
            left: 0;
            background: linear-gradient(90deg, rgba(88,166,255,0.08) 0%, transparent 100%);
            box-shadow: inset 10px 0 20px rgba(88,166,255,0.03);
            border-left: 1px solid rgba(88,166,255,0.1);
        }
        .edge-signal-right {
            /* Adaptive Header System (No Overlap & Non-Selectable) */
        .day-label { 
            font-size: 11px; font-weight: 700; color: var(--text-disabled); 
            letter-spacing: 1px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            min-width: 0; flex: 1; pointer-events: none; user-select: none;
        }
        .date-number { 
            font-size: 14px; color: var(--text-hero); font-weight: 700; 
            font-family: var(--font-mono); opacity: 1; margin: 0 0 0 8px; position: static;
            text-shadow: 0 0 10px rgba(88,166,255,0.4); flex-shrink: 0;
            user-select: none; -webkit-user-select: none; pointer-events: none;
        }

        /* Month View Grid Modifiers */
        .timeline-grid.month-mode { display: grid; grid-template-columns: repeat(7, 1fr); width: 100%; gap: 10px; margin-top: 12px; }
        .timeline-grid.month-mode .timeline-day { min-height: 140px; border-radius: 12px; background: rgba(22, 27, 34, 0.6); flex: none; max-width: none; }
        .timeline-grid.month-mode .timeline-day-header { display: none; }
        
        .timeline-day.today { 
            border-color: var(--blue); background: rgba(88,166,255,0.05); 
            box-shadow: inset 0 0 20px rgba(88,166,255,0.1);
            animation: todayBreath 3s infinite ease-in-out;
        }
        .timeline-day.today .date-number { color: var(--blue); }
        @keyframes todayBreath {
            0%, 100% { border-color: rgba(88,166,255,0.4); }
            50% { border-color: rgba(88,166,255,1); box-shadow: inset 0 0 30px rgba(88,166,255,0.2); }
        }
        .timeline-day.other-month { opacity: 0.3; filter: grayscale(1); }
        .timeline-day.weekend-col { background: rgba(255,255,255,0.01); }
        
        .timeline-header-row { 
            display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; 
            margin-top: 24px; text-align: center; user-select: none; -webkit-user-select: none;
        }
        .header-cell { 
            font-size: 11px; font-weight: 800; color: var(--text-disabled); 
            letter-spacing: 2px; padding: 10px; background: rgba(255,255,255,0.02);
            border-bottom: 1px solid var(--border-neutral); transition: all 0.3s;
        }
        .header-cell.weekend { color: var(--amber); opacity: 0.7; }
        .header-cell.active { color: var(--blue); border-bottom-color: var(--blue); }

        @keyframes todayBreath {
            0%, 100% { border-color: rgba(88,166,255,0.4); }
            50% { border-color: rgba(88,166,255,1); box-shadow: inset 0 0 30px rgba(88,166,255,0.2); }
        }
        .timeline-day.other-month { opacity: 0.15; filter: grayscale(1); }
        .timeline-day.weekend-col { background: rgba(255,255,255,0.01); }
            animation: todayBreath 3s infinite ease-in-out;
        }
        @keyframes todayBreath {
            0%, 100% { border-color: rgba(88,166,255,0.4); }
            50% { border-color: rgba(88,166,255,1); box-shadow: inset 0 0 30px rgba(88,166,255,0.2); }
        }
        .timeline-day.other-month { opacity: 0.15; }
        .timeline-day.weekend-col { background: rgba(255,255,255,0.01); }

        .timeline-day.today { border-color: var(--blue); background: rgba(88,166,255,0.03); }
        .timeline-day.today .date-number { color: var(--blue); opacity: 1; }
        .timeline-day.other-month { opacity: 0.3; filter: grayscale(1); }

        .unscheduled-pool {
            margin-top: 24px; padding: 24px; background: rgba(22, 27, 34, 0.4);
            border: 1px solid var(--border-subtle); border-radius: 16px; min-height: 120px;
            display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-start; align-content: flex-start;
            transition: all 0.3s;
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

    <!-- New Top Progress Bar -->
    <div id="focus-progress-bar" class="focus-progress-bar"></div>

    <div id="focus-overlay" class="focus-overlay">
        <div class="focus-overlay-content">
            <!-- Left: Strategic Info -->
            <div style="display:flex; flex-direction:column; gap:30px;">
                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--blue); letter-spacing:4px; margin-bottom:8px;">FOCUS PROTOCOL ACTIVE</div>
                    <div style="font-size:11px; font-weight:700; color:#f0a030; letter-spacing:3px; margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                        <span>★</span> PRIME TARGET
                    </div>
                    <div id="focus-task-title" style="font-size:28px; color:var(--text-hero); font-weight:700; line-height:1.2;">[TASK NAME]</div>
                </div>

                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--text-disabled); letter-spacing:2px; margin-bottom:12px;">OBJECTIVE</div>
                    <div id="focus-task-notes" style="padding:16px; background:rgba(255,255,255,0.03); border-radius:12px; border:1px solid rgba(255,255,255,0.05); font-size:14px; color:var(--text-body); line-height:1.6; opacity:0.8;">No tactical notes provided.</div>
                </div>

                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--text-disabled); letter-spacing:2px; margin-bottom:12px;">FOCUS CYCLE</div>
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="flex:1; height:8px; background:rgba(255,255,255,0.1); border-radius:4px; overflow:hidden;">
                            <div id="focus-cycle-bar" style="height:100%; width:25%; background:linear-gradient(90deg, var(--blue), var(--ai-purple)); transition:width 0.5s;"></div>
                        </div>
                        <div id="focus-cycle-text" style="font-size:12px; font-weight:700; color:var(--text-hero);">1 / 4</div>
                    </div>
                </div>

                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--text-disabled); letter-spacing:2px; margin-bottom:12px;">SYSTEM STATUS</div>
                    <div id="focus-system-status" style="font-size:14px; color:var(--text-hero); display:flex; align-items:center; gap:8px;">
                        <span style="color:var(--emerald); animation:glowPulse 2s infinite;">●</span> <span id="focus-status-text">Stabilizing focus...</span>
                    </div>
                </div>

                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--text-disabled); letter-spacing:2px; margin-bottom:12px;">DOMAIN NEUTRALIZATION</div>
                    <div id="focus-blocked-list" style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom: 12px;">
                        <!-- Blocked sites will appear here -->
                    </div>
                    <div id="focus-defense-feed" style="font-size:12px; color:var(--text-muted); height:16px; transition:opacity 0.3s; opacity:0;"></div>
                    <div id="focus-defense-counter" style="font-size:11px; color:rgba(255,255,255,0.4); margin-top:8px;">✦ 0 breach attempts deflected</div>
                </div>
            </div>

            <!-- Right: Execution Status -->
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:40px; border-left:1px solid rgba(255,255,255,0.05); padding-left:60px; position:relative;">
                <div id="focus-timer" class="timer-running" style="font-size:120px; font-family:var(--font-mono); font-weight:700; color:var(--blue); line-height:1; transition: color 2s ease;">25:00</div>
                <div id="focus-paused-indicator" style="position:absolute; top:40%; left:50%; transform:translate(-50%,-50%); font-size:24px; font-weight:700; color:var(--text-hero); letter-spacing:8px; display:none; background:rgba(0,0,0,0.8); padding:10px 20px; border-radius:10px; border:1px solid rgba(255,255,255,0.1);">PAUSED</div>
                
                <div id="focus-controls" style="display:flex; flex-direction:column; gap:16px; width:100%;">
                    <button id="btn-focus-ai" onclick="assistExecution()" class="btn-assist pulsing">
                        <span style="font-size:18px;">◆</span> Assist Execution
                    </button>

                    <button id="btn-focus-complete" onclick="promptCompleteMission()" class="btn-focus-complete">
                        ✓ Complete Mission
                    </button>
                    
                    <div style="display:flex; gap:16px;">
                        <button id="btn-focus-pause" onclick="togglePauseFocus()" class="btn-focus-pause">
                            ⏸ Pause
                        </button>
                        <button id="btn-focus-abort" onclick="showAbortModal()" class="btn-focus-abort">
                            Abort Protocol
                        </button>
                    </div>
                </div>
                <!-- Controls shown when paused -->
                <div id="focus-resume-controls" style="display:none; flex-direction:column; gap:16px; width:100%;">
                    <button id="btn-focus-resume" onclick="togglePauseFocus()" class="btn-focus-resume">
                        ▶ Resume Focus <span id="resume-cooldown"></span>
                    </button>
                    <button onclick="showAbortModal()" class="btn-focus-abort btn-focus-abort-full">
                        Abort Protocol
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Abort Modal -->
    <div id="abort-modal" class="abort-modal">
        <div class="abort-modal-content">
            <div class="abort-icon">⚠</div>
            <h2 style="color:var(--text-hero); margin-bottom:12px; font-size:24px;">Abort Focus Session?</h2>
            <p style="color:var(--text-muted); margin-bottom:30px; line-height:1.5;">Progress will be lost.<br>Session discipline will be impacted.</p>
            <div style="display:flex; flex-direction:column; gap:12px;">
                <button onclick="hideAbortModal()" class="btn-modal-primary">Continue Focus</button>
                <button onclick="confirmAbortFocus()" class="btn-modal-danger">Abort Anyway</button>
            </div>
        </div>
    </div>
    
    <!-- Early Completion Modal -->
    <div id="complete-modal" class="abort-modal">
        <div class="abort-modal-content" style="border-color: rgba(74,222,128,0.3); box-shadow: 0 20px 60px rgba(74,222,128,0.15);">
            <div class="abort-icon" style="color: var(--emerald); animation: none; font-size:48px;">✓</div>
            <h2 style="color:var(--text-hero); margin-bottom:12px; font-size:24px;">Mission Completed Early?</h2>
            <p id="complete-modal-time" style="color:var(--text-muted); margin-bottom:30px; line-height:1.5;">Remaining time: calculating...</p>
            <div style="display:flex; flex-direction:column; gap:12px;">
                <button onclick="submitMissionComplete()" class="btn-modal-primary" style="background:var(--emerald); color:#000;">Complete & End Session</button>
                <button onclick="hideCompleteModal()" class="btn-modal-danger" style="color:var(--text-muted); border-color:rgba(255,255,255,0.2);">Continue Focus</button>
            </div>
        </div>
    </div>

    <!-- Momentum Deployment Modal (Base Dashboard) -->
    <div id="momentum-modal" class="abort-modal">
        <div class="abort-modal-content" style="max-width: 600px; padding: 40px; text-align: left; background: rgba(5,7,10,0.95);">
            <div style="text-align: center; margin-bottom: 25px;">
                <div class="reward-icon" style="font-size:24px; color:var(--emerald); letter-spacing:6px; margin-bottom:12px;">✨ MISSION COMPLETE ✨</div>
                <h2 id="momentum-cycle-text" style="color:var(--text-hero); font-size:18px; font-weight:700; margin-bottom:20px;">Focus Cycle Completed</h2>
                
                <div class="reward-stats" style="margin-bottom: 25px;">
                    <div style="color:var(--emerald); font-weight:700; margin-bottom:12px;">+<span id="momentum-reward-minutes">25</span> min Deep Work</div>
                    <div id="momentum-efficiency" style="color:var(--blue); font-weight:700; margin-bottom:12px;">Execution Efficiency ↑</div>
                    <div style="color:var(--ai-purple); font-weight:700;">System Stability: OPTIMAL</div>
                </div>

                <div style="width: 50px; height: 2px; background: rgba(255,255,255,0.1); margin: 0 auto 25px;"></div>

                <div style="font-size: 32px; color: var(--blue); margin-bottom: 10px; animation: glowPulse 2s infinite;">⚡</div>
                <h2 style="color:var(--text-hero); font-size:24px; margin: 0;">Momentum Detected</h2>
                <p style="color:var(--text-muted); font-size: 14px; margin-top: 8px;">Stay in execution flow?</p>
            </div>
            
            <div style="margin-bottom: 16px; font-size: 12px; font-weight: 700; color: var(--text-disabled); letter-spacing: 2px; text-align: center;">NEXT OPTIMAL TARGETS</div>
            
            <div id="momentum-targets-container" style="display: flex; flex-direction: column; gap: 12px; max-height: 250px; overflow-y: auto; padding-right:8px;">
                <!-- dynamic targets loaded here -->
            </div>
            
            <div style="margin-top: 25px; text-align: center;">
                <button onclick="hideMomentumModal()" style="background: transparent; border: none; color: var(--text-muted); font-size: 14px; cursor: pointer; text-decoration: underline; transition: all 0.2s;" onmouseover="this.style.color='var(--text-hero)'" onmouseout="this.style.color='var(--text-muted)'">Close & Return to Dashboard</button>
            </div>
        </div>
    </div>
    
    <!-- Reward Screen -->
    <div id="reward-screen" class="reward-screen">
        <div class="reward-content">
            <div class="reward-title">✦ MISSION COMPLETE ✦</div>
            <div id="reward-cycle-text" class="reward-subtitle">Focus Cycle 1/4 Completed</div>
            
            <div class="reward-stats">
                <div class="reward-stat-row">
                    <span style="color:var(--emerald);">+<span id="reward-minutes">25</span> min Deep Work</span>
                </div>
                <div class="reward-stat-row">
                    <span style="color:var(--blue);">Execution Efficiency ↑</span>
                </div>
                <div class="reward-stat-row">
                    <span style="color:var(--ai-purple);">System Stability: HIGH</span>
                </div>
            </div>
            
            <div style="color:var(--text-muted); margin-bottom:40px; line-height:1.6;">
                Session discipline maintained.<br>
                Take a short break to recover.
            </div>
            
            <button onclick="closeRewardScreen()" style="background:var(--bg-surface); border:1px solid rgba(255,255,255,0.1); color:var(--text-hero); padding:16px 32px; border-radius:12px; font-weight:700; cursor:pointer; transition:all 0.3s; box-shadow:0 0 20px rgba(255,255,255,0.1);">
                Return to Dashboard
            </button>
        </div>
    </div>

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

                <div class="mission-panel" style="padding:16px; margin-bottom:16px; border-radius:8px;">
                    <div class="section-label" style="font-size:9px; margin-bottom:12px;">SIGNAL FILTERS</div>
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

                <div style="display:flex; justify-content:space-between; align-items:center; margin: 32px 0 16px;">
                    <div class="section-label" style="font-size:10px; margin:0; letter-spacing:3px;">PRIORITY SIGNALS</div>
                    <div id="header-task-count" style="font-size:10px; color:var(--text-disabled); font-family:var(--font-mono);">0 ACTIVE</div>
                </div>
                <div id="task-list-container" class="task-list">
                    <div class="filament-line"></div>
                    <!-- Quantum Content -->
                </div>
            </div>
        </div>

        <!-- VIEW: TIMELINE -->
        <div id="view-timeline" class="view-content hidden">
            <div class="timeline-header-wrap">
                <div style="display: flex; flex-direction: column;">
                    <div class="section-label" style="margin:0;">TIMELINE PROTOCOL</div>
                    <div class="timeline-selector" id="timeline-selector">
                        <button class="timeline-btn" id="timeline-view-btn">
                            <span id="current-view-label">THIS WEEK</span>
                            <span class="chevron">▾</span>
                        </button>
                        <div class="timeline-dropdown" id="timeline-dropdown">
                            <div class="dropdown-item active" data-view="week">This Week</div>
                            <div class="dropdown-item" data-view="month">This Month</div>
                            <div class="dropdown-item" data-view="calendar">Full Calendar</div>
                        </div>
                    </div>
                </div>

                <div class="timeline-nav" id="timeline-nav">
                    <button class="nav-btn" id="prev-btn">←</button>
                    <div class="current-nav-label" id="timeline-period-label">March 2026</div>
                    <button class="nav-btn" id="next-btn">→</button>
                </div>
            </div>
            
            <div id="timeline-header-row" class="timeline-header-row" style="display:none;">
                <div class="header-cell">MON</div>
                <div class="header-cell">TUE</div>
                <div class="header-cell">WED</div>
                <div class="header-cell">THU</div>
                <div class="header-cell">FRI</div>
                <div class="header-cell weekend">SAT</div>
                <div class="header-cell weekend">SUN</div>
            </div>

            <div class="timeline-viewport" id="timeline-viewport">

                <div class="edge-signal edge-signal-left" id="signal-left"></div>
                <div class="edge-signal edge-signal-right" id="signal-right"></div>
                
                <div class="timeline-container">
                    <div class="timeline-grid" id="timeline-grid">
                        <!-- Days injected by JS -->
                    </div>
                </div>
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
            <button class="btn-deploy btn-execute" onclick="toggleCreateMission()" style="margin-top:20px; font-size:12px; font-weight:700; background: linear-gradient(135deg, rgba(88,166,255,0.15), rgba(88,166,255,0.05)); color: var(--blue); border: 1px solid rgba(88,166,255,0.2); width:100%; transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.2);">+ CREATE MISSION</button>
        </div>
    </aside>

    <div id="deploy-modal-overlay" class="deploy-modal-overlay">
        <div class="deploy-modal">
            <div class="close-modal" onclick="toggleCreateMission()">×</div>
            <div class="section-label" style="margin-bottom:24px;">NEW MISSION DEPLOYMENT</div>
            <div class="flex-row">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">OBJECTIVE</label>
                    <input type="text" id="mission-title" class="input-system" placeholder="Enter tactical objective..." autocomplete="off">
                </div>
            </div>
            <div class="flex-row" style="margin-top:24px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">PRIORITY PROTOCOL</label>
                    <div class="priority-grid">
                        <button class="pill-btn" data-priority="low">LOW</button>
                        <button class="pill-btn selected" data-priority="medium">MEDIUM</button>
                        <button class="pill-btn" data-priority="high">HIGH</button>
                    </div>
                </div>
            </div>
            <div class="flex-row" style="margin-top:24px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">TAG SIGNALS (COMMA SEPARATED)</label>
                    <input type="text" id="mission-tags" class="input-system" placeholder="e.g. work, personal, critical" autocomplete="off">
                </div>
            </div>
            <div style="display:flex; gap:12px; margin-top:32px;">
                <button class="btn-deploy" id="btn-deploy" disabled style="margin:0;">DEPLOY</button>
                <button class="btn-execute" onclick="toggleCreateMission()" style="margin:0; background:transparent; border-color:var(--border-neutral); color:var(--text-muted); width:auto; padding:0 24px;">CANCEL</button>
            </div>
        </div>
    </div>

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
        const p = document.getElementById('deploy-modal-overlay');
        p.classList.toggle('active');
        if (p.classList.contains('active')) {
            setTimeout(() => document.getElementById('mission-title').focus(), 100);
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
            const countEl = document.getElementById('header-task-count');
            if (countEl) countEl.textContent = `${filtered.length} ACTIVE`;

            showToast("Rendering " + filtered.length + " tasks", "var(--green)");

            // 2. Render new DOM
            container.innerHTML = filtered.map((t) => `
                <div class="task-card-wrap priority-${(t.priority||'medium').toLowerCase()}" data-id="${t.id}">
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
                        <div class="task-action-strip">
                            <div class="action-icon" onclick="event.stopPropagation(); startFocusFromCard(${t.id}, this)" title="Deploy Focus Protocol">
                                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M8 5v14l11-7z"/></svg>
                            </div>
                            <div class="action-icon purge" onclick="event.stopPropagation(); purgeTask(${t.id}, this)" title="Purge Mission Records">
                                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                            </div>
                        </div>
                    </div>
                `).join('');

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
                    card.classList.add('cascade-visible');

                    requestAnimationFrame(() => {
                        requestAnimationFrame(() => {
                            card.style.transition = 'transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)';
                            card.style.transform = 'translateY(0)';
                        });
                    });
                } else {
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
        } catch(e) {
            console.error("renderTaskList failed:", e);
            showToast('TaskList Render Error: ' + e.message, 'var(--red)');
        }
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

            allTasks.forEach(task => {
                const el = document.createElement('div');
                el.className = `timeline-task priority-${(task.priority||'medium').toLowerCase()}`;
                el.draggable = true;
                el.dataset.id = task.id;
                
                // Force dynamic width in week mode
                const ws = timelineState.view === 'week' ? 'white-space:nowrap;' : '';
                el.innerHTML = `<div style="overflow:hidden; text-overflow:ellipsis; ${ws}">${task.title}</div>`;

                
                el.ondragstart = (e) => {
                    e.dataTransfer.setData('application/task-id', task.id.toString());
                    setTimeout(() => el.classList.add('dragging'), 0);
                };
                el.ondragend = () => {
                    el.classList.remove('dragging');
                    document.querySelectorAll('.drag-over').forEach(d => d.classList.remove('drag-over'));
                };

                const dateKey = mapping[task.id];
                if (dateKey) {
                    const zone = grid.querySelector(`[data-date="${dateKey}"]`);
                    if (zone) zone.appendChild(el);
                    else if (timelineState.view === 'week' || timelineState.view === 'calendar' || timelineState.view === 'month') {
                        const baseDate = dateKey.replace('_prime', '');
                        const fallbackZone = grid.querySelector(`.timeline-dropzone[data-date="${baseDate}"]`);
                        if (fallbackZone) fallbackZone.appendChild(el);
                        else pool.appendChild(el);
                    }
                    else pool.appendChild(el);
                } else {
                    pool.appendChild(el);
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

    function startFocusFromCard(taskId, btnEl) {
        // High-fidelity feedback pulse
        if (btnEl) {
            const core = btnEl.querySelector('.control-node-core');
            if (core) {
                core.style.transform = 'scale(0.8)';
                core.style.boxShadow = '0 0 40px var(--blue)';
            }
            btnEl.style.background = 'rgba(88, 166, 255, 0.2)';
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
                    `<div class="badge tag" style="background:rgba(248,81,73,0.1); border-color:rgba(248,81,73,0.3); color:var(--red);">${s}</div>`
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
            timerEl.style.textShadow = '0 0 50px rgba(248,81,73,0.5)';
        } else if (remaining <= 300) {
            timerEl.style.color = '#f0a030';
            timerEl.style.textShadow = '0 0 50px rgba(240,160,48,0.5)';
        } else {
            timerEl.style.color = 'var(--blue)';
        }

        const elapsedMins = Math.floor(passedData / 60);
        if (elapsedMins >= 20) overlay.style.boxShadow = 'inset 0 0 100px rgba(163,113,247,0.3)';
        else if (elapsedMins >= 10) overlay.style.boxShadow = 'inset 0 0 80px rgba(88,166,255,0.2)';
        else if (elapsedMins >= 5) overlay.style.boxShadow = 'inset 0 0 50px rgba(88,166,255,0.1)';
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
        hideCompleteModal();
        const timeUsedSecs = totalFocusSecondsInitial - (currentFocusMinutesLeft * 60);
        const timeSavedMins = currentFocusMinutesLeft;
        const timeUsedMins = Math.floor(timeUsedSecs / 60);
        const effScore = Math.floor((totalFocusSecondsInitial / (timeUsedSecs > 0 ? timeUsedSecs : 1)) * 100);
        const finalEffScore = effScore > 500 ? 500 : effScore;
        
        try {
            await fetch('/api/focus/complete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    efficiency_score: finalEffScore, 
                    time_saved: timeSavedMins,
                    time_used: timeUsedMins
                })
            });
            deactivateFocusLock();
            loadTasks();
            
            // Pop the unified Momentum Modal directly
            const cycleText = document.getElementById('focus-cycle-text');
            const cText = cycleText ? `Focus Cycle ${cycleText.innerText} Completed` : 'Focus Cycle Completed';
            
            openMomentumDeployment(timeUsedMins, timeSavedMins, finalEffScore, cText);
            
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
                <div class="task-card" style="padding: 20px; cursor: default; transition:all 0.3s;" onmouseenter="this.style.boxShadow='0 0 20px rgba(88,166,255,0.2)'; this.style.transform='translateX(4px)'" onmouseleave="this.style.boxShadow='none'; this.style.transform='none'">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-weight:700; color:var(--text-hero); font-size: 18px; margin-bottom: 8px;">${t.title}</div>
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
        deactivateFocusLock();
        document.getElementById('reward-minutes').innerText = Math.round(totalFocusSecondsInitial / 60);
        const cycleText = document.getElementById('focus-cycle-text');
        if(cycleText) document.getElementById('reward-cycle-text').innerText = `Focus Cycle ${cycleText.innerText} Completed`;
        
        document.getElementById('reward-screen').classList.add('active');
        showToast("Execution efficiency +12%. Momentum verified.", "var(--green)");
        loadTasks();
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
