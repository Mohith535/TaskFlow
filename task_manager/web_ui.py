HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskFlow | Mission Control</title>
    <script src="/static/three.min.js"></script>
    <!-- SEC-06: external Google-Fonts CDN removed to honor the 100% offline promise (it leaked
         the user's IP to Google on every load). Falls back to system mono/sans below. To restore
         the exact look, bundle the font files under static/ and @font-face them locally. -->
    <script>
    /* THEME: apply the saved theme synchronously before first paint — avoids a flash of the wrong theme */
    (function(){try{
        var t=localStorage.getItem('tf_active_theme');
        if(t&&t!=='midnight'&&t!=='custom'){document.documentElement.setAttribute('data-theme',t);}
        if(t==='custom'){var c=JSON.parse(localStorage.getItem('tf_custom_theme')||'{}');for(var k in c){document.documentElement.style.setProperty(k,c[k]);}}
    }catch(e){}})();
    </script>
    <link rel="stylesheet" href="/static/dashboard.css">
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
            <button id="omnibar-close" onclick="document.getElementById('omnibar-overlay').classList.remove('active')" style="position:absolute;top:-14px;right:-14px;width:36px;height:36px;border-radius:50%;background:color-mix(in srgb, var(--text-primary) 6%, transparent);border:1px solid color-mix(in srgb, var(--text-primary) 15%, transparent);color:var(--text-muted);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:10;transition:all 0.3s;backdrop-filter:blur(8px);" onmouseover="this.style.background='color-mix(in srgb, var(--accent-danger) 90%, transparent)';this.style.color='#fff';this.style.borderColor='transparent';this.style.boxShadow='0 0 20px color-mix(in srgb, var(--accent-danger) 40%, transparent)';this.style.transform='rotate(90deg) scale(1.1)'" onmouseout="this.style.background='color-mix(in srgb, var(--text-primary) 6%, transparent)';this.style.color='var(--text-muted)';this.style.borderColor='color-mix(in srgb, var(--text-primary) 15%, transparent)';this.style.boxShadow='none';this.style.transform='scale(1)'">&times;</button>
            <input type="text" id="omnibar-input" placeholder="Capture a thought..." autocomplete="off">
            <div id="omnibar-time-section" style="margin-top:12px;padding:14px 16px;background:color-mix(in srgb, var(--text-primary) 2%, transparent);border:1px solid color-mix(in srgb, var(--text-primary) 6%, transparent);border-radius:12px;">
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
                    <div id="focus-task-notes" style="padding:16px; background:color-mix(in srgb, var(--text-primary) 3%, transparent); border-radius:12px; border:1px solid color-mix(in srgb, var(--text-primary) 5%, transparent); font-size:14px; color:var(--text-body); line-height:1.6; opacity:0.8;">No tactical notes provided.</div>
                </div>

                <div>
                    <div style="font-size:10px; font-weight:700; color:var(--text-disabled); letter-spacing:2px; margin-bottom:12px;">FOCUS CYCLE</div>
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="flex:1; height:8px; background:color-mix(in srgb, var(--text-primary) 10%, transparent); border-radius:4px; overflow:hidden;">
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
                    <div id="focus-defense-counter" style="font-size:11px; color:color-mix(in srgb, var(--text-primary) 40%, transparent); margin-top:8px;">✦ 0 breach attempts deflected</div>
                </div>
            </div>

            <!-- Right: Execution Status -->
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:40px; border-left:1px solid color-mix(in srgb, var(--text-primary) 5%, transparent); padding-left:60px; position:relative;">
                <div id="focus-timer" class="timer-running" style="font-size:120px; font-family:var(--font-mono); font-weight:700; color:var(--blue); line-height:1; transition: color 2s ease;">25:00</div>
                <div id="focus-paused-indicator" style="position:absolute; top:40%; left:50%; transform:translate(-50%,-50%); font-size:24px; font-weight:700; color:var(--text-hero); letter-spacing:8px; display:none; background:rgba(0,0,0,0.8); padding:10px 20px; border-radius:10px; border:1px solid color-mix(in srgb, var(--text-primary) 10%, transparent);">PAUSED</div>
                
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
        <div class="abort-modal-content" style="border-color: color-mix(in srgb, var(--accent-emerald) 30%, transparent); box-shadow: 0 20px 60px color-mix(in srgb, var(--accent-emerald) 15%, transparent);">
            <div class="abort-icon" style="color: var(--emerald); animation: none; font-size:48px;">✓</div>
            <h2 style="color:var(--text-hero); margin-bottom:12px; font-size:24px;">Mission Completed Early?</h2>
            <p id="complete-modal-time" style="color:var(--text-muted); margin-bottom:30px; line-height:1.5;">Remaining time: calculating...</p>
            <div style="display:flex; flex-direction:column; gap:12px;">
                <button onclick="submitMissionComplete()" class="btn-modal-primary" style="background:var(--emerald); color:#000;">Complete & End Session</button>
                <button onclick="hideCompleteModal()" class="btn-modal-danger" style="color:var(--text-muted); border-color:color-mix(in srgb, var(--text-primary) 20%, transparent);">Continue Focus</button>
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

                <div style="width: 50px; height: 2px; background: color-mix(in srgb, var(--text-primary) 10%, transparent); margin: 0 auto 25px;"></div>

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
            
            <button onclick="closeRewardScreen()" style="background:var(--bg-surface); border:1px solid color-mix(in srgb, var(--text-primary) 10%, transparent); color:var(--text-hero); padding:16px 32px; border-radius:12px; font-weight:700; cursor:pointer; transition:all 0.3s; box-shadow:0 0 20px color-mix(in srgb, var(--text-primary) 10%, transparent);">
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
        <div id="operator-bar" onclick="tfToggleOperatorPanel(event)" style="margin-top:auto; padding-top:24px; border-top:1px solid var(--border-subtle); display:flex; align-items:center; gap:12px; position:relative; cursor:pointer;">
            <div style="width:32px; height:32px; background:var(--bg-surface); border-radius:50%; display:flex; align-items:center; justify-content:center;">👨‍💻</div>
            <div style="font-size:12px; font-weight:600; color:var(--text-hero);">OPERATOR M</div>
            <div style="margin-left:auto; color:var(--text-disabled); font-size:12px;">⚙</div>
            <div id="operator-panel" class="operator-panel" onclick="event.stopPropagation()">
                <div class="op-h">OPERATOR SETTINGS</div>
                <div class="op-row">
                    <div>
                        <div class="op-label">3D Particles</div>
                        <div class="op-sub">Ambient background animation</div>
                    </div>
                    <div id="op-particle-toggle" class="op-toggle" onclick="tfToggleParticles()"><div class="op-thumb"></div></div>
                </div>
                <div id="op-opacity-wrap" class="op-opacity-wrap">
                    <div class="op-slider-row"><span class="op-slider-label">Opacity</span><span id="op-opacity-val" class="op-slider-val">25%</span></div>
                    <input id="op-opacity-slider" class="op-slider" type="range" min="5" max="60" step="5" value="25"
                           oninput="tfParticleOpacityInput(this.value)" onchange="tfParticleOpacitySave(this.value)">
                </div>
                <div class="op-why" onclick="tfToggleWhy()">⚠ Why does this affect performance?</div>
                <div id="op-why-panel" class="op-why-panel">
                    <div class="op-why-text">Peripheral motion involuntarily captures attention — your visual system is wired to track movement.<br><br>Behind task lists and charts, animation measurably reduces reading speed and accelerates cognitive fatigue over time.<br><br>Lower opacity = better focus on data pages. Turning it off completely removes all attention cost.</div>
                    <div class="op-why-chips">
                        <span class="op-chip op-chip-red">↓ Reading speed with motion</span>
                        <span class="op-chip op-chip-green">↑ Focus on static backgrounds</span>
                    </div>
                </div>
                <div class="op-h" style="margin-top:18px;">THEME</div>
                <div class="op-theme-row" id="op-theme-swatches"></div>
                <div class="op-customize" onclick="tfToggleCustomize()">Customize ▾</div>
                <div id="op-custom-panel" class="op-custom-panel">
                    <div class="op-pick-row"><span>Background</span><input type="color" id="tf-pick-bg" class="op-pick" oninput="tfPickVar('--bg-base', this.value)"></div>
                    <div class="op-pick-row"><span>Surface</span><input type="color" id="tf-pick-surface" class="op-pick" oninput="tfPickVar('--bg-surface', this.value)"></div>
                    <div class="op-pick-row"><span>Primary text</span><input type="color" id="tf-pick-text" class="op-pick" oninput="tfPickVar('--text-primary', this.value)"></div>
                    <div class="op-pick-row"><span>Accent</span><input type="color" id="tf-pick-accent" class="op-pick" oninput="tfPickVar('--accent-info', this.value)"></div>
                    <button class="op-save-theme" onclick="tfSaveCustomTheme()">Save as Custom Theme</button>
                </div>
                <div class="op-reset" onclick="tfResetTheme()">Reset to Midnight</div>
            </div>
        </div>
    </aside>

    <!-- OPERATIONS CENTER -->
    <main class="col-main">
        <!-- VIEW: DASHBOARD (CONTROL CENTER) -->
        <div id="view-dashboard" class="view-content">
            <div style="max-width: 800px; margin: 0 auto; width: 100%;">
                
                <!-- 1. AI INPUT -->
                <div class="ai-zone" style="margin-top: 24px; text-align: center; border: 1px solid color-mix(in srgb, var(--accent-ai) 30%, transparent); box-shadow: 0 0 40px color-mix(in srgb, var(--accent-ai) 10%, transparent);">
                    <div style="font-size: 12px; font-weight: 700; color: var(--ai-purple); margin-bottom: 20px; letter-spacing: 2px;">INTELLIGENCE PROTOCOL</div>
                    <div class="ai-input-wrap" style="background: rgba(0,0,0,0.2); justify-content: center; padding: 4px 16px;">
                        <span style="color:var(--ai-purple); font-size:20px;">✦</span>
                        <input type="text" id="ai-input" class="ai-input" placeholder="What's the next objective?" style="text-align: center; font-size: 16px; padding: 12px;">
                        <button class="btn-execute" id="btn-execute" style="background: color-mix(in srgb, var(--accent-ai) 10%, transparent); color: var(--ai-purple); border-color: color-mix(in srgb, var(--accent-ai) 30%, transparent);">SYNTHESIZE</button>
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
                        style="margin-top:16px; width:100%; background:transparent; border:1px dashed var(--border-neutral); color:var(--text-disabled); font-size:11px; padding:10px; border-radius:8px; cursor:pointer; font-family:'DM Mono',monospace; letter-spacing:1px;">
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
                    <div class="mission-panel" style="padding: 24px; border-color: color-mix(in srgb, var(--accent-danger) 20%, transparent); box-shadow: inset 0 0 20px color-mix(in srgb, var(--accent-danger) 5%, transparent);">
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
                                <div id="cc-overdue-count" style="font-size:18px; font-weight:700; color:var(--red); font-family:var(--font-mono);">0</div>
                            </div>
                            <div>
                                <div style="font-size:10px; color:var(--text-disabled); letter-spacing:1.5px; text-transform:uppercase; margin-bottom:4px;">DEFERRED</div>
                                <div id="cc-deferred-count" style="font-size:18px; font-weight:700; color:var(--amber); font-family:var(--font-mono);">0</div>
                            </div>
                        </div>
                    </div>

                    <!-- 5. AI INSIGHT PANEL -->
                    <div class="mission-panel" style="padding: 24px; border-color: color-mix(in srgb, var(--accent-ai) 20%, transparent);">
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
                            <div style="padding:12px; border-left:2px solid var(--green); background:color-mix(in srgb, var(--text-primary) 2%, transparent); font-size:12px;">Your real behavioral telemetry is live in the <strong>Analytics</strong> tab — Time Integrity Score, patterns, streaks and recovery history, computed from how you actually work.</div>
                            <div style="padding:12px; border-left:2px solid var(--blue); background:color-mix(in srgb, var(--text-primary) 2%, transparent); font-size:12px;">CLI: <code>taskflow stats</code>, <code>taskflow heatmap</code>, <code>taskflow rescue</code>, <code>taskflow path</code>.</div>
                            <div style="padding:12px; border-left:2px solid var(--ai-purple); background:color-mix(in srgb, var(--text-primary) 2%, transparent); font-size:12px;">The adaptive AI layer (predictive scheduling, natural-language coaching) arrives in <strong>Phase 3</strong>.</div>
                        </div>
                    </div>
                    
                    <!-- Suggestions -->
                    <div class="mission-panel" style="padding:32px; background:color-mix(in srgb, var(--accent-ai) 5%, transparent); border-color:color-mix(in srgb, var(--accent-ai) 20%, transparent);">
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
                                <circle id="tis-ring" cx="90" cy="90" r="78" fill="none" stroke="var(--green)" stroke-width="10"
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
        <div style="background:color-mix(in srgb, var(--text-primary) 2%, transparent); padding:24px; border-radius:16px; border:1px solid var(--border-neutral);">
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
                <span style="color:var(--green);font-size:14px;">✓</span>
                <div>
                    <div class="prb-t">Day recovered.</div>
                    <div class="prb-s" id="post-rec-badge-sub"></div>
                </div>
            </div>
            <div class="rec-salvage-btn" id="rec-salvage-btn" onclick="tfRecSalvageClick()">
                <span style="font-size:12px;">⚡</span> <span id="rec-salvage-text">SALVAGE MY DAY</span>
            </div>
            <button class="btn-deploy btn-execute" onclick="toggleCreateMission()" style="margin-top:20px; font-size:12px; font-weight:700; background: linear-gradient(135deg, color-mix(in srgb, var(--accent-info) 15%, transparent), color-mix(in srgb, var(--accent-info) 5%, transparent)); color: var(--blue); border: 1px solid color-mix(in srgb, var(--accent-info) 20%, transparent); width:100%; transition:all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 12px rgba(0,0,0,0.2);">+ CREATE MISSION</button>
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
                        <div style="position:relative; width:42px; height:42px; background:color-mix(in srgb, var(--text-primary) 5%, transparent); border:1px solid var(--border-neutral); border-radius:8px; display:flex; align-items:center; justify-content:center; cursor:pointer;" title="Pick a date manually">
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
                    <div id="event-duration-display" style="margin-top:10px; padding:8px 12px; background:color-mix(in srgb, var(--accent-ai) 8%, transparent); border:1px solid color-mix(in srgb, var(--accent-ai) 15%, transparent); border-radius:8px; font-family:var(--font-mono); font-size:12px; color:var(--ai-purple); text-align:center; display:none;">
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
                <span id="dm-focus-badge" style="display:none; font-size:10px; color:var(--blue); background:color-mix(in srgb, var(--accent-info) 10%, transparent); border:1px solid var(--blue); border-radius:12px; padding:3px 8px; font-family:'DM Mono',monospace; align-self:center; margin-right:8px;"></span>
                <button class="btn-deploy" id="btn-deploy" disabled>DEPLOY MISSION</button>
                <button class="dm-cancel" onclick="toggleCreateMission()">CANCEL</button>
            </div>
        </div>
    </div>


    <script src="/static/dashboard.js"></script>
</body>
</html>
"""
