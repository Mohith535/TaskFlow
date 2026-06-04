HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow | Mission Control</title>
    <script src="/static/three.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
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
            --font-body: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Ubuntu, 'Helvetica Neue', sans-serif;

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

        .pill-btn-small {
            border: 1px solid var(--border-neutral); background: transparent;
            padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500;
            cursor: pointer; color: var(--text-muted); transition: all 150ms;
        }
        .pill-btn-small:hover { border-color: var(--text-disabled); color: var(--text-body); }
        .pill-btn-small.selected {
            background: rgba(88,166,255,0.1);
            border-color: #58A6FF;
            color: #58A6FF;
            transform: translateY(-1px);
            box-shadow: 0 0 12px rgba(88,166,255,0.15);
            animation: pillBounce 200ms ease-out;
        }
        @keyframes pillBounce {
            0%   { transform: translateY(-1px) scale(1); }
            40%  { transform: translateY(-3px) scale(1.04); }
            100% { transform: translateY(-1px) scale(1); }
        }

        .btn-deploy {
            width: 100%; margin-top: 16px; height: 44px; background: var(--bg-surface);
            border: 1px solid var(--border-neutral); border-radius: 8px;
            color: var(--text-muted); font-weight: 600; cursor: pointer; transition: all 200ms;
        }
        .btn-deploy.active { background: var(--blue-dark); color: #fff; border-color: var(--blue-dark); }
        .btn-deploy.active:hover { box-shadow: 0 8px 24px rgba(31,111,235,0.4); transform: translateY(-1px); }

        /* ─── DEPLOYMENT MODAL (PREMIUM) ───────── */
        .deploy-modal-overlay {
            position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); z-index: 10000;
            display: flex; align-items: stretch; justify-content: flex-end;
            opacity: 0; pointer-events: none; transition: opacity 200ms ease-out;
        }
        .deploy-modal-overlay.active { opacity: 1; pointer-events: auto; }

        /* Create Mission = right side panel, never overflows the viewport */
        .deploy-modal {
            background: linear-gradient(180deg, #0D1117, #0A0E13);
            box-sizing: border-box;
            border-left: 1px solid var(--border-subtle);
            box-shadow: -24px 0 64px rgba(0, 0, 0, 0.6);
            width: 480px; max-width: 100%; height: 100vh; max-height: 100vh;
            padding: 0; display: flex; flex-direction: column; overflow: hidden;
            position: relative;
            transform: translateX(100%); opacity: 0;
            transition: transform 280ms cubic-bezier(0.16, 1, 0.3, 1), opacity 200ms ease-out;
        }
        .deploy-modal-overlay.active .deploy-modal { transform: translateX(0); opacity: 1; }

        /* Zone A — header (fixed) */
        .dm-header { flex-shrink: 0; padding: 16px 24px 12px; border-bottom: 1px solid var(--border-subtle); background: #0D1117; }
        .dm-header-top { display: flex; align-items: center; justify-content: space-between; }
        .dm-title-label { font-size: 11px; font-weight: 500; letter-spacing: 2px; color: var(--text-disabled); text-transform: uppercase; }
        .dm-dots { display: flex; gap: 6px; margin-top: 12px; }
        .dm-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--border-neutral); transition: background 200ms ease, box-shadow 200ms ease; }
        .dm-dot.filled { background: var(--blue); box-shadow: 0 0 8px rgba(88,166,255,0.5); }

        /* Zone B — scrollable content */
        .dm-body { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 24px 24px 16px; -webkit-overflow-scrolling: touch; transition: box-shadow 150ms ease; }
        .dm-body::-webkit-scrollbar { width: 4px; }
        .dm-body::-webkit-scrollbar-track { background: transparent; }
        .dm-body::-webkit-scrollbar-thumb { background: var(--border-neutral); border-radius: 4px; }
        .dm-body::-webkit-scrollbar-thumb:hover { background: var(--text-disabled); }

        /* Zone C — footer (fixed) */
        .dm-footer { flex-shrink: 0; height: 72px; display: flex; align-items: center; gap: 12px; padding: 0 24px; border-top: 1px solid var(--border-subtle); background: #0D1117; }
        .dm-footer .btn-deploy { flex: 1; margin: 0; height: 44px; border-radius: 10px; }
        .btn-deploy.active { background: linear-gradient(135deg, #1F6FEB, #388BFD); color: #fff; border-color: transparent; animation: deployPulse 2.5s ease-in-out infinite; }
        @keyframes deployPulse { 0%,100% { box-shadow: 0 4px 16px rgba(31,111,235,0.35); } 50% { box-shadow: 0 6px 28px rgba(31,111,235,0.6); } }
        .btn-deploy.active:hover { transform: translateY(-1px); box-shadow: 0 8px 32px rgba(31,111,235,0.6); }
        .dm-cancel { width: 90px; height: 44px; background: transparent; border: 1px solid var(--border-neutral); border-radius: 10px; color: var(--text-muted); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 150ms ease; }
        .dm-cancel:hover { border-color: var(--text-disabled); color: var(--text-body); }

        /* Section 4 — collapsible enrichment */
        .dm-enrich { margin-top: 8px; }
        .dm-enrich-toggle { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; height: 38px; background: #161B22; border: 1px dashed var(--border-neutral); border-radius: 8px; font-size: 12px; color: var(--text-disabled); cursor: pointer; transition: all 150ms ease; }
        .dm-enrich-toggle:hover { border-color: var(--text-disabled); color: var(--text-muted); background: #1C2128; }
        .dm-enrich.open .dm-enrich-toggle { border-style: solid; color: var(--text-muted); }
        .dm-enrich-body { max-height: 0; overflow: hidden; transition: max-height 400ms cubic-bezier(0.4, 0, 0.2, 1); }
        .dm-enrich.open .dm-enrich-body { max-height: 1000px; }
        .dm-enrich-body .flex-row { margin-top: 14px !important; }

        /* Mobile — bottom sheet */
        @media (max-width: 768px) {
            .deploy-modal-overlay { align-items: flex-end; justify-content: center; }
            .deploy-modal { width: 100%; height: 90vh; max-height: 90vh; border-left: none;
                border-top-left-radius: 20px; border-top-right-radius: 20px;
                transform: translateY(100%); }
            .deploy-modal-overlay.active .deploy-modal { transform: translateY(0); }
        }
        .close-modal {
            position: absolute; top: 18px; right: 18px; width: 42px; height: 42px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,0.06); color: var(--text-muted); border: 1px solid rgba(255,255,255,0.12);
            font-size: 20px; cursor: pointer; transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 100; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
        }
        .close-modal:hover { 
            background: rgba(248, 81, 73, 0.9); color: #fff; 
            transform: rotate(90deg) scale(1.1); border-color: transparent;
            box-shadow: 0 0 24px rgba(248, 81, 73, 0.5), 0 0 60px rgba(248, 81, 73, 0.15);
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
            transform: translateY(18px);
            opacity: 0;
            backdrop-filter: blur(var(--system-blur));
            transition: all 450ms cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
            will-change: transform, opacity, box-shadow;
        }
        .task-card.cascade-visible {
            opacity: 1;
            transform: translateY(0);
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

        /* ─── OMNIBAR (FRICTIONLESS CAPTURE) ──── */
        .omnibar-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            z-index: 25000; display: flex; align-items: flex-start; justify-content: center;
            padding-top: 18vh; background: rgba(0,0,0,0.5);
            backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
            opacity: 0; pointer-events: none;
            transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .omnibar-overlay.active { opacity: 1; pointer-events: auto; }
        .omnibar-container {
            position: relative; width: 560px; max-width: 90vw;
            transform: translateY(-30px) scale(0.96);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .omnibar-overlay.active .omnibar-container {
            transform: translateY(0) scale(1);
        }
        #omnibar-input {
            width: 100%; background: rgba(15, 20, 25, 0.95);
            border: 1px solid rgba(163, 113, 247, 0.3);
            border-radius: 16px; padding: 20px 28px;
            color: var(--text-hero); font-size: 15px; font-family: 'Inter', sans-serif;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            outline: none; box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 30px rgba(163,113,247,0.1);
        }
        #omnibar-input:focus {
            border-color: rgba(163, 113, 247, 0.6);
            box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 40px rgba(163,113,247,0.25);
        }
        #omnibar-input:disabled { opacity: 0.5; cursor: wait; }
        #omnibar-input::placeholder { color: var(--text-disabled); }
        .omnibar-hints {
            display: flex; justify-content: space-between; align-items: center;
            margin-top: 10px; padding: 0 8px;
        }
        .omnibar-hint {
            font-size: 10px; font-weight: 600; letter-spacing: 0.8px;
            color: rgba(255,255,255,0.25);
        }
        .omnibar-hint kbd {
            background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
            border-radius: 4px; padding: 2px 6px; font-family: var(--font-mono); font-size: 9px;
        }
        .omnibar-flash { animation: omniFlash 0.5s ease-out; }
        @keyframes omniFlash { 0% { background: rgba(163,113,247,0.3); border-color:var(--ai-purple); transform: scale(1.02); } 100% { background: rgba(15, 20, 25, 0.95); border-color: rgba(163,113,247,0.3); transform: scale(1); } }
        
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
            right: 0;
            background: linear-gradient(270deg, rgba(88,166,255,0.08) 0%, transparent 100%);
            box-shadow: inset -10px 0 20px rgba(88,166,255,0.03);
            border-right: 1px solid rgba(88,166,255,0.1);
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

        .unscheduled-pool {
            margin-top: 24px; padding: 24px; background: rgba(22, 27, 34, 0.4);
            border: 1px solid var(--border-subtle); border-radius: 16px; min-height: 120px;
            display: flex; gap: 12px; flex-wrap: nowrap; overflow-x: auto; align-items: center;
            transition: all 0.3s;
        }
        .unscheduled-pool::-webkit-scrollbar {
            height: 6px;
        }
        .unscheduled-pool::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
        }
        .unscheduled-pool.drag-over { background: rgba(88,166,255,0.05); border-color: var(--blue); }


        
        .task-title { flex: 1; font-weight: 500; font-size: 15px; color: var(--text-body); }
        .badge { font-size: 9px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
        .badge.high { color: var(--red); background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.2); }
        .badge.medium { color: var(--amber); background: rgba(210,153,34,0.1); border: 1px solid rgba(210,153,34,0.2); }
        .badge.low { color: var(--blue); background: rgba(88,166,255,0.1); border: 1px solid rgba(88,166,255,0.2); }
        .badge.tag { color: var(--ai-purple); background: rgba(163,113,247,0.1); border: 1px solid rgba(163,113,247,0.2); }

        /* ═══════════════════════════════════════════════════════════
           TASK ENRICHMENT — card row (E10) + inline expand (E11) + create panel (E12)
           ═══════════════════════════════════════════════════════════ */
        .enrich-zone { padding-left: 28px; margin-top: 8px; }

        /* ── E10: enrichment row of pills ── */
        .enrich-row {
            display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
            cursor: pointer; user-select: none;
        }
        .enrich-pill {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: 600;
            background: rgba(139,148,158,0.08); border: 1px solid rgba(139,148,158,0.15);
            color: var(--text-muted); transition: all 160ms ease; line-height: 1.6;
        }
        .enrich-pill .ep-ico { font-size: 11px; line-height: 1; }
        .enrich-pill:hover { transform: translateY(-1px); }
        .enrich-pill.ep-links { color: var(--blue); background: rgba(88,166,255,0.08); border-color: rgba(88,166,255,0.18); }
        .enrich-pill.ep-map   { color: var(--green); background: rgba(63,185,80,0.08); border-color: rgba(63,185,80,0.2); }
        .enrich-pill.ep-check { color: var(--text-muted); background: rgba(139,148,158,0.08); border-color: rgba(139,148,158,0.15); }
        .enrich-pill.ep-check.in-progress { color: var(--amber); background: rgba(210,153,34,0.08); border-color: rgba(210,153,34,0.2); }
        .enrich-pill.ep-check.all-done { color: var(--green); background: rgba(63,185,80,0.1); border-color: rgba(63,185,80,0.25); }
        .enrich-pill .ep-bar {
            position: relative; width: 40px; height: 2px; border-radius: 2px;
            background: rgba(255,255,255,0.1); overflow: hidden; margin-left: 2px;
        }
        .enrich-pill .ep-bar > i {
            position: absolute; left: 0; top: 0; bottom: 0; border-radius: 2px;
            background: var(--amber); transition: width 300ms ease-out;
        }
        .enrich-pill.ep-check.all-done .ep-bar > i { background: var(--green); }
        .enrich-row .enrich-hint {
            margin-left: auto; font-size: 10px; color: var(--text-disabled);
            opacity: 0; transition: opacity 160ms ease; white-space: nowrap;
        }
        .task-card-wrap:hover .enrich-row .enrich-hint { opacity: 1; }
        .enrich-hint .chev { display: inline-block; transition: transform 280ms cubic-bezier(0.16,1,0.3,1); }
        .enrich-zone.open .enrich-hint .chev { transform: rotate(180deg); }

        /* ── E11: inline expand ── */
        .enrich-expand {
            max-height: 0; overflow: hidden;
            transition: max-height 300ms ease-out, opacity 220ms ease, margin 300ms ease-out;
            opacity: 0;
        }
        .enrich-expand.open {
            opacity: 1; margin-top: 12px; padding-top: 12px;
            border-top: 1px solid var(--border-subtle);
        }
        .enrich-sub { margin-bottom: 16px; }
        .enrich-sub:last-of-type { margin-bottom: 6px; }
        .enrich-sub-label {
            font-size: 10px; text-transform: uppercase; letter-spacing: 1.5px;
            color: var(--text-disabled); font-weight: 700; margin-bottom: 8px; display: block;
        }
        .enrich-notes-text {
            font-size: 13px; color: var(--text-body); line-height: 1.7;
            white-space: pre-wrap; max-height: 120px; overflow-y: auto;
            padding-right: 6px;
        }
        .enrich-notes-text.clamped { max-height: 60px; }
        .enrich-showmore { font-size: 11px; color: var(--blue); cursor: pointer; margin-top: 4px; display: inline-block; }

        .enrich-link-row {
            display: flex; align-items: center; gap: 10px; padding: 6px 8px;
            border-radius: 8px; transition: background 140ms ease;
        }
        .enrich-link-row:hover { background: rgba(255,255,255,0.03); }
        .enrich-link-row .elr-ico { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }
        .enrich-link-row .elr-ico.t-url { color: var(--blue); }
        .enrich-link-row .elr-ico.t-map { color: var(--green); }
        .enrich-link-row .elr-ico.t-reference, .enrich-link-row .elr-ico.t-file { color: var(--text-muted); }
        .enrich-link-row .elr-label {
            flex: 1; font-size: 12px; color: var(--text-body);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .enrich-link-row .elr-id { font-size: 9px; color: var(--text-disabled); font-family: var(--font-mono); flex-shrink: 0; }
        .enrich-link-btn {
            background: none; border: none; cursor: pointer; font-size: 11px;
            font-weight: 600; padding: 2px 6px; border-radius: 6px; flex-shrink: 0;
            transition: all 140ms ease;
        }
        .enrich-link-btn.open { color: var(--blue); }
        .enrich-link-btn.open:hover { background: rgba(88,166,255,0.12); }
        .enrich-link-btn.copy { color: var(--text-muted); }
        .enrich-link-btn.copy:hover { background: rgba(139,148,158,0.12); color: var(--text-body); }

        .enrich-prog-track {
            height: 3px; background: #21262D; border-radius: 3px; margin-bottom: 10px; overflow: hidden;
        }
        .enrich-prog-fill {
            height: 100%; border-radius: 3px; background: var(--amber);
            transition: width 320ms cubic-bezier(0.16,1,0.3,1); width: 0%;
        }
        .enrich-prog-fill.complete { background: var(--green); }
        .enrich-chk-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
        .enrich-cbx {
            width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid var(--border-neutral);
            background: transparent; flex-shrink: 0; cursor: pointer; position: relative;
            transition: all 160ms ease; display: flex; align-items: center; justify-content: center;
        }
        .enrich-cbx:hover { border-color: var(--green); }
        .enrich-cbx svg { width: 11px; height: 11px; opacity: 0; transform: scale(0.2); transition: none; }
        .enrich-cbx.checked { background: var(--green); border-color: var(--green); }
        .enrich-cbx.checked svg { opacity: 1; transform: scale(1); animation: cbxPop 220ms cubic-bezier(0.34,1.56,0.64,1); }
        @keyframes cbxPop { 0% { transform: scale(0.2); } 60% { transform: scale(1.25); } 100% { transform: scale(1); } }
        .enrich-chk-text { font-size: 13px; color: var(--text-body); transition: color 200ms ease; }
        .enrich-chk-row.done .enrich-chk-text {
            color: var(--text-disabled);
            text-decoration: line-through; text-decoration-color: var(--text-disabled);
            animation: strikethrough 320ms ease-out forwards;
        }
        @keyframes strikethrough { from { text-decoration-color: transparent; } to { text-decoration-color: var(--text-disabled); } }
        .enrich-collapse {
            display: block; width: 100%; text-align: center; margin-top: 10px;
            background: none; border: none; color: var(--text-disabled);
            font-size: 11px; cursor: pointer; transition: color 140ms ease;
        }
        .enrich-collapse:hover { color: var(--text-muted); }
        .enrich-flash { animation: enrichFlash 380ms ease-out; }
        @keyframes enrichFlash { 0% { background: rgba(63,185,80,0); } 40% { background: rgba(63,185,80,0.14); } 100% { background: rgba(63,185,80,0); } }
        .enrich-confetti-piece {
            position: absolute; width: 6px; height: 6px; border-radius: 1px;
            pointer-events: none; z-index: 50; will-change: transform, opacity;
        }
        @keyframes enrichConfetti {
            0%   { transform: translate(0,0) rotate(0deg); opacity: 1; }
            100% { transform: translate(var(--cx), var(--cy)) rotate(var(--cr)); opacity: 0; }
        }

        /* ── E12: create-mission enrichment fields ── */
        .enrich-textarea {
            width: 100%; min-height: 72px; max-height: 200px; resize: none;
            line-height: 1.6; font-family: var(--font-body);
        }
        .enrich-textarea::placeholder { color: var(--text-disabled); }
        .enrich-textarea:focus { border-color: var(--blue-mid); box-shadow: 0 0 0 3px rgba(56,139,253,0.08); }
        .enrich-counter { font-size: 10px; color: var(--text-disabled); text-align: right; min-height: 12px; opacity: 0; transition: opacity 200ms ease; }
        .enrich-counter.show { opacity: 1; }
        .enrich-link-input-row { display: flex; gap: 8px; align-items: center; }
        .enrich-type-selector { display: flex; gap: 4px; }
        .enrich-type-btn {
            width: 32px; height: 32px; border-radius: 6px; cursor: pointer; font-size: 14px;
            background: transparent; border: 1px solid var(--border-neutral); color: var(--text-disabled);
            display: flex; align-items: center; justify-content: center; transition: all 150ms ease;
        }
        .enrich-type-btn:hover { border-color: var(--text-disabled); }
        .enrich-type-btn.active { background: rgba(88,166,255,0.1); border-color: var(--blue); color: var(--blue); }
        .enrich-link-input { flex: 1; height: 36px; padding: 0 12px !important; font-size: 13px !important; }
        .enrich-link-title { height: 32px; padding: 0 12px !important; font-size: 12px !important; margin-top: 8px; }
        .enrich-add-btn {
            height: 36px; padding: 0 14px; border-radius: 8px; cursor: pointer; white-space: nowrap;
            background: rgba(88,166,255,0.08); border: 1px solid rgba(88,166,255,0.2);
            color: var(--blue); font-size: 12px; font-weight: 600; transition: all 150ms ease;
        }
        .enrich-add-btn:hover { background: rgba(88,166,255,0.16); }
        .enrich-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
        .enrich-chip {
            display: inline-flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: 6px;
            background: rgba(88,166,255,0.06); border: 1px solid rgba(88,166,255,0.12);
            font-size: 12px; color: var(--text-body); animation: chipIn 150ms ease-out;
        }
        .enrich-chip .ec-ico.t-map { color: var(--green); }
        .enrich-chip .ec-ico.t-url { color: var(--blue); }
        .enrich-chip .ec-ico.t-reference, .enrich-chip .ec-ico.t-file { color: var(--text-muted); }
        .enrich-chip .ec-val { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .enrich-chip .ec-x { color: var(--text-disabled); cursor: pointer; font-size: 14px; line-height: 1; }
        .enrich-chip .ec-x:hover { color: var(--red); }
        .enrich-chip.removing { animation: chipOut 150ms ease-in forwards; }
        @keyframes chipIn { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        @keyframes chipOut { from { transform: scale(1); opacity: 1; } to { transform: scale(0.8); opacity: 0; } }
        .enrich-build-list { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
        .enrich-build-item {
            display: flex; align-items: center; gap: 10px; padding: 6px 10px; border-radius: 8px;
            background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle);
            animation: chipIn 150ms ease-out;
        }
        .enrich-build-item.drag-over { border-color: var(--blue); background: rgba(88,166,255,0.06); }
        .enrich-build-item .ebi-grip { cursor: grab; color: var(--text-disabled); font-size: 12px; line-height: 1; }
        .enrich-build-item .ebi-box { width: 14px; height: 14px; border-radius: 4px; border: 1.5px solid var(--border-neutral); flex-shrink: 0; }
        .enrich-build-item .ebi-text { flex: 1; font-size: 13px; color: var(--text-body); }
        .enrich-build-item .ebi-x { color: var(--text-disabled); cursor: pointer; font-size: 14px; }
        .enrich-build-item .ebi-x:hover { color: var(--red); }

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
            border-radius: 20px; padding: 0; width: 600px; max-width: calc(100vw - 48px);
            max-height: calc(100vh - 80px);
            display: flex; flex-direction: column; overflow: hidden;
            position: relative; box-shadow: 0 64px 128px rgba(0,0,0,0.8);
            transform: scale(0.9) translateY(20px); transition: all 600ms cubic-bezier(0.16, 1, 0.3, 1);
            clip-path: circle(0% at var(--origin-x, 50%) var(--origin-y, 50%));
        }
        #modal-overlay.show .modal-card {
            transform: scale(1) translateY(0);
            clip-path: circle(150% at var(--origin-x, 50%) var(--origin-y, 50%));
        }
        .modal-close {
            position: absolute; top: 16px; right: 16px; width: 34px; height: 34px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
            background: rgba(255,255,255,0.06); color: var(--text-muted); border: 1px solid rgba(255,255,255,0.12);
            font-size: 18px; cursor: pointer; transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); z-index: 10;
        }
        .modal-close:hover {
            background: rgba(248, 81, 73, 0.9); color: #fff;
            transform: rotate(90deg) scale(1.1); border-color: transparent;
            box-shadow: 0 0 24px rgba(248, 81, 73, 0.5), 0 0 60px rgba(248, 81, 73, 0.15);
        }

        /* Mission Briefing — viewport-safe three-zone layout */
        #modal-content { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
        .brief-header { flex-shrink: 0; padding: 22px 56px 14px 26px; border-bottom: 1px solid var(--border-subtle); }
        .brief-h-label { font-size: 10px; font-weight: 500; letter-spacing: 2px; color: var(--text-disabled); text-transform: uppercase; }
        .brief-title { font-size: 21px; font-weight: 600; color: var(--text-hero); letter-spacing: -0.4px; margin: 8px 0 0; line-height: 1.3; word-break: break-word;
            display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
        .brief-badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-top: 10px; }
        .brief-deadline { margin-top: 10px; }
        .brief-body { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 18px 24px; -webkit-overflow-scrolling: touch; transition: box-shadow 150ms ease; }
        .brief-body::-webkit-scrollbar { width: 4px; }
        .brief-body::-webkit-scrollbar-track { background: transparent; }
        .brief-body::-webkit-scrollbar-thumb { background: var(--border-neutral); border-radius: 4px; }
        .brief-body::-webkit-scrollbar-thumb:hover { background: var(--text-disabled); }
        .brief-footer { flex-shrink: 0; padding: 14px 24px 16px; border-top: 1px solid var(--border-subtle); background: rgba(13,17,23,0.6); }
        .brief-meta { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-disabled); margin-top: 14px; }
        .brief-enrich-block { margin-bottom: 6px; }

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

        /* ─── PHASE 1: NEW BADGE TYPES ─────────────── */
        /* Map CLI priority names to badge styles */
        .badge.critical  { color: var(--red);   background: rgba(248,81,73,0.1);   border: 1px solid rgba(248,81,73,0.2); }
        .badge.strategic { color: var(--amber);  background: rgba(210,153,34,0.1);  border: 1px solid rgba(210,153,34,0.2); }
        .badge.noise     { color: var(--blue);   background: rgba(88,166,255,0.1);  border: 1px solid rgba(88,166,255,0.2); }
        .badge.purge     { color: #6E7681;        background: rgba(110,118,129,0.1); border: 1px solid rgba(110,118,129,0.2); }

        /* Duration badge */
        .duration-badge {
            background: rgba(88,166,255,0.08); border: 1px solid rgba(88,166,255,0.15);
            border-radius: 20px; padding: 2px 8px; font-size: 10px; color: var(--blue);
            font-family: 'DM Mono', monospace; flex-shrink: 0;
        }

        /* Postpone badge */
        .postpone-badge {
            border-radius: 20px; padding: 2px 8px; font-size: 10px; font-weight: 600;
            flex-shrink: 0;
        }
        .postpone-badge.mild  { background: rgba(210,153,34,0.08); border: 1px solid rgba(210,153,34,0.2); color: #D29922; }
        .postpone-badge.warn  { background: rgba(248,81,73,0.08);  border: 1px solid rgba(248,81,73,0.2);  color: #F85149; }

        /* Deadline row */
        .deadline-row {
            display: flex; align-items: center; gap: 6px; margin-top: 6px;
            font-size: 11px; font-family: 'DM Mono', monospace;
            transition: all 300ms ease-out;
        }
        .hard-tag {
            font-size: 10px; font-weight: 700; color: #F85149;
            border: 1px solid rgba(248,81,73,0.3); border-radius: 4px;
            padding: 1px 5px; flex-shrink: 0;
        }
        .overdue-chip {
            font-size: 9px; font-weight: 700; color: #F85149;
            background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3);
            border-radius: 4px; padding: 1px 6px; margin-left: auto; flex-shrink: 0;
        }

        /* ─── PRESSURE LEVELS ─────────────────────── */
        .task-card { transition: border-left-color 300ms ease-out, box-shadow 300ms ease-out, color 300ms ease-out; }
        .task-card.pressure-1 { border-left-color: #D29922; box-shadow: 0 0 12px rgba(210,153,34,0.08); }
        .task-card.pressure-2 { border-left-color: #D29922; box-shadow: 0 0 16px rgba(210,153,34,0.15); }
        .task-card.pressure-2 .task-title { color: #D29922; }
        .task-card.pressure-3 { border-left-color: #F85149; box-shadow: 0 0 20px rgba(248,81,73,0.2); animation: urgentBorder 1.5s ease-in-out infinite; }
        .task-card.pressure-3 .task-title { color: #F85149; }
        .task-card.overdue-card { background: rgba(248,81,73,0.04); border-left-color: #F85149; }
        .task-card.overdue-card .task-title { color: #F85149; }
        .task-card-wrap.hard-deadline-urgent::before {
            content: ''; display: block; height: 1px; margin-bottom: 2px;
            background: linear-gradient(90deg, transparent, #F85149, transparent);
            animation: urgentPulse 1.5s ease-in-out infinite;
        }

        @keyframes urgentPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        @keyframes urgentBorder { 0%, 100% { border-left-color: #F85149; } 50% { border-left-color: rgba(248,81,73,0.3); } }

        /* ─── SORT CONTROLS ───────────────────────── */
        .sort-controls { display: flex; align-items: center; gap: 8px; }
        .sort-label { font-size: 9px; font-weight: 700; color: var(--text-disabled); letter-spacing: 1.5px; }
        .sort-chip {
            font-size: 9px; font-weight: 700; letter-spacing: 1px; padding: 3px 8px;
            border: 1px solid var(--border-neutral); border-radius: 4px; background: transparent;
            color: var(--text-disabled); cursor: pointer; transition: all 150ms ease-out;
        }
        .sort-chip.active { background: rgba(88,166,255,0.1); border-color: var(--blue); color: var(--blue); }
        .sort-chip:hover:not(.active) { border-color: #6E7681; color: var(--text-body); }

        /* filter count badges */
        .chip-count {
            display: inline-block; background: rgba(255,255,255,0.1);
            border-radius: 10px; padding: 0 5px; font-size: 10px;
            margin-left: 4px; font-weight: 400;
        }

        /* ─── PRIORITY ALERT CARDS (Control Center) ─── */
        .alert-card {
            border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;
            border-left: 3px solid transparent;
        }
        .alert-card .alert-type { font-size: 10px; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px; }
        .alert-card .alert-title { font-size: 14px; font-weight: 500; color: var(--text-hero); margin-bottom: 2px; }
        .alert-card .alert-meta { font-size: 12px; color: var(--text-muted); }
        .alert-card.missed  { background: rgba(248,81,73,0.06); border-left-color: #F85149; }
        .alert-card.urgent  { background: rgba(248,81,73,0.04); border-left-color: #D29922; }
        .alert-card.deferred{ background: rgba(210,153,34,0.04); border-left-color: #D29922; }
        .alert-card.deferred-severe{ background: rgba(248,81,73,0.06); border-left-color: #F85149; }
        .alert-card.soft { background: rgba(139,148,158,0.04); border-left-color: #8B949E; }

        /* ─── RECOVERY MODE ───────────────────────── */
        #recovery-banner {
            display: none; height: 56px; align-items: center; justify-content: space-between;
            padding: 0 32px;
            background: linear-gradient(90deg, rgba(248,81,73,0.08) 0%, rgba(210,153,34,0.05) 100%);
            border-bottom: 1px solid rgba(248,81,73,0.2);
            flex-shrink: 0;
        }
        #recovery-banner.active { display: flex; }
        .recovery-badge { font-size: 11px; font-weight: 700; color: #F85149; letter-spacing: 2px; }
        .recovery-sub { font-size: 13px; color: var(--text-muted); margin-left: 12px; }
        .btn-exit-recovery {
            background: transparent; border: 1px solid rgba(248,81,73,0.3); color: #F85149;
            border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; transition: all 150ms ease;
        }
        .btn-exit-recovery:hover { background: rgba(248,81,73,0.08); }

        /* ═══ RECOVERY MODE — UI LAYER (entry points, dialogs, auto-trigger) ═══ */
        @keyframes recSlideDown { from { transform: translateY(-100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        @keyframes recSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
        @keyframes recScaleIn { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        @keyframes recFadeOut { to { opacity: 0; } }
        @keyframes recDot { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }

        /* Pre-recovery warning banner (5pm) */
        .rec-prewarn {
            height: 44px; background: rgba(210,153,34,0.06); border-bottom: 1px solid rgba(210,153,34,0.2);
            display: flex; align-items: center; padding: 0 24px; gap: 12px;
            animation: recSlideDown 300ms ease-out;
        }
        .rec-prewarn .rec-pw-mid { flex: 1; font-size: 13px; }
        .rec-pw-link { color: #D29922; font-size: 12px; font-weight: 500; background: transparent; border: none; text-decoration: underline; cursor: pointer; }
        .rec-pw-x { color: #6E7681; font-size: 16px; background: transparent; border: none; cursor: pointer; margin-left: 12px; }

        /* 6pm prompt bottom sheet */
        .rec-sheet { position: fixed; bottom: 0; left: 0; right: 0; max-height: 320px; background: #161B22;
            border-top: 1px solid rgba(210,153,34,0.3); border-radius: 20px 20px 0 0; padding: 24px 32px 32px;
            box-shadow: 0 -8px 40px rgba(0,0,0,0.5); z-index: 1000; animation: recSlideUp 350ms cubic-bezier(0.34,1.56,0.64,1); }
        .rec-sheet-handle { width: 40px; height: 4px; background: #30363D; border-radius: 4px; margin: 0 auto 20px; }

        /* Entry/exit confirmation dialog */
        .rec-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
            z-index: 1001; display: flex; align-items: center; justify-content: center; }
        .rec-dialog { width: 400px; max-width: 92vw; background: #161B22; border: 1px solid #21262D; border-radius: 16px; padding: 28px 28px 24px; text-align: center; }
        .rec-dialog .rec-d-icon { font-size: 32px; margin-bottom: 12px; }
        .rec-dialog .rec-d-title { font-size: 18px; font-weight: 400; color: #E6EDF3; }
        .rec-dialog .rec-d-desc { font-size: 13px; color: #8B949E; line-height: 1.6; margin-top: 8px; }
        .rec-d-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6E7681; margin-top: 16px; text-align: left; }
        .rec-preview-row { background: rgba(255,255,255,0.03); border: 1px solid #21262D; border-radius: 8px; padding: 8px 12px; margin-top: 8px;
            display: flex; align-items: center; gap: 10px; text-align: left; }
        .rec-pdot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .rec-pdot.high { background: var(--red); } .rec-pdot.medium { background: var(--amber); } .rec-pdot.low { background: var(--blue); }
        .rec-prow-title { flex: 1; font-size: 13px; color: #C9D1D9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .rec-prow-dur { font-size: 10px; color: var(--blue); font-family: var(--font-mono); }
        .rec-btn-primary { width: 100%; height: 46px; border-radius: 10px; cursor: pointer; margin-top: 20px; font-size: 14px; font-weight: 600;
            background: linear-gradient(135deg, rgba(210,153,34,0.15), rgba(248,81,73,0.1)); border: 1px solid rgba(210,153,34,0.4); color: #D29922; transition: all 150ms ease-out; }
        .rec-btn-primary:hover { background: linear-gradient(135deg, rgba(210,153,34,0.25), rgba(248,81,73,0.15)); border-color: rgba(210,153,34,0.6); transform: translateY(-1px); }
        .rec-btn-exit { background: rgba(248,81,73,0.08); border-color: rgba(248,81,73,0.3); color: #F85149; }
        .rec-btn-exit:hover { background: rgba(248,81,73,0.16); }
        .rec-btn-secondary { background: transparent; border: none; color: #6E7681; font-size: 12px; cursor: pointer; margin-top: 12px; width: 100%; }
        .rec-btn-secondary:hover { color: #8B949E; }
        .rec-btn-stay { color: #3FB950; }

        /* Entry point 2 — sidebar nav item */
        .rec-nav-item { display: flex; align-items: center; gap: 12px; padding: 8px 16px; cursor: pointer; color: #D29922;
            opacity: 0.7; border-left: 3px solid transparent; font-size: 14px; transition: all 150ms ease; }
        .rec-nav-item:hover { background: rgba(210,153,34,0.05); opacity: 1; border-left-color: #D29922; }
        .rec-nav-item.active { background: rgba(248,81,73,0.06); border-left-color: #F85149; color: #F85149; opacity: 1; }
        .rec-nav-dot { width: 6px; height: 6px; border-radius: 50%; background: #F85149; margin-left: auto; display: none; animation: recDot 2s ease-in-out infinite; }
        .rec-nav-item.active .rec-nav-dot { display: block; }

        /* Entry point 3 — right-panel salvage button */
        .rec-salvage-btn { width: 100%; height: 40px; background: rgba(210,153,34,0.06); border: 1px solid rgba(210,153,34,0.2);
            border-radius: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; cursor: pointer; margin-bottom: 10px;
            color: #D29922; font-size: 11px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase; transition: all 150ms ease-out; }
        .rec-salvage-btn:hover { background: rgba(210,153,34,0.12); border-color: rgba(210,153,34,0.4); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(210,153,34,0.15); }
        .rec-salvage-btn.active { background: rgba(248,81,73,0.08); border-color: rgba(248,81,73,0.3); color: #F85149; }

        /* Entry point 4 — priority alerts button */
        .rec-alerts-zone { border-top: 1px solid #21262D; margin-top: 12px; padding-top: 12px; }
        .rec-alerts-btn { width: 100%; height: 36px; background: transparent; border: 1px dashed rgba(210,153,34,0.3); border-radius: 8px;
            color: #D29922; font-size: 11px; font-weight: 500; letter-spacing: 1px; cursor: pointer; transition: all 150ms ease; }
        .rec-alerts-btn:hover { background: rgba(210,153,34,0.06); border-style: solid; }
        .rec-alerts-btn.active { color: #F85149; border-color: rgba(248,81,73,0.3); }

        /* Right-panel context box + post-recovery badge */
        .rec-context-box { background: rgba(210,153,34,0.05); border: 1px solid rgba(210,153,34,0.15); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; }
        .rec-context-box .rcb-t { font-size: 12px; color: #D29922; font-weight: 500; }
        .rec-context-box .rcb-s { font-size: 11px; color: #8B949E; margin-top: 2px; }
        .post-rec-badge { background: rgba(63,185,80,0.06); border: 1px solid rgba(63,185,80,0.15); border-radius: 8px; padding: 8px 12px;
            display: flex; align-items: center; gap: 8px; margin-top: 12px; }
        .post-rec-badge .prb-t { color: #3FB950; font-size: 12px; font-weight: 500; }
        .post-rec-badge .prb-s { color: #6E7681; font-size: 11px; }

        /* Celebration overlay */
        .rec-celebrate { position: fixed; inset: 0; background: rgba(63,185,80,0.03); display: flex; flex-direction: column;
            align-items: center; justify-content: center; pointer-events: none; z-index: 1002; animation: recFadeOut 500ms ease-out 2000ms forwards; }
        .rec-celebrate .rc-check { font-size: 48px; color: #3FB950; animation: recScaleIn 400ms cubic-bezier(0.34,1.56,0.64,1); }
        .rec-celebrate .rc-big { font-size: 22px; color: #3FB950; font-weight: 300; margin-top: 8px; }
        .rec-celebrate .rc-sub { font-size: 14px; color: #8B949E; margin-top: 4px; }

        /* Transformation 4 — FOCUS NOW badge + on-card complete button */
        .rec-focus-badge { background: rgba(210,153,34,0.1); border: 1px solid rgba(210,153,34,0.3); color: #D29922; border-radius: 4px;
            padding: 2px 8px; font-size: 9px; font-weight: 700; flex-shrink: 0; }
        .rec-card-complete { height: 32px; width: 100%; background: rgba(63,185,80,0.08); border: 1px solid rgba(63,185,80,0.2);
            border-radius: 6px; color: #3FB950; font-size: 12px; cursor: pointer; margin-top: 10px; transition: all 150ms ease; }
        .rec-card-complete:hover { background: rgba(63,185,80,0.16); }
        .recovery-priority-badge { background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.25); color: #F85149; border-radius: 4px; padding: 2px 8px; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; flex-shrink: 0; }
        .recovery-suppressed { opacity: 0.25; pointer-events: none; filter: blur(0.5px); transition: all 600ms ease-out; }
        .recovery-highlighted {
            border: 1px solid rgba(248,81,73,0.3) !important;
            box-shadow: 0 0 20px rgba(248,81,73,0.1) !important;
        }
        .recovery-priority-badge {
            font-size: 9px; font-weight: 700; color: #F85149;
            background: rgba(248,81,73,0.1); border: 1px solid rgba(248,81,73,0.3);
            border-radius: 4px; padding: 2px 8px; margin-left: auto;
        }

        /* ─── REMINDER TOASTS ─────────────────────── */
        #reminder-stack {
            position: fixed; bottom: 88px; right: 24px; z-index: 19000;
            display: flex; flex-direction: column; gap: 8px; align-items: flex-end;
        }
        .reminder-toast {
            width: 320px; background: #161B22; border: 1px solid #30363D;
            border-left: 3px solid var(--blue); border-radius: 12px; padding: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            transform: translateY(20px); opacity: 0;
            animation: toastIn 300ms ease-out forwards;
        }
        .reminder-toast.hard-reminder { border-left-color: #F85149; background: linear-gradient(135deg, #161B22 0%, rgba(248,81,73,0.03) 100%); }
        @keyframes toastIn { to { transform: translateY(0); opacity: 1; } }
        .toast-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .toast-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: var(--blue); }
        .toast-label.hard { color: #F85149; }
        .toast-close { font-size: 16px; color: #6E7681; cursor: pointer; background: none; border: none; line-height: 1; padding: 0; }
        .toast-title { font-size: 14px; font-weight: 500; color: var(--text-hero); margin-bottom: 4px; }
        .toast-deadline { font-size: 12px; margin-bottom: 4px; font-family: 'DM Mono', monospace; }
        .toast-meta { font-size: 11px; color: var(--text-muted); margin-bottom: 12px; }
        .toast-actions { display: flex; gap: 8px; }
        .btn-toast-focus {
            background: linear-gradient(135deg, #1F6FEB, #388BFD); border: none;
            border-radius: 6px; color: white; font-size: 12px; font-weight: 600;
            padding: 6px 14px; cursor: pointer; transition: all 150ms ease;
        }
        .btn-toast-dismiss {
            background: transparent; border: 1px solid #30363D;
            border-radius: 6px; color: #8B949E; font-size: 12px;
            padding: 6px 14px; cursor: pointer; transition: all 150ms ease;
        }
        .btn-toast-dismiss:hover { border-color: #6E7681; color: var(--text-body); }

        /* ─── TIMELINE TASK CHIPS ─────────────────── */
        .tl-chip {
            border-radius: 6px; padding: 6px 10px; margin-bottom: 4px;
            font-size: 12px; color: #C9D1D9; cursor: grab; border-left: 2px solid transparent;
            overflow: hidden; line-height: 1.3;
        }
        .tl-chip .tl-chip-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .tl-chip .tl-chip-meta { font-size: 10px; color: var(--text-muted); font-family: 'DM Mono', monospace; margin-top: 2px; }
        .tl-chip.p-critical { background: rgba(248,81,73,0.1);  border-left-color: #F85149; }
        .tl-chip.p-strategic{ background: rgba(210,153,34,0.1); border-left-color: #D29922; }
        .tl-chip.p-noise    { background: rgba(88,166,255,0.1); border-left-color: #58A6FF; }
        .tl-chip.p-high     { background: rgba(248,81,73,0.1);  border-left-color: #F85149; }
        .tl-chip.p-medium   { background: rgba(210,153,34,0.1); border-left-color: #D29922; }
        .tl-chip.p-low      { background: rgba(88,166,255,0.1); border-left-color: #58A6FF; }
        .col-mission-count  { font-size: 10px; color: var(--text-disabled); letter-spacing: 1.5px; font-weight: 700; margin-bottom: 4px; }

        /* ─── CREATE MISSION: NEW FIELDS ─────────── */
        .duration-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }
        .dur-pill {
            height: 36px; border-radius: 8px; font-size: 12px; font-weight: 500;
            background: #0D1117; border: 1px solid #30363D; color: #8B949E;
            cursor: pointer; transition: all 150ms ease-out; font-family: 'DM Mono', monospace;
        }
        .dur-pill:hover { border-color: #6E7681; color: var(--text-body); }
        .dur-pill.selected {
            background: rgba(88,166,255,0.1); border-color: var(--blue);
            color: var(--blue); transform: translateY(-1px);
            box-shadow: 0 0 12px rgba(88,166,255,0.15);
        }
        .deadline-input {
            width: 100%; height: 44px; background: #0D1117;
            border: 1px solid #30363D; border-radius: 10px; padding: 0 14px;
            color: var(--text-hero); font-size: 14px; outline: none;
            caret-color: var(--blue); transition: border-color 150ms ease;
        }
        .deadline-input:focus { border-color: var(--blue); }
        .deadline-parsed { font-size: 12px; margin-top: 6px; opacity: 0; transition: opacity 200ms ease-out; }
        .deadline-parsed.visible { opacity: 1; }
        .deadline-type-row { display: flex; gap: 12px; margin-top: 10px; }
        .dl-type-pill {
            flex: 1; height: 40px; border-radius: 8px; font-size: 12px; font-weight: 500;
            cursor: pointer; border: 1px solid #30363D; background: transparent;
            color: #8B949E; transition: all 150ms ease-out;
        }
        .dl-type-pill.soft.selected { background: rgba(88,166,255,0.08); border-color: var(--blue); color: var(--blue); }
        .dl-type-pill.hard.selected { background: rgba(248,81,73,0.08); border-color: #F85149; color: #F85149; box-shadow: 0 0 12px rgba(248,81,73,0.15); }
        .hard-warning { font-size: 11px; color: #F85149; opacity: 0.7; margin-top: 6px; display: none; }
        .hard-warning.visible { display: block; }

        /* ─── EPDO COMMAND MATRIX ─────────────── */
        .epdo-section {
            margin: 20px 0 0; padding: 20px; border-radius: 16px;
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
        }
        .epdo-label {
            font-size: 9px; font-weight: 800; letter-spacing: 2.5px;
            color: var(--text-disabled); margin-bottom: 14px;
        }
        .epdo-grid {
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
        }
        .epdo-btn {
            display: flex; align-items: center; gap: 10px;
            padding: 14px 16px; border-radius: 12px; cursor: pointer;
            font-size: 12px; font-weight: 700; letter-spacing: 1px;
            border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.02);
            color: var(--text-muted); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative; overflow: hidden;
        }
        .epdo-btn::before {
            content: ''; position: absolute; inset: 0; opacity: 0;
            transition: opacity 0.3s; border-radius: inherit;
        }
        .epdo-btn:hover { transform: translateY(-2px); }
        .epdo-btn:active { transform: translateY(0) scale(0.98); }
        .epdo-icon { font-size: 16px; flex-shrink: 0; }
        .epdo-text { flex: 1; }
        .epdo-key {
            font-size: 9px; font-family: var(--font-mono); padding: 2px 6px;
            border-radius: 4px; background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1); color: var(--text-disabled);
            line-height: 1;
        }
        .epdo-btn.execute {
            border-color: rgba(74,222,128,0.2); color: var(--emerald);
        }
        .epdo-btn.execute::before { background: rgba(74,222,128,0.08); }
        .epdo-btn.execute:hover {
            border-color: var(--emerald); background: rgba(74,222,128,0.1);
            box-shadow: 0 0 24px rgba(74,222,128,0.15), 0 8px 20px rgba(0,0,0,0.3);
        }
        .epdo-btn.postpone {
            border-color: rgba(210,153,34,0.2); color: var(--amber);
        }
        .epdo-btn.postpone::before { background: rgba(210,153,34,0.08); }
        .epdo-btn.postpone:hover {
            border-color: var(--amber); background: rgba(210,153,34,0.1);
            box-shadow: 0 0 24px rgba(210,153,34,0.15), 0 8px 20px rgba(0,0,0,0.3);
        }
        .epdo-btn.postpone.disabled {
            opacity: 0.3; cursor: not-allowed; pointer-events: none;
        }
        .epdo-btn.drop {
            border-color: rgba(248,81,73,0.15); color: var(--red);
        }
        .epdo-btn.drop::before { background: rgba(248,81,73,0.08); }
        .epdo-btn.drop:hover {
            border-color: var(--red); background: rgba(248,81,73,0.1);
            box-shadow: 0 0 24px rgba(248,81,73,0.15), 0 8px 20px rgba(0,0,0,0.3);
        }
        .epdo-btn.offload {
            border-color: rgba(163,113,247,0.2); color: var(--ai-purple);
        }
        .epdo-btn.offload::before { background: rgba(163,113,247,0.08); }
        .epdo-btn.offload:hover {
            border-color: var(--ai-purple); background: rgba(163,113,247,0.1);
            box-shadow: 0 0 24px rgba(163,113,247,0.15), 0 8px 20px rgba(0,0,0,0.3);
        }
        .epdo-sub-panel {
            margin-top: 12px; padding: 16px; border-radius: 12px;
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
            animation: subPanelIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes subPanelIn {
            0% { opacity: 0; transform: translateY(-8px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        .epdo-sub-label {
            font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
            color: var(--text-disabled); margin-bottom: 10px;
        }
        .postpone-options { display: flex; gap: 8px; flex-wrap: wrap; }
        .postpone-opt {
            flex: 1; min-width: 80px; padding: 10px 12px; border-radius: 10px;
            background: rgba(210,153,34,0.05); border: 1px solid rgba(210,153,34,0.15);
            color: var(--amber); font-size: 12px; font-weight: 600; cursor: pointer;
            font-family: 'DM Mono', monospace;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .postpone-opt:hover {
            background: rgba(210,153,34,0.15); border-color: var(--amber);
            transform: translateY(-2px); box-shadow: 0 4px 16px rgba(210,153,34,0.2);
        }
        .postpone-opt:active { transform: translateY(0) scale(0.97); }
        .epdo-btn-util {
            flex: 1; padding: 12px; border-radius: 10px; font-size: 12px; font-weight: 600;
            cursor: pointer; transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.02);
            color: var(--text-muted);
        }
        .epdo-btn-util.complete {
            border-color: rgba(74,222,128,0.2); color: var(--emerald);
        }
        .epdo-btn-util.complete:hover {
            background: rgba(74,222,128,0.1); border-color: var(--emerald);
            box-shadow: 0 0 16px rgba(74,222,128,0.15);
        }
        .epdo-btn-util.ai {
            border-color: rgba(163,113,247,0.2); color: var(--ai-purple);
        }
        .epdo-btn-util.ai:hover {
            background: rgba(163,113,247,0.1); border-color: var(--ai-purple);
            box-shadow: 0 0 16px rgba(163,113,247,0.15);
        }
        .modal-deadline {
            margin-bottom: 16px; font-family: 'DM Mono', monospace; font-size: 13px;
            padding: 10px 14px; border-radius: 10px;
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
        }
        .modal-meta-row {
            display: flex; justify-content: space-between; margin-top: 16px;
            font-size: 11px; color: var(--text-disabled); font-family: 'DM Mono', monospace;
            padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.04);
        }

        /* ─── OMNIBAR DEADLINE TYPE ──────────── */
        .omni-dl-type-row { display: flex; gap: 6px; margin-top: 8px; }
        .omni-dl-type {
            flex: 1; height: 30px; border-radius: 6px; font-size: 10px; font-weight: 600;
            cursor: pointer; border: 1px solid #30363D; background: transparent;
            color: #8B949E; transition: all 150ms ease-out;
        }
        .omni-dl-type.soft.selected { background: rgba(88,166,255,0.08); border-color: var(--blue); color: var(--blue); }
        .omni-dl-type.hard.selected { background: rgba(248,81,73,0.08); border-color: #F85149; color: #F85149; }

        /* ─── PREMIUM MODAL ENHANCEMENTS ─────── */
        .modal-card {
            background: linear-gradient(165deg, rgba(13, 17, 23, 0.92), rgba(6, 10, 15, 0.98));
            backdrop-filter: blur(40px) saturate(150%); -webkit-backdrop-filter: blur(40px) saturate(150%);
            border: 1px solid rgba(88, 166, 255, 0.12);
            box-shadow: 0 64px 128px rgba(0,0,0,0.8), 0 0 80px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
        }
        .modal-card::before {
            content: ''; position: absolute; top: -1px; left: 15%; right: 15%; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(88,166,255,0.4), transparent);
            pointer-events: none;
        }
        .deploy-modal {
            box-shadow: -24px 0 64px rgba(0,0,0,0.6), inset 1px 0 0 rgba(255,255,255,0.04);
        }

        /* ─── DROP CONFIRMATION MODAL ────────── */
        .drop-overlay {
            position: fixed; inset: 0; z-index: 999999;
            background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
            display: flex; align-items: center; justify-content: center;
            opacity: 0; pointer-events: none; transition: opacity 0.3s ease;
        }
        .drop-overlay.active { opacity: 1; pointer-events: all; }
        .drop-modal {
            background: linear-gradient(165deg, rgba(20, 14, 14, 0.98), rgba(10, 6, 6, 0.99));
            border: 1px solid rgba(248, 81, 73, 0.25); border-radius: 20px;
            padding: 36px; max-width: 420px; width: 90%;
            box-shadow: 0 0 80px rgba(248,81,73,0.1), 0 40px 80px rgba(0,0,0,0.8);
            transform: scale(0.9) translateY(20px); transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .drop-overlay.active .drop-modal { transform: scale(1) translateY(0); }
        .drop-modal::before {
            content: ''; position: absolute; top: -1px; left: 20%; right: 20%; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(248,81,73,0.5), transparent);
        }
        .drop-modal-icon { font-size: 40px; text-align: center; margin-bottom: 16px; }
        .drop-modal-title { font-size: 18px; font-weight: 700; color: var(--red); text-align: center; margin-bottom: 8px; letter-spacing: 1px; }
        .drop-modal-msg { font-size: 13px; color: var(--text-body); text-align: center; line-height: 1.6; margin-bottom: 24px; }
        .drop-modal-task { font-size: 15px; font-weight: 600; color: var(--text-hero); text-align: center; margin-bottom: 16px; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); }
        .drop-modal-actions { display: flex; gap: 10px; }
        .drop-btn-confirm {
            flex: 1; padding: 14px; border-radius: 12px; font-size: 13px; font-weight: 700;
            cursor: pointer; border: 1px solid rgba(248,81,73,0.4); background: rgba(248,81,73,0.1);
            color: var(--red); letter-spacing: 1px; transition: all 0.25s;
        }
        .drop-btn-confirm:hover { background: rgba(248,81,73,0.25); box-shadow: 0 0 20px rgba(248,81,73,0.2); }
        .drop-btn-cancel {
            flex: 1; padding: 14px; border-radius: 12px; font-size: 13px; font-weight: 600;
            cursor: pointer; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03);
            color: var(--text-muted); transition: all 0.25s;
        }
        .drop-btn-cancel:hover { background: rgba(255,255,255,0.06); color: var(--text-body); }

        /* ─── CUSTOM POSTPONE INPUT ──────────── */
        .postpone-custom-row {
            margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.04);
        }
        .postpone-reason {
            width: 100%; margin-top: 10px; padding: 10px 14px; border-radius: 10px;
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
            color: var(--text-body); font-size: 12px; font-family: var(--font-body);
            resize: none; outline: none; transition: border-color 0.2s;
        }
        .postpone-reason:focus { border-color: rgba(210,153,34,0.3); }
        .postpone-reason::placeholder { color: var(--text-disabled); }

        /* ─── MISSION TYPE SWITCHER ──────────── */
        .mission-type-switcher {
            display: flex; background: rgba(0,0,0,0.3); border-radius: 12px;
            padding: 4px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.05);
        }
        .type-btn {
            flex: 1; padding: 10px; text-align: center; font-size: 11px; font-weight: 700;
            color: var(--text-muted); cursor: pointer; border-radius: 8px; transition: all 0.3s;
            letter-spacing: 1px; user-select: none;
        }
        .type-btn.active { background: rgba(88,166,255,0.15); color: var(--blue); box-shadow: 0 0 12px rgba(88,166,255,0.2); }
        
        /* ─── EVENT UI ──────────── */
        .event-mode-only { display: none; }
        .task-mode-only { display: block; }
        
        .timeline-slider-wrap {
            position: relative; height: 36px; background: rgba(255,255,255,0.03);
            border-radius: 8px; margin-top: 12px; border: 1px solid rgba(255,255,255,0.05);
            user-select: none; touch-action: none; cursor: crosshair;
        }
        .timeline-slider-track {
            position: absolute; left: 0; top: 0; bottom: 0; width: 100%;
            display: flex; pointer-events: none; opacity: 0.2;
        }
        .timeline-slider-tick { flex: 1; border-right: 1px solid var(--text-muted); }
        .timeline-slider-selection {
            position: absolute; top: 0; bottom: 0; background: rgba(163,113,247,0.3);
            border: 1px solid var(--ai-purple); border-radius: 4px; pointer-events: none;
            display: none; box-shadow: inset 0 0 10px rgba(163,113,247,0.4);
        }
        .time-labels {
            display: flex; justify-content: space-between; margin-top: 6px;
            font-size: 9px; color: var(--text-disabled); font-family: var(--font-mono);
        }
        .fallback-date {
            margin-top: 8px; padding: 10px; border-radius: 8px; font-family: var(--font-mono);
            background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
            color: var(--text-body); font-size: 12px; width: 100%; box-sizing: border-box; outline: none;
        }
        .fallback-date::-webkit-calendar-picker-indicator { filter: invert(1); cursor: pointer; opacity: 0.6; }
    </style>
</head>
<body class="state-idle">
    <div id="threejs-canvas" style="position: fixed; inset: 0; z-index: -2; pointer-events: none; opacity: 1;"></div>
    <div id="bg-parallax"></div>
    <div id="bg-grid"></div>
    <div id="hud-scanlines"></div>
    <div id="toast">Protocol Offline</div>

    <!-- DROP CONFIRMATION MODAL -->
    <div id="drop-overlay" class="drop-overlay">
        <div class="drop-modal">
            <div class="drop-modal-icon">✕</div>
            <div class="drop-modal-title">DROP MISSION</div>
            <div class="drop-modal-msg">This action is permanent and cannot be undone. Are you sure you want to drop this mission?</div>
            <div id="drop-modal-task-name" class="drop-modal-task">Mission Name</div>
            <div class="drop-modal-actions">
                <button id="drop-btn-cancel" class="drop-btn-cancel">CANCEL</button>
                <button id="drop-btn-confirm" class="drop-btn-confirm">PURGE</button>
            </div>
        </div>
    </div>

    <!-- FLOATING OMNIBAR OVERLAY (Ctrl+K from any view) -->
    <div id="omnibar-overlay" class="omnibar-overlay">
        <div class="omnibar-container">
            <button id="omnibar-close" onclick="document.getElementById('omnibar-overlay').classList.remove('active')" style="position:absolute;top:-14px;right:-14px;width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:var(--text-muted);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:10;transition:all 0.3s;backdrop-filter:blur(8px);" onmouseover="this.style.background='rgba(248,81,73,0.9)';this.style.color='#fff';this.style.borderColor='transparent';this.style.boxShadow='0 0 20px rgba(248,81,73,0.4)';this.style.transform='rotate(90deg) scale(1.1)'" onmouseout="this.style.background='rgba(255,255,255,0.06)';this.style.color='var(--text-muted)';this.style.borderColor='rgba(255,255,255,0.15)';this.style.boxShadow='none';this.style.transform='scale(1)'">&times;</button>
            <input type="text" id="omnibar-input" placeholder="Capture a thought..." autocomplete="off">
            <div id="omnibar-time-section" style="margin-top:12px;padding:14px 16px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;">
                <div style="font-size:9px;font-weight:700;color:var(--text-disabled);letter-spacing:1.5px;margin-bottom:8px;">TIME BLOCK</div>
                <div style="display:flex;gap:6px;" id="omni-dur-grid">
                    <button class="dur-pill omni-dur" data-dur="15m" style="flex:1;height:32px;font-size:11px;">15m</button>
                    <button class="dur-pill omni-dur" data-dur="30m" style="flex:1;height:32px;font-size:11px;">30m</button>
                    <button class="dur-pill omni-dur" data-dur="1h" style="flex:1;height:32px;font-size:11px;">1h</button>
                    <button class="dur-pill omni-dur" data-dur="2h" style="flex:1;height:32px;font-size:11px;">2h</button>
                </div>
                <div style="margin-top:10px;">
                    <div style="font-size:9px;font-weight:700;color:var(--text-disabled);letter-spacing:1.5px;margin-bottom:6px;">DEADLINE</div>
                    <input type="text" id="omni-deadline" class="deadline-input" style="height:36px;font-size:12px;border-radius:8px;" placeholder="e.g. tomorrow 3pm, Friday, in 2 hours" autocomplete="off">
                    <div id="omni-dl-parsed" style="font-size:11px;margin-top:4px;opacity:0;transition:opacity 0.2s;"></div>
                    <div class="omni-dl-type-row" id="omni-dl-type-row" style="display:none;">
                        <button class="omni-dl-type soft selected" id="omni-dl-soft" onclick="setOmniDeadlineType('soft')">Soft</button>
                        <button class="omni-dl-type hard" id="omni-dl-hard" onclick="setOmniDeadlineType('hard')">Hard ⚠</button>
                    </div>
                </div>
            </div>
            <div class="omnibar-hints">
                <span class="omnibar-hint">Use <kbd>#tag</kbd> and <kbd>!h</kbd> <kbd>!m</kbd> <kbd>!l</kbd> for priority</span>
                <span class="omnibar-hint"><kbd>Enter</kbd> to save &middot; <kbd>Esc</kbd> to close</span>
            </div>
        </div>
    </div>

    <!-- New Top Progress Bar -->
    <div id="focus-progress-bar" class="focus-progress-bar"></div>

    <!-- RECOVERY MODE BANNER -->
    <div id="recovery-banner">
        <div style="display:flex; align-items:center;">
            <span class="recovery-badge">⚡ RECOVERY MODE ACTIVE</span>
            <span class="recovery-sub">· Today's been rough. Let's salvage it.</span>
        </div>
        <button class="btn-exit-recovery" id="btn-exit-recovery">EXIT RECOVERY</button>
    </div>

    <!-- REMINDER TOAST STACK -->
    <div id="reminder-stack"></div>

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
            <div class="rec-nav-item" id="rec-nav-item" onclick="tfRecSidebarClick()" title="Activate Recovery Mode">
                <span class="nav-icon">⚡</span> <span id="rec-nav-text">Recovery</span>
                <span class="rec-nav-dot"></span>
            </div>

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

                <!-- TWO-COLUMN CONTROL CENTER: left = path · now · today's missions | right = alerts · insight · snapshot -->
                <div style="display: grid; grid-template-columns: 1.3fr 1fr; gap: 24px; margin-top: 24px; align-items: start;">

                <!-- LEFT COLUMN -->
                <div style="display:flex; flex-direction:column; gap:16px; min-width:0;">

                <!-- 1. TODAY'S EXECUTION PATH (top priority) -->
                <div class="mission-panel" id="cc-path-panel" style="padding: 24px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div class="section-label" style="margin:0; font-size:10px; letter-spacing:2px;">TODAY'S EXECUTION PATH</div>
                        <div id="cc-path-meta" style="font-size:10px; color:var(--text-disabled); font-family:var(--font-mono);"></div>
                    </div>
                    <div id="cc-path-body" style="margin-top:16px; display:flex; flex-direction:column; gap:12px;">
                        <!-- Filled by JS via /api/path -->
                    </div>
                    <button id="cc-path-regen" onclick="regeneratePath()"
                        style="margin-top:16px; width:100%; background:transparent; border:1px dashed #30363D; color:#6E7681; font-size:11px; padding:10px; border-radius:8px; cursor:pointer; font-family:'DM Mono',monospace; letter-spacing:1px;">
                        ↻ REGENERATE PATH
                    </button>
                </div>

                <!-- 2. NOW WINDOW (what to do right now) -->
                <div id="cc-now"></div>

                <!-- left-column stack continues: path · now · today's missions -->
                    
                    <!-- TODAY'S MISSIONS -->
                    <div class="mission-panel" style="padding: 24px;">
                        <div id="cc-approaching-banner" style="margin-bottom: 12px; padding: 10px; border-radius: 8px; font-weight: 700; font-size: 12px; display: none; align-items: center; gap: 8px;"></div>
                        <div class="section-label">TODAY'S MISSIONS</div>
                        <div id="cc-upcoming" style="min-height: 120px; color: var(--text-muted); font-size: 12px; display: flex; flex-direction: column; gap: 8px; margin-top: 16px;">
                            <!-- Filled by JS -->
                        </div>
                    </div>

                </div><!-- /LEFT COLUMN -->

                <!-- RIGHT COLUMN -->
                <div style="display:flex; flex-direction:column; gap:16px; min-width:0;">

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
                        <!-- Phase 1: Overdue + Deferred row -->
                        <div style="display:flex; gap:24px; margin-top:16px; padding-top:12px; border-top:1px solid var(--border-subtle);">
                            <div>
                                <div style="font-size:10px; color:var(--text-disabled); letter-spacing:1.5px; text-transform:uppercase; margin-bottom:4px;">OVERDUE</div>
                                <div id="cc-overdue-count" style="font-size:18px; font-weight:700; color:#F85149; font-family:var(--font-mono);">0</div>
                            </div>
                            <div>
                                <div style="font-size:10px; color:var(--text-disabled); letter-spacing:1.5px; text-transform:uppercase; margin-bottom:4px;">DEFERRED</div>
                                <div id="cc-deferred-count" style="font-size:18px; font-weight:700; color:#D29922; font-family:var(--font-mono);">0</div>
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
                </div><!-- /RIGHT COLUMN -->

                </div><!-- /grid -->
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
                        <div class="filter-chip active" id="fc-all" onclick="filterTasks('all', this)">ALL<span class="chip-count" id="fc-count-all">0</span></div>
                        <div class="filter-chip" id="fc-high" onclick="filterTasks('high', this)">HIGH-THREAT<span class="chip-count" id="fc-count-high">0</span></div>
                        <div class="filter-chip" id="fc-medium" onclick="filterTasks('medium', this)">STABLE<span class="chip-count" id="fc-count-medium">0</span></div>
                        <div class="filter-chip" id="fc-low" onclick="filterTasks('low', this)">ROUTINE<span class="chip-count" id="fc-count-low">0</span></div>
                    </div>

                    <div class="section-label" style="font-size:9px; margin:20px 0 12px;">SIGNAL DISCOVERY (TAGS)</div>
                    <div id="tag-signal-discovery" class="filter-hud" style="flex-wrap:wrap; margin:0; gap:8px;">
                        <!-- Dynamic Signals -->
                    </div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin: 32px 0 16px;">
                    <div class="section-label" style="font-size:10px; margin:0; letter-spacing:3px;">PRIORITY SIGNALS</div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <div id="header-task-count" style="font-size:10px; color:var(--text-disabled); font-family:var(--font-mono);">0 ACTIVE</div>
                        <div class="sort-controls">
                            <span class="sort-label">SORT BY:</span>
                            <button class="sort-chip active" id="sort-urgency" onclick="setSortMode('urgency', this)">URGENCY ▾</button>
                            <button class="sort-chip" id="sort-priority" onclick="setSortMode('priority', this)">PRIORITY</button>
                            <button class="sort-chip" id="sort-created" onclick="setSortMode('created', this)">CREATED</button>
                        </div>
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
                            <div style="padding:12px; border-left:2px solid var(--green); background:rgba(255,255,255,0.02); font-size:12px;">Your real behavioral telemetry is live in the <strong>Analytics</strong> tab — Time Integrity Score, patterns, streaks and recovery history, computed from how you actually work.</div>
                            <div style="padding:12px; border-left:2px solid var(--blue); background:rgba(255,255,255,0.02); font-size:12px;">CLI: <code>taskflow stats</code>, <code>taskflow heatmap</code>, <code>taskflow rescue</code>, <code>taskflow path</code>.</div>
                            <div style="padding:12px; border-left:2px solid var(--ai-purple); background:rgba(255,255,255,0.02); font-size:12px;">The adaptive AI layer (predictive scheduling, natural-language coaching) arrives in <strong>Phase 3</strong>.</div>
                        </div>
                    </div>
                    
                    <!-- Suggestions -->
                    <div class="mission-panel" style="padding:32px; background:rgba(163, 113, 247, 0.05); border-color:rgba(163, 113, 247, 0.2);">
                        <div class="section-label" style="color:var(--ai-purple);">AI ADVISORY</div>
                        <div id="intel-advisory" style="margin-top:20px; font-size:13px; line-height:1.6; color:var(--text-body);">
                            <div style="margin-bottom:16px;"><span style="color:var(--ai-purple);">✦</span> TaskFlow keeps its intelligence <strong>honest</strong>: every number you see is computed from your own logged behavior — never invented.</div>
                            <div><span style="color:var(--ai-purple);">✦</span> Once you have a few days of history, the Analytics tab will surface your peak hour, most-avoided category, and start-time drift automatically.</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW: ANALYTICS -->
        <div id="view-stats" class="view-content hidden">
            <div style="max-width: 900px; margin: 0 auto; width: 100%;">
                <div class="section-label" style="text-align:center; margin-bottom: 24px;">PERFORMANCE TELEMETRY</div>

                <div id="stats-building" style="display:none; text-align:center; color:var(--text-muted); font-size:13px; margin-bottom:24px;"></div>

                <div id="stats-content">
                    <!-- Section 1: TIME INTEGRITY gauge + Section 2: WEEK OVERVIEW -->
                    <div style="display:grid; grid-template-columns: 280px 1fr; gap:24px; margin-bottom:24px;">
                        <div class="mission-panel" style="padding:24px; text-align:center;">
                            <div class="section-label" style="margin:0 0 12px;">TIME INTEGRITY SCORE</div>
                            <svg width="180" height="180" viewBox="0 0 180 180" style="margin:0 auto; display:block;">
                                <circle cx="90" cy="90" r="78" fill="none" stroke="var(--border-neutral)" stroke-width="10"></circle>
                                <circle id="tis-ring" cx="90" cy="90" r="78" fill="none" stroke="#3FB950" stroke-width="10"
                                        stroke-linecap="round" stroke-dasharray="490" stroke-dashoffset="490"
                                        transform="rotate(-90 90 90)" style="transition:stroke-dashoffset 0.8s ease, stroke 0.4s;"></circle>
                                <text id="tis-num" x="90" y="86" text-anchor="middle" font-family="var(--font-mono)" font-size="48" font-weight="300" fill="var(--text-hero)">—</text>
                                <text id="tis-sub" x="90" y="112" text-anchor="middle" font-size="11" fill="var(--text-disabled)">7-day avg</text>
                            </svg>
                            <div id="tis-trend" style="margin-top:10px; font-size:12px;">—</div>
                            <div id="tis-bestworst" style="margin-top:6px; font-size:11px; color:var(--text-disabled);"></div>
                        </div>
                        <div class="mission-panel" style="padding:24px;">
                            <div class="section-label" style="margin:0 0 8px;">WEEK OVERVIEW</div>
                            <div id="tis-bars" style="height:180px; display:flex; align-items:flex-end; gap:10px; padding-top:20px;"></div>
                        </div>
                    </div>

                    <!-- Section 2.5: DAY OF WEEK PATTERNS (S14-F) -->
                    <div class="mission-panel" style="padding:20px; margin-bottom:24px;">
                        <div class="section-label" style="margin:0 0 16px; letter-spacing:2px;">DAY OF WEEK PATTERNS</div>
                        <div id="dow-bars" style="display:flex; flex-direction:column; gap:8px;"></div>
                        <div id="dow-chips" style="display:flex; gap:12px; margin-top:16px;"></div>
                    </div>

                    <!-- Section 3: EXECUTION BREAKDOWN -->
                    <div class="mission-panel" style="padding:24px; margin-bottom:24px;">
                        <div class="section-label" style="margin:0 0 16px;">EXECUTION BREAKDOWN</div>
                        <div id="stats-chips" style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px;"></div>
                    </div>

                    <!-- Section 4: PATTERNS + Section 5: RECOVERY HISTORY -->
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px;">
                        <div class="mission-panel" style="padding:24px;">
                            <div class="section-label" style="margin:0 0 16px;">PATTERNS</div>
                            <div id="stats-patterns" style="font-size:13px; color:var(--text-body); display:flex; flex-direction:column; gap:12px;"></div>
                        </div>
                        <div class="mission-panel" style="padding:24px;">
                            <div class="section-label" style="margin:0 0 16px;">RECOVERY HISTORY</div>
                            <div id="stats-recovery" style="font-size:12px; color:var(--text-muted); display:flex; flex-direction:column; gap:8px;"></div>
                        </div>
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
            <div class="rec-context-box" id="rec-context-box" style="display:none;">
                <div class="rcb-t">Recovery in progress.</div>
                <div class="rcb-s">Complete your focus tasks to exit.</div>
            </div>
            <div class="section-label">EXECUTION XP</div>
            <div style="height:6px; background:var(--bg-surface); border-radius:3px; overflow:hidden; margin-bottom:8px;">
                <div id="xp-fill" style="width:40%; height:100%; background:var(--blue); transition:width 1s ease-out;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:700; color:var(--text-disabled);">
                <span>RANK: 01</span>
                <span id="xp-text">40 / 100 XP</span>
            </div>
            <div class="post-rec-badge" id="post-rec-badge" style="display:none;">
                <span style="color:#3FB950;font-size:14px;">✓</span>
                <div>
                    <div class="prb-t">Day recovered.</div>
                    <div class="prb-s" id="post-rec-badge-sub"></div>
                </div>
            </div>
            <div class="rec-salvage-btn" id="rec-salvage-btn" onclick="tfRecSalvageClick()">
                <span style="font-size:12px;">⚡</span> <span id="rec-salvage-text">SALVAGE MY DAY</span>
            </div>
            <button class="btn-deploy btn-execute" onclick="toggleCreateMission()" style="margin-top:20px; font-size:12px; font-weight:700; background: linear-gradient(135deg, rgba(88,166,255,0.15), rgba(88,166,255,0.05)); color: var(--blue); border: 1px solid rgba(88,166,255,0.2); width:100%; transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.2);">+ CREATE MISSION</button>
        </div>
    </aside>

    <div id="deploy-modal-overlay" class="deploy-modal-overlay">
        <div class="deploy-modal">
            <div class="dm-header">
                <div class="dm-header-top">
                    <span class="dm-title-label">New Mission</span>
                    <div class="close-modal" onclick="toggleCreateMission()">×</div>
                </div>
                <div class="dm-dots">
                    <span class="dm-dot filled" id="dm-dot-1"></span>
                    <span class="dm-dot" id="dm-dot-2"></span>
                    <span class="dm-dot" id="dm-dot-3"></span>
                </div>
            </div>
            <div class="dm-body" id="dm-body">

            <div class="mission-type-switcher">
                <div class="type-btn active" id="btn-type-task" onclick="setMissionType('Task')">🧩 TASK (FLEXIBLE)</div>
                <div class="type-btn" id="btn-type-event" onclick="setMissionType('Event')">📅 EVENT (TIME-LOCKED)</div>
            </div>
            
            <div class="flex-row">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">OBJECTIVE</label>
                    <input type="text" id="mission-title" class="input-system" placeholder="Enter tactical objective..." autocomplete="off">
                </div>
            </div>
            <div class="flex-row task-mode-only" style="margin-top:24px;">
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

            <!-- TASK MODE: DURATION -->
            <div class="flex-row task-mode-only" style="margin-top:24px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px; font-weight:500; letter-spacing:2px; text-transform:uppercase;">ESTIMATED DURATION</label>
                    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:8px;">
                        <button class="pill-btn-small" data-dur="15m" onclick="selectDurationPill(this,'15m')">15m</button>
                        <button class="pill-btn-small" data-dur="30m" onclick="selectDurationPill(this,'30m')">30m</button>
                        <button class="pill-btn-small" data-dur="1h"  onclick="selectDurationPill(this,'1h')">1h</button>
                        <button class="pill-btn-small" data-dur="2h"  onclick="selectDurationPill(this,'2h')">2h</button>
                        <button class="pill-btn-small" data-dur="3h"  onclick="selectDurationPill(this,'3h')">3h</button>
                        <button class="pill-btn-small" data-dur="4h+" onclick="selectDurationPill(this,'4h+')">4h+</button>
                    </div>
                    <input type="hidden" id="mission-duration" value="">
                </div>
            </div>

            <!-- TASK MODE: DEADLINE -->
            <div class="flex-row task-mode-only" style="margin-top:24px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">DEADLINE (OPTIONAL)</label>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <input type="text" id="mission-deadline" class="deadline-input"
                               placeholder="e.g. tomorrow 3pm, Friday, in 2 hours" autocomplete="off" style="flex:1;">
                        <div style="position:relative; width:42px; height:42px; background:rgba(255,255,255,0.05); border:1px solid var(--border-neutral); border-radius:8px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Pick a date manually">
                            <span style="font-size:16px;">📅</span>
                            <input type="date" id="mission-deadline-fallback" style="position:absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer;" onchange="document.getElementById('mission-deadline').value = this.value; document.getElementById('mission-deadline').dispatchEvent(new Event('input'));">
                        </div>
                    </div>
                    <div style="display:flex; gap:8px; margin-top:8px; margin-bottom:8px; flex-wrap:wrap;">
                        <button class="pill-btn-small" data-dl-preset="Today 6pm" onclick="selectDeadlinePill(this,'Today 6pm')">Today 6pm</button>
                        <button class="pill-btn-small" data-dl-preset="Tomorrow 9am" onclick="selectDeadlinePill(this,'Tomorrow 9am')">Tomorrow 9am</button>
                        <button class="pill-btn-small" data-dl-preset="Friday" onclick="selectDeadlinePill(this,'Friday')">Friday</button>
                    </div>
                    <div class="deadline-parsed" id="deadline-parsed-display"></div>
                    <div id="deadline-type-section" style="display:none;">
                        <div class="deadline-type-row">
                            <button class="dl-type-pill soft selected" id="dl-soft" onclick="setDeadlineType('soft')">🔵 Soft — flexible</button>
                            <button class="dl-type-pill hard" id="dl-hard" onclick="setDeadlineType('hard')">🔴 Hard — critical</button>
                        </div>
                        <div class="hard-warning" id="hard-warning">⚠ Hard deadlines trigger strong alerts if missed.</div>
                    </div>
                </div>
            </div>

            <!-- EVENT MODE: DATE & TIME SELECTOR -->
            <div class="flex-row event-mode-only" style="margin-top:24px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">EVENT DATE</label>
                    <input type="date" id="event-date" class="fallback-date">
                </div>
            </div>
            <div class="flex-row event-mode-only" style="margin-top:16px;">
                <div class="mission-field" style="width:100%;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                        <label class="section-label" style="font-size:9px;">TIMELINE BLOCK</label>
                        <div id="event-time-display" style="font-family:var(--font-mono); font-size:11px; color:var(--ai-purple); font-weight:700;">Drag to select</div>
                    </div>
                    <div class="timeline-slider-wrap" id="timeline-slider">
                        <div class="timeline-slider-track">
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                            <div class="timeline-slider-tick"></div><div class="timeline-slider-tick"></div>
                        </div>
                        <div class="timeline-slider-selection" id="timeline-selection"></div>
                    </div>
                    <div class="time-labels">
                        <span>8 AM</span><span>11 AM</span><span>2 PM</span><span>5 PM</span><span>8 PM</span>
                    </div>
                    <div style="display:flex; gap:12px; margin-top:12px; align-items:center;">
                        <div style="flex:1;">
                            <label class="section-label" style="font-size:8px; margin-bottom:4px;">START TIME</label>
                            <input type="text" id="event-start-time" class="input-system" placeholder="e.g. 8:45 AM" autocomplete="off" style="font-family:var(--font-mono); font-size:13px; text-align:center;">
                        </div>
                        <div style="color:var(--text-disabled); font-size:16px; margin-top:16px;">→</div>
                        <div style="flex:1;">
                            <label class="section-label" style="font-size:8px; margin-bottom:4px;">END TIME</label>
                            <input type="text" id="event-end-time" class="input-system" placeholder="e.g. 2:10 PM" autocomplete="off" style="font-family:var(--font-mono); font-size:13px; text-align:center;">
                        </div>
                    </div>
                    <div id="event-duration-display" style="margin-top:10px; padding:8px 12px; background:rgba(163,113,247,0.08); border:1px solid rgba(163,113,247,0.15); border-radius:8px; font-family:var(--font-mono); font-size:12px; color:var(--ai-purple); text-align:center; display:none;">
                        <span style="opacity:0.6;">DURATION:</span> <span id="event-duration-value">—</span>
                    </div>
                </div>
            </div>

            <!-- REMINDER (EVENT ONLY) -->
            <div class="flex-row event-mode-only" style="margin-top:20px;">
                <div class="mission-field">
                    <label class="section-label" style="font-size:9px;">REMINDER</label>
                    <select id="event-reminder" class="input-system" style="padding:10px; border-radius:8px; width:100%;">
                        <option value="60" selected>1 hour before (Default)</option>
                        <option value="30">30 minutes before</option>
                        <option value="10">10 minutes before</option>
                        <option value="0">At time of event</option>
                        <option value="-1">No reminder</option>
                    </select>
                </div>
            </div>

            <!-- SECTION 4: ENRICHMENT (collapsible, last — progressive disclosure) -->
            <div class="dm-enrich" id="dm-enrich">
                <div class="dm-enrich-toggle" onclick="tfToggleEnrichSection()">
                    <span id="dm-enrich-text">+ Add notes, links &amp; checklist</span>
                </div>
                <div class="dm-enrich-body" id="dm-enrich-body">
                    <div class="flex-row">
                        <div class="mission-field">
                            <label class="section-label" style="font-size:9px;">NOTES</label>
                            <textarea id="mission-notes" class="input-system enrich-textarea"
                                      placeholder="Context, approach, what to watch for..."
                                      oninput="tfAutoGrow(this); tfNotesCounter(this); tfUpdateProgressDots();"></textarea>
                            <div id="mission-notes-counter" class="enrich-counter"></div>
                        </div>
                    </div>
                    <div class="flex-row">
                        <div class="mission-field">
                            <label class="section-label" style="font-size:9px;">LINKS &amp; REFERENCES</label>
                            <div class="enrich-link-input-row">
                                <div class="enrich-type-selector">
                                    <button type="button" class="enrich-type-btn active" data-ltype="url" onclick="tfSelectLinkType(this,'url')" title="URL">🔗</button>
                                    <button type="button" class="enrich-type-btn" data-ltype="map" onclick="tfSelectLinkType(this,'map')" title="Map / location">📍</button>
                                    <button type="button" class="enrich-type-btn" data-ltype="reference" onclick="tfSelectLinkType(this,'reference')" title="Reference">📄</button>
                                    <button type="button" class="enrich-type-btn" data-ltype="file" onclick="tfSelectLinkType(this,'file')" title="File">📁</button>
                                </div>
                                <input type="text" id="mission-link-input" class="input-system enrich-link-input" placeholder="https://..." autocomplete="off"
                                       onkeydown="if(event.key==='Enter'){event.preventDefault(); tfAddLink();}">
                                <button type="button" class="enrich-add-btn" onclick="tfAddLink()">+ Add</button>
                            </div>
                            <input type="text" id="mission-link-title" class="input-system enrich-link-title" placeholder="Label (optional, e.g. Design doc)" autocomplete="off"
                                   onkeydown="if(event.key==='Enter'){event.preventDefault(); tfAddLink();}">
                            <div id="mission-links-list" class="enrich-chips"></div>
                        </div>
                    </div>
                    <div class="flex-row">
                        <div class="mission-field">
                            <label class="section-label" style="font-size:9px;">CHECKLIST (OPTIONAL)</label>
                            <input type="text" id="mission-checklist-input" class="input-system" placeholder="Add a sub-task, then press Enter..." autocomplete="off"
                                   onkeydown="if(event.key==='Enter'){event.preventDefault(); tfAddChecklistItem();}">
                            <div id="mission-checklist-list" class="enrich-build-list"></div>
                        </div>
                    </div>
                </div>
            </div>

            </div><!-- /dm-body -->
            <div class="dm-footer">
                <span id="dm-focus-badge" style="display:none; font-size:10px; color:#58A6FF; background:rgba(88,166,255,0.1); border:1px solid #58A6FF; border-radius:12px; padding:3px 8px; font-family:'DM Mono',monospace; align-self:center; margin-right:8px;"></span>
                <button class="btn-deploy" id="btn-deploy" disabled>DEPLOY MISSION</button>
                <button class="dm-cancel" onclick="toggleCreateMission()">CANCEL</button>
            </div>
        </div>
    </div>


    <script>
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

    // ── PHASE 1 UTILITIES ─────────────────────────────────────────────
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
                color = '#F85149';
            } else if (isToday) {
                if (diffHr > 3) { text = 'Today at ' + timeStr; color = '#8B949E'; pressureLevel = 0; }
                else if (diffHr > 1) { text = 'Today at ' + timeStr + ' · ' + Math.floor(diffHr) + 'h ' + (diffMin % 60) + 'm left'; color = '#D29922'; pressureLevel = 1; isUrgent = true; }
                else if (diffMin > 15) { text = 'Today at ' + timeStr + ' · ' + diffMin + 'm left'; color = '#D29922'; pressureLevel = 2; isUrgent = true; }
                else { text = 'Today at ' + timeStr + ' · ' + diffMin + 'm left ⚠'; color = '#F85149'; pressureLevel = 3; isUrgent = true; }
            } else if (isTomorrow) { text = 'Tomorrow at ' + timeStr; color = '#8B949E'; }
            else { text = dateStr + ' · ' + timeStr; color = '#8B949E'; }
            return { text, color, isOverdue, isUrgent, pressureLevel };
        } catch(e) { return null; }
    }

    function getPressureLevel(task) {
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
            const r1 = new RegExp('\\b(' + monthFull[mi] + '|' + monthNames[mi] + ')\\s+(\\d{1,2})');
            const r2 = new RegExp('(\\d{1,2})(?:st|nd|rd|th)?\\s+(' + monthFull[mi] + '|' + monthNames[mi] + ')');
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
                ? `<span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--blue);background:rgba(88,166,255,0.08);padding:1px 6px;border-radius:4px;margin-left:8px;">${t.duration}</span>`
                : '';
        }
        function dlStr(t) {
            const d = (typeof formatDeadline === 'function') ? formatDeadline(t.deadline) : null;
            return d ? `<span style="font-size:10px;color:${d.color};margin-left:8px;font-family:'DM Mono',monospace;">${d.text}</span>` : '';
        }
        function row(t) {
            const done = t.completed ? 'opacity:0.5;text-decoration:line-through;' : '';
            return `<div style="display:flex;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--text-body);${done}">${t.title}${durBadge(t)}${dlStr(t)}</div>`;
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
            const nc = data.day_mode === 'best' ? '#3FB950' : (data.day_mode === 'worst' ? '#D29922' : '#58A6FF');
            html += `<div style="font-size:11px;color:${nc};letter-spacing:0.5px;margin-bottom:4px;">⚡ ${data.day_note}</div>`;
        }
        html += group('★ PRIME TARGET', '#D29922', 'rgba(210,153,34,0.04)', prime);
        html += group('SECONDARY', '#58A6FF', 'rgba(88,166,255,0.03)', sec);
        html += group('LOW EFFORT', '#6E7681', 'rgba(139,148,158,0.03)', low);
        if (!prime.length && !sec.length && !low.length) {
            // S13-A BLOCK 1: nothing scheduled → a single generate action, not an empty void
            html = `<div style="opacity:0.6;font-size:12px;margin-bottom:10px;">No path generated for today.</div>
                <button onclick="regeneratePath()" style="width:100%;background:transparent;border:1px dashed #30363D;color:#6E7681;font-size:11px;padding:10px;border-radius:8px;cursor:pointer;font-family:'DM Mono',monospace;letter-spacing:1px;">+ Generate Today's Path</button>`;
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
                    btn.style.background = 'linear-gradient(135deg,#D29922,#E3B341)';
                    btn.style.borderColor = 'transparent';
                    btn.style.color = '#0D1117';
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
                    banner.style.background = 'rgba(248,81,73,0.1)';
                    banner.style.border = '1px solid var(--red)';
                    banner.style.color = 'var(--red)';
                    banner.innerHTML = `<span style="animation: glowPulse 1.5s infinite;">⚡</span> ${totalPressure} task(s) need attention now.`;
                } else {
                    banner.style.background = 'rgba(210,153,34,0.1)';
                    banner.style.border = '1px solid var(--amber)';
                    banner.style.color = 'var(--amber)';
                    banner.innerHTML = `⚡ ${totalPressure} task(s) need attention now.`;
                }
                if (!recoveryActive) {
                    banner.innerHTML += ` <button onclick="tfRecEntryConfirm()" style="margin-left:auto;background:rgba(210,153,34,0.1);border:1px solid rgba(210,153,34,0.3);border-radius:6px;padding:4px 12px;color:#D29922;font-size:11px;font-weight:500;cursor:pointer;">Salvage my day →</button>`;
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
                    alerts.push({title:t.title, meta:'Hard deadline · due today, overdue', icon:'⚠ HARD DEADLINE TODAY', color:'#F85149', sort:0});
                } else if (isHard && dueToday && dl.pressureLevel >= 2) {
                    alerts.push({title:t.title, meta:dl.text, icon:'⚡ HARD DEADLINE APPROACHING', color:'#D29922', sort:1});
                } else if (isHard && dl.isOverdue) {
                    alerts.push({title:t.title, meta:'Was due: '+dl.text.replace(/OVERDUE [·—]\s*/, ''), icon:'⚠ HARD DEADLINE MISSED', color:'#F85149', sort:1.5});
                } else if ((t.postpone_count||0) >= 3) {
                    const severe = t.postpone_count >= 5;
                    alerts.push({title:t.title, meta:'Postponed '+t.postpone_count+'×'+(severe?' ⚠⚠':' ⚠'), icon: severe?'🚨 REPEATEDLY DEFERRED':'↩ REPEATEDLY DEFERRED', color: severe?'#F85149':'#D29922', sort:2});
                }
            });
            alerts.sort((a,b) => a.sort - b.sort);
            alerts = alerts.slice(0, 3);

            let html = '';
            if (alerts.length > 0) {
                html = alerts.map(a => `<div class="alert-card">
                        <div class="alert-type" style="color:${a.color}">${a.icon}</div>
                        <div class="alert-title">${a.title}</div>
                        <div class="alert-meta">${a.meta}</div>
                    </div>`).join('');
            } else if (oldMissed === 0) {
                html = '<div style="color:#3FB950; font-size:13px;">✓ All systems nominal.</div>';
            }
            if (oldMissed > 0) {
                html += `<div style="margin-top:8px;background:rgba(248,81,73,0.04);border:1px solid rgba(248,81,73,0.1);color:#F85149;font-size:12px;border-radius:8px;padding:8px 14px;">⚠ ${oldMissed} older missed deadline${oldMissed!==1?'s':''} pending review<br><span style="opacity:0.7;">Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span> to address them</span></div>`;
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
                nowEl.innerHTML = `<div style="background:rgba(88,166,255,0.05);border:1px solid rgba(88,166,255,0.2);border-left:3px solid #58A6FF;border-radius:10px;padding:14px 16px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-size:10px;color:#58A6FF;letter-spacing:2px;font-weight:500;">▶ NOW — YOU ARE HERE</div>
                        <div style="font-family:'DM Mono',monospace;color:#6E7681;font-size:11px;">${nowTimeStr}</div>
                    </div>
                    <div style="font-size:15px;color:#E6EDF3;font-weight:500;margin-top:6px;">${t.title}</div>
                    <div style="font-size:11px;color:#8B949E;margin-top:2px;">${t.priority}${durStr}${endsStr}</div>
                    <button onclick="tfStartFocus(${t.id})" style="background:linear-gradient(135deg,#1F6FEB,#388BFD);border:none;border-radius:8px;height:34px;padding:0 14px;color:#fff;font-size:12px;font-weight:600;cursor:pointer;margin-top:10px;">Start Focus →</button>
                </div>`;
            } else {
                let sub;
                if (futureNow.length > 0) {
                    const t = futureNow[0];
                    const mins = Math.round((new Date(t.deadline) - now) / 60000);
                    sub = `<div style="color:#8B949E;font-size:12px;margin-top:4px;">Next: ${t.title} · in ${mins} min</div>`;
                } else if (activeTasks.some(t => t.deadline && new Date(t.deadline) < now)) {
                    sub = `<div style="color:#F85149;font-size:12px;margin-top:4px;">All scheduled missions overdue.<br>Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span></div>`;
                } else {
                    sub = `<div style="color:#8B949E;font-size:12px;margin-top:4px;">Nothing due soon.</div>`;
                }
                nowEl.innerHTML = `<div style="background:rgba(255,255,255,0.02);border:1px solid #21262D;border-radius:10px;padding:12px 16px;">
                    <div style="font-size:13px;color:#E6EDF3;">No mission in current window.</div>
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
                    <button onclick="toggleCreateMission()" style="margin-top:10px;background:rgba(88,166,255,0.1);border:1px solid rgba(88,166,255,0.2);color:var(--blue);border-radius:8px;padding:8px 14px;font-size:12px;cursor:pointer;">+ Create Mission</button>`;
            } else {
                upcomingContainer.innerHTML = todays.slice(0, 6).map(t => {
                    const np = normalizePriority(t.priority);
                    const isNow = isInNowWindow(t);
                    const borderColor = isNow ? 'var(--blue)' : (np === 'high' ? 'var(--red)' : np === 'medium' ? 'var(--amber)' : 'var(--blue)');
                    const dlInfo = formatDeadline(t.deadline);
                    const dlStr = dlInfo ? `<span style="font-size:10px;color:${dlInfo.color};margin-left:8px;font-family:'DM Mono',monospace;">${dlInfo.text}</span>` : '';
                    const nowBadge = isNow ? `<span style="background:rgba(88,166,255,0.2);color:var(--blue);font-size:9px;font-weight:800;padding:2px 6px;border-radius:4px;margin-right:6px;letter-spacing:0.5px;">NOW</span>` : '';
                    // Fix 3: only show a duration line when one is actually set
                    const durLine = t.duration ? `<div style="font-size:11px;color:var(--text-disabled);margin-top:6px;font-family:'DM Mono',monospace;">Est. ${t.duration}</div>` : '';
                    return `<div style="padding:12px;background:rgba(255,255,255,0.02);border-radius:8px;border-left:3px solid ${borderColor};">
                        <div style="display:flex;align-items:center;flex-wrap:wrap;">${nowBadge}${t.title}${dlStr}</div>
                        ${durLine}
                    </div>`;
                }).join('');

                // Fix 3: Next = earliest deadline >= now; if all overdue → taskflow missed (not "Next: overdue")
                const future2 = todays.filter(t => t.deadline && new Date(t.deadline) >= now).sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
                if (future2.length > 0) {
                    const nt = future2[0];
                    const mins = Math.round((new Date(nt.deadline) - now) / 60000);
                    upcomingContainer.innerHTML += `<div style="margin-top:10px;font-size:12px;color:#58A6FF;">Next: ${nt.title} · in ${mins} min</div>`;
                } else if (todays.some(t => t.deadline && new Date(t.deadline) < now)) {
                    upcomingContainer.innerHTML += `<div style="margin-top:10px;font-size:12px;color:#D29922;">All scheduled missions overdue. Run: <span style="font-family:'DM Mono',monospace;">taskflow missed</span></div>`;
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
                    `<div class="enrich-notes-text" style="background:#0D1117;border:1px solid var(--border-subtle);border-radius:8px;padding:12px 14px;max-height:160px;">${tfEsc(desc)}</div></div>`;
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
        window.open(l.url, '_blank');
    };
    window.tfCopyLink = function(taskId, linkId, btn) {
        const t = allTasks.find(x => x.id === taskId); if (!t) return;
        const l = (t.links || []).find(x => x.id === linkId); if (!l) return;
        const done = () => { const o = btn.textContent; btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = o; }, 1500); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(l.url).then(done).catch(() => showToast('Copy failed', 'var(--red)'));
        else showToast(l.url, 'var(--blue)');
    };

    function tfConfetti(anchorEl) {
        const colors = ['#3FB950', '#58A6FF'];
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
                    eventBadge = `<span class="badge" style="background:rgba(163,113,247,0.15);color:var(--ai-purple);border:1px solid rgba(163,113,247,0.3);">📅 EVENT${dateStr}${timeRange}</span>`;
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
                            <div class="task-title">${t.title}</div>
                            ${durBadge}${overdueChip}${recoveryBadge}
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px;padding-left:28px;">
                            <span class="badge ${np}">${(t.priority||'Medium').toUpperCase()}</span>
                            ${(t.tags||[]).map(tg =>
                                '<span class="badge tag" onclick="event.stopPropagation(); filterByTag(\\'' + tg + '\\')">#' + tg + '</span>'
                            ).join('')}
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
                document.body.style.background = '#060A0F';
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
            if (!tasks.length) return '<div style="color:#6E7681;font-size:12px;margin-top:8px;">No actionable tasks found.</div>';
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
        b.innerHTML = '<div class="rec-dialog"><div class="rec-d-icon" style="color:#D29922;">⚡</div><div class="rec-d-title">Activate Recovery Mode?</div><div class="rec-d-desc">Loading…</div></div>';
        const rows = await tfRecPreviewRows();
        b.innerHTML = `<div class="rec-dialog">
            <div class="rec-d-icon" style="color:#D29922;">⚡</div>
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
            <div class="rec-d-icon" style="color:#8B949E;">←</div>
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
            if (res.ok) { await checkRecoveryStatus(); try { renderTaskList(); } catch(e) {} if (typeof showToast === 'function') showToast('Recovery Mode active.', '#D29922'); }
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
        el.innerHTML = '<span style="color:#D29922;font-size:14px;">⏳</span>' +
            '<span class="rec-pw-mid"><span style="color:#D29922;">You haven\\'t completed anything today.</span> <span style="color:#8B949E;">Focus window closing.</span></span>' +
            '<button class="rec-pw-link" onclick="tfRecActivate(\\'D\\')">Salvage my day →</button>' +
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
            '<span style="color:#D29922;font-size:20px;">⚡</span>' +
            '<button class="rec-pw-x" onclick="tfRecDismissSheet(true)">×</button></div>' +
            '<div style="font-size:20px;color:#E6EDF3;margin-top:8px;">Today\\'s been difficult.</div>' +
            '<div style="font-size:14px;color:#8B949E;margin-top:4px;">You have ' + incomplete + ' incomplete tasks. Want to simplify?</div>' +
            rows +
            '<button class="rec-btn-primary" onclick="tfRecDismissSheet(false); tfRecActivate(\\'auto_6pm\\')">Activate Recovery Mode</button>' +
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
            const dlColor = dl ? dl.color : '#8B949E';
            stack.innerHTML += `
            <div class="reminder-toast${isHard?' hard-reminder':''}" id="reminder-${t.id}">
                <div class="toast-header">
                    <span class="toast-label${isHard?' hard':''}">🔔 REMINDER</span>
                    <button class="toast-close" onclick="dismissReminder(${t.id})">&times;</button>
                </div>
                <div class="toast-title">${t.title}</div>
                ${dl ? '<div class="toast-deadline" style="color:'+dlColor+'">Due: '+dlText+'</div>' : ''}
                <div class="toast-meta">${(t.priority||'Medium').toUpperCase()}${t.duration ? ' · '+t.duration : ''}</div>
                <div class="toast-actions">
                    <button class="btn-toast-focus" onclick="dismissReminder(${t.id});startFocus(${t.id})">Start Focus</button>
                    <button class="btn-toast-dismiss" onclick="dismissReminder(${t.id})">Dismiss</button>
                </div>
            </div>`;
        });
        if (due.length > 3) {
            stack.innerHTML += `<div style="font-size:12px;color:#8B949E;text-align:right;margin-top:4px;">and ${due.length-3} more reminders</div>`;
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
            const color = s => s >= 80 ? '#3FB950' : (s >= 60 ? '#D29922' : '#F85149');
            const barsEl = document.getElementById('dow-bars');
            if (barsEl) {
                barsEl.innerHTML = names.map((nm, i) => {
                    const row = byDay[i] || byDay[String(i)] || { avg_tis: null, sample_size: 0 };
                    const tis = row.avg_tis;
                    const has = row.sample_size >= 2 && tis != null;
                    const w = has ? Math.max(2, Math.round(tis)) : 0;
                    const bar = has ? `<div style="height:8px;width:${w}%;background:${color(tis)};border-radius:4px;"></div>` : '';
                    return `<div style="display:flex;align-items:center;gap:10px;">
                        <div style="width:32px;color:#8B949E;font-size:11px;">${nm}</div>
                        <div style="flex:1;height:8px;background:#21262D;border-radius:4px;overflow:hidden;">${bar}</div>
                        <div style="width:28px;text-align:right;font-family:'DM Mono',monospace;font-size:11px;color:${has ? color(tis) : '#6E7681'};">${has ? tis : '—'}</div>
                    </div>`;
                }).join('');
            }
            const chipsEl = document.getElementById('dow-chips');
            if (chipsEl) {
                let chips = '';
                if (d && d.best_day_name) {
                    chips += `<div style="flex:1;background:rgba(63,185,80,0.08);border:1px solid rgba(63,185,80,0.15);border-radius:8px;padding:8px 12px;">
                        <div style="color:#6E7681;font-size:9px;text-transform:uppercase;letter-spacing:1px;">BEST DAY</div>
                        <div style="color:#3FB950;font-size:14px;font-weight:500;">${d.best_day_name}</div>
                        <div style="color:#8B949E;font-size:11px;">avg ${d.best_day_avg_tis} TIS</div>
                    </div>`;
                }
                if (d && d.worst_day_name && d.worst_day_avg_tis != null && d.worst_day_avg_tis < 65 && d.worst_day_name !== d.best_day_name) {
                    chips += `<div style="flex:1;background:rgba(210,153,34,0.08);border:1px solid rgba(210,153,34,0.15);border-radius:8px;padding:8px 12px;">
                        <div style="color:#6E7681;font-size:9px;text-transform:uppercase;letter-spacing:1px;">WATCH OUT</div>
                        <div style="color:#D29922;font-size:14px;font-weight:500;">${d.worst_day_name}</div>
                        <div style="color:#8B949E;font-size:11px;">avg ${d.worst_day_avg_tis} TIS</div>
                    </div>`;
                }
                if (!chips) chips = `<div style="color:#6E7681;font-size:11px;">Building pattern… complete tasks across more days for day-of-week insights.</div>`;
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

            const color = s => s >= 80 ? '#3FB950' : (s >= 60 ? '#D29922' : '#F85149');
            const avg = Math.round(w.avg_score || 0);

            // Section 1 — gauge
            const ring = document.getElementById('tis-ring');
            const CIRC = 2 * Math.PI * 78;
            if (ring) { ring.setAttribute('stroke-dasharray', CIRC.toFixed(1)); ring.setAttribute('stroke-dashoffset', (CIRC * (1 - avg / 100)).toFixed(1)); ring.setAttribute('stroke', color(avg)); }
            const num = document.getElementById('tis-num'); if (num) { num.textContent = avg; num.setAttribute('fill', color(avg)); }
            const trend = document.getElementById('tis-trend');
            if (trend) { const t = w.trend || 'stable'; const tc = t === 'improving' ? '#3FB950' : (t === 'declining' ? '#F85149' : '#D29922'); const ar = t === 'improving' ? '↑' : (t === 'declining' ? '↓' : '→'); trend.innerHTML = `<span style="color:${tc};">${ar} ${t}</span> · 7-day average`; }
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
                ['Completed', sum('tasks_completed'), '#3FB950'],
                ['Missed', sum('tasks_missed'), '#F85149'],
                ['Postponed', sum('tasks_postponed'), '#D29922'],
                ['Dropped', sum('tasks_dropped'), '#8B949E'],
                ['Focus sessions', sum('focus_sessions'), '#58A6FF'],
                ['Focus minutes', sum('focus_minutes_total'), '#58A6FF'],
                ['Streak', (w.execution_streak || 0) + 'd', '#D29922'],
                ['Hard misses', w.hard_deadlines_missed_week || 0, '#F85149'],
            ];
            const chipsEl = document.getElementById('stats-chips');
            if (chipsEl) chipsEl.innerHTML = chips.map(([label, val, c]) =>
                `<div style="background:#161B22; border:1px solid #21262D; border-radius:8px; padding:10px 14px;">
                    <div style="font-family:'DM Mono',monospace; font-size:24px; color:${c};">${val}</div>
                    <div style="color:#6E7681; font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-top:4px;">${label}</div>
                </div>`).join('');

            // Section 4 — patterns
            const pat = document.getElementById('stats-patterns');
            if (pat) {
                const drift = w.avg_start_drift;
                const driftStr = drift == null ? '—' : `${drift > 0 ? '+' : ''}${Math.round(drift)} min`;
                const driftColor = drift == null ? 'var(--text-muted)' : (drift > 0 ? '#D29922' : '#3FB950');
                pat.innerHTML = `
                    <div>PEAK HOUR <span style="float:right; color:var(--blue); font-family:'DM Mono',monospace;">${_statsHourRange(w.most_productive_hour)}</span></div>
                    <div>MOST AVOIDED <span style="float:right; color:#D29922;">${w.most_avoided_tag ? ('#' + w.most_avoided_tag) : '—'}</span></div>
                    <div>AVG START DRIFT <span style="float:right; color:${driftColor}; font-family:'DM Mono',monospace;">${driftStr}</span></div>
                    <div>RECOVERY (week) <span style="float:right; color:var(--text-hero); font-family:'DM Mono',monospace;">${w.recovery_sessions || 0}</span></div>`;
            }

            // Section 5 — recovery history
            const rec = document.getElementById('stats-recovery');
            if (rec) {
                const hist = w.recovery_history || [];
                rec.innerHTML = hist.length ? hist.map(h => {
                    const ok = h.was_successful;
                    return `<div style="display:flex; justify-content:space-between; border-left:3px solid ${ok ? '#3FB950' : '#F85149'}; padding:6px 10px; background:rgba(255,255,255,0.02); border-radius:6px;">
                        <span>${h.date || ''} · ${h.trigger_reason || '—'}</span>
                        <span style="color:${ok ? '#3FB950' : '#F85149'};">${h.tasks_completed || 0} done ${ok ? '✓' : '✗'}</span>
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

                el.innerHTML = `<div class="tl-chip-title">${hardIcon}${task.title}</div>` +
                    (timeStr || durStr ? `<div class="tl-chip-meta">${timeStr}${durStr}</div>` : '');

                el.ondragstart = (e) => {
                    e.dataTransfer.setData('application/task-id', task.id.toString());
                    setTimeout(() => el.classList.add('dragging'), 0);
                };
                el.ondragend = () => {
                    el.classList.remove('dragging');
                    document.querySelectorAll('.drag-over').forEach(d => d.classList.remove('drag-over'));
                };

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
                        badge.style.cssText = 'background: rgba(255,255,255,0.1); color: var(--text-muted); font-size: 9px; padding: 2px 6px; border-radius: 10px; margin-left: 6px;';
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
            return `<div class="filter-chip${isActive}" onclick="filterByTag('${tg}', this)">#${tg.toUpperCase()}</div>`;
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
        const tagBadges = (task.tags||[]).map(tg => `<span class="badge tag">#${tg}</span>`).join('');
        const pc = task.postpone_count || 0;
        const canPostpone = pc < 5;
        let postponeWarn = '';
        if (pc >= 5) postponeWarn = '<div style="color:#F85149;font-size:11px;margin-top:8px;padding:6px 10px;background:rgba(248,81,73,0.06);border-radius:6px;">⚠ Maximum postpones reached. Execute or Drop this mission.</div>';
        else if (pc >= 3) postponeWarn = '<div style="color:#D29922;font-size:11px;margin-top:8px;padding:6px 10px;background:rgba(210,153,34,0.06);border-radius:6px;">⚠ Postponed ' + pc + '× — the mirror doesn\\'t lie. Consider dropping.</div>';
        else if (pc >= 2) postponeWarn = '<div style="color:#8B949E;font-size:11px;margin-top:8px;">Postponed ' + pc + '× — be honest with yourself.</div>';

        const createdDate = task.created_at ? new Date(task.created_at).toLocaleDateString([], {day:'numeric', month:'short', year:'numeric'}) : 'Unknown';

        let fMin = 25;
        if (task.duration) { const mm = String(task.duration).match(/([0-9]+) *(h|m)/i); if (mm) fMin = mm[2].toLowerCase() === 'h' ? parseInt(mm[1]) * 60 : parseInt(mm[1]); }
        const focusClock = (fMin < 10 ? '0' : '') + fMin + ':00';

        document.getElementById('modal-content').innerHTML = `
            <div class="brief-header">
                <div class="brief-h-label">MISSION BRIEFING</div>
                <h2 class="brief-title">${task.title}</h2>
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

                <div style="background:rgba(255,255,255,0.02); padding:18px; border-radius:14px; border:1px solid rgba(255,255,255,0.05);">
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
                        if(disp){disp.textContent='→ ' + nice; disp.style.color='#3FB950'; disp.classList.add('visible');}
                        if(section) section.style.display='block';
                    } else {
                        parsedDeadlineISO = null;
                        if(disp){disp.textContent="→ Could not understand. Try: 'Friday 3pm'"; disp.style.color='#F85149'; disp.classList.add('visible');}
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
                        disp.textContent = '→ ' + nice; disp.style.color = '#3FB950'; disp.style.opacity = '1';
                        if (typeRow) typeRow.style.display = 'flex';
                    } else if (disp) { disp.textContent = '→ Could not parse'; disp.style.color = '#F85149'; disp.style.opacity = '1'; if(typeRow) typeRow.style.display='none'; }
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
