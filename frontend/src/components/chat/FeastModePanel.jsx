import React, { useState, useEffect, useRef, useCallback } from 'react';

// ── Panel has 3 states:
//   1. ANIMATING  – isActivating=true  → progress ring animation
//   2. ACTIVE     – feastStatus non-null → persists across sessions / new chats
//   3. DEFAULT    – feastStatus null    → idle "activate feast mode" prompt

const STEPS = [
  "Calculating calorie bank...",
  "Syncing workout history...",
  "Adjusting macro targets...",
  "Unlocking feast permissions...",
  "🎉 Feast Mode Ready!",
];

const BASE_UNLOCK_COLORS = ["#a855f7", "#22c55e", "#f59e0b", "#ef4444"];

const FACTS = [
  { icon: "🔥", title: "Calorie Banking Works",        body: "Saving 250 kcal/day for 3 days = 750 kcal banked. That's 2 hrs of cardio, without running a step." },
  { icon: "⚡", title: "Metabolism Stays Active",       body: "Strategic feast days prevent metabolic adaptation, keeping your burn rate high." },
  { icon: "💪", title: "Muscle is Protected",           body: "With enough protein on feast days your body burns fat — not muscle — for fuel." },
  { icon: "🧠", title: "Dopamine Peaks on Feast Days",  body: "Planned indulgence boosts motivation and keeps you compliant all week." },
  { icon: "🎯", title: "Smart Cardio = More Room",      body: "45-min cardio today adds ~400 kcal to your party budget. Hello, extra slice." },
];

const CONFETTI_COLORS = ['#a855f7','#fbbf24','#22c55e','#ef4444','#60a5fa','#f472b6'];
const CIRCUMFERENCE = 2 * Math.PI * 42;

const getWorkoutLabel = (pref) => {
  if (pref === 'cardio') return 'Cardio Burn';
  if (pref === 'skip') return 'Rest Day';
  return 'Strength';
};

const getMealLabel = (meals) => {
  if (!meals || meals.length === 0) return 'All Foods OK';
  return meals.map(m => m.charAt(0).toUpperCase() + m.slice(1)).join(', ');
};

const getEventEmoji = (name) => {
  if (!name) return '🎂';
  const n = name.toLowerCase();
  if (n.includes('wedding')) return '💍';
  if (n.includes('birthday')) return '🎂';
  if (n.includes('party')) return '🎉';
  if (n.includes('dinner')) return '🍽';
  if (n.includes('festival') || n.includes('diwali') || n.includes('eid') || n.includes('christmas')) return '🎊';
  return '🎉';
};

const FeastModePanel = ({ isActivating = false, proposalData = null, feastStatus = null, onActivationComplete }) => {
  const [progress, setProgress] = useState(0);
  const [isDone, setIsDone] = useState(false);
  const [revealedUnlocks, setRevealedUnlocks] = useState([]);
  const [factIdx, setFactIdx] = useState(0);
  const [tipHidden, setTipHidden] = useState(false);
  const intervalRef = useRef(null);
  const factIntervalRef = useRef(null);

  // ── Data source priority: feastStatus (API, persists) > proposalData (just activated)
  // During animation: proposalData is used. After reload / new chat: feastStatus is used.
  const src = feastStatus || proposalData;

  const totalBanked =
    feastStatus?.target_bank_calories ??
    proposalData?.total_banked ??
    (proposalData?.daily_deduction * proposalData?.days_remaining) ??
    750;

  const workoutPref =
    feastStatus?.feast_workout_data?.workout_preference ??
    (feastStatus?.workout_boost_enabled ? 'cardio' : 'standard') ??
    proposalData?.workout_preference ??
    'standard';

  const selectedMeals = src?.selected_meals;
  const eventName = src?.event_name ?? 'Your Event';
  const eventDate = src?.event_date
    ? String(src.event_date).split('T')[0]
    : '';
  const daysRemaining = feastStatus?.days_remaining ?? proposalData?.days_remaining ?? 0;
  const dailyDeduction = feastStatus?.daily_deduction ?? proposalData?.daily_deduction ?? 0;
  const feastStat = feastStatus?.status ?? 'BANKING'; // BANKING / FEAST_DAY / COMPLETED

  const UNLOCKS = [
    { name: "Bonus Calories",   val: `+${totalBanked} kcal`,      color: BASE_UNLOCK_COLORS[0] },
    { name: "Meal Flexibility",  val: getMealLabel(selectedMeals),  color: BASE_UNLOCK_COLORS[1] },
    { name: "Workout Credit",    val: getWorkoutLabel(workoutPref), color: BASE_UNLOCK_COLORS[2] },
    { name: "Streak Saved",      val: "Protected 🔥",               color: BASE_UNLOCK_COLORS[3] },
  ];

  // Progress engine
  useEffect(() => {
    if (!isActivating) return;

    setProgress(0);
    setIsDone(false);
    setRevealedUnlocks([]);

    intervalRef.current = setInterval(() => {
      setProgress(prev => {
        const next = Math.min(prev + 1, 100);
        return next;
      });
    }, 80);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isActivating]);

  // Handle progress milestones
  useEffect(() => {
    const thresholds = [20, 40, 60, 80];
    thresholds.forEach((threshold, i) => {
      if (progress >= threshold && !revealedUnlocks.includes(i)) {
        setRevealedUnlocks(prev => [...prev, i]);
      }
    });

    if (progress >= 100 && !isDone) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setIsDone(true);
      spawnConfetti();
      if (onActivationComplete) {
        setTimeout(() => onActivationComplete(), 600);
      }
    }
  }, [progress, isDone, revealedUnlocks, onActivationComplete]);

  // Facts rotation
  useEffect(() => {
    factIntervalRef.current = setInterval(() => {
      setTipHidden(true);
      setTimeout(() => {
        setFactIdx(prev => (prev + 1) % FACTS.length);
        setTipHidden(false);
      }, 350);
    }, 3400);

    return () => {
      if (factIntervalRef.current) clearInterval(factIntervalRef.current);
    };
  }, []);

  const spawnConfetti = useCallback(() => {
    for (let i = 0; i < 55; i++) {
      setTimeout(() => {
        const d = document.createElement('div');
        d.className = 'feast-confetti-dot';
        const size = 5 + Math.random() * 7;
        d.style.cssText = `
          left:${Math.random() * 100}vw; top:-10px;
          width:${size}px; height:${size}px;
          border-radius:${Math.random() > 0.5 ? '50%' : '2px'};
          background:${CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)]};
          animation-duration:${1.5 + Math.random() * 2}s;
          animation-delay:${Math.random() * 0.4}s;
        `;
        document.body.appendChild(d);
        setTimeout(() => d.remove(), 4000);
      }, i * 28);
    }
  }, []);

  const stepIdx = Math.min(
    Math.floor(progress / 100 * (STEPS.length - 1)),
    STEPS.length - 1
  );

  const ringOffset = CIRCUMFERENCE * (1 - progress / 100);
  const currentFact = FACTS[factIdx];

  // ══════════════════════════════════════════
  // STATE 1 – DEFAULT (no feast active at all)
  // ══════════════════════════════════════════
  if (!isActivating && !feastStatus) {
    return (
      <div className="feast-right-panel">
        <div className="feast-rp-inner">
          <div className="feast-section-card" style={{ textAlign: 'center', padding: '30px 16px' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>⚡</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'white', marginBottom: 6 }}>Feast Mode</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
              Activate Feast Mode from the chat to start banking calories for your upcoming event.
            </div>
          </div>

          <div className="feast-section-card">
            <div className="feast-eyebrow">DID YOU KNOW?</div>
            <div className={`feast-tip-inner ${tipHidden ? 'feast-tip-hidden' : ''}`}>
              <div className="feast-tip-emoji">{currentFact.icon}</div>
              <div>
                <div className="feast-tip-title">{currentFact.title}</div>
                <div className="feast-tip-body">{currentFact.body}</div>
              </div>
            </div>
            <div className="feast-tip-dots">
              {FACTS.map((_, i) => (
                <div key={i} className={`feast-tip-dot ${i === factIdx ? 'active' : ''}`} />
              ))}
            </div>
          </div>

          <Ticker />
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════
  // STATE 2 – ANIMATING (first activation)
  // ══════════════════════════════════════════
  if (isActivating) {
    return (
      <div className="feast-right-panel">
        <div className="feast-rp-inner">
          {/* Hero Animation Card */}
          <div className="feast-hero-card">
            <div className={`feast-hero-bg-glow ${isDone ? 'done' : ''}`} />
            <div className="feast-orb-wrap">
              <div className={`feast-orb ${isDone ? 'done' : ''}`}>
                {isDone ? '🔥' : '⚡'}
              </div>
              <div className="feast-orbit-ring">
                <div className={`feast-orbit-dot ${isDone ? 'done' : ''}`} />
              </div>
            </div>
            <div className="feast-hero-title">
              {isDone ? '🎉 Feast Mode Active!' : 'Activating Feast Mode'}
            </div>
            <div className="feast-hero-sub">
              {isDone ? 'Your calorie bank is ready' : STEPS[stepIdx]}
            </div>
            <div className="feast-ring-wrap">
              <svg viewBox="0 0 100 100">
                <circle className="feast-ring-track" cx="50" cy="50" r="42" />
                <circle
                  className={`feast-ring-fill ${isDone ? 'done' : ''}`}
                  cx="50" cy="50" r="42"
                  style={{ strokeDashoffset: ringOffset }}
                />
              </svg>
              <div className="feast-ring-pct">{Math.round(progress)}%</div>
            </div>
            <div className="feast-step-dots">
              {STEPS.map((_, i) => (
                <div key={i} className={`feast-step-dot ${i <= stepIdx ? 'active' : ''} ${isDone ? 'done' : ''}`} />
              ))}
            </div>
          </div>

          {/* Unlocks (reveal as progress advances) */}
          <div className="feast-section-card">
            <div className="feast-eyebrow">UNLOCKING FOR YOU</div>
            <div className="feast-unlock-grid">
              {UNLOCKS.map((u, i) => (
                <div key={i} className={`feast-unlock-item ${revealedUnlocks.includes(i) ? 'revealed' : ''}`}>
                  <div className="feast-unlock-name">{u.name}</div>
                  <div className="feast-unlock-val" style={revealedUnlocks.includes(i) ? { color: u.color } : {}}>
                    {revealedUnlocks.includes(i) ? u.val : '—'}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tips */}
          <div className="feast-section-card">
            <div className="feast-eyebrow">DID YOU KNOW?</div>
            <div className={`feast-tip-inner ${tipHidden ? 'feast-tip-hidden' : ''}`}>
              <div className="feast-tip-emoji">{currentFact.icon}</div>
              <div>
                <div className="feast-tip-title">{currentFact.title}</div>
                <div className="feast-tip-body">{currentFact.body}</div>
              </div>
            </div>
            <div className="feast-tip-dots">
              {FACTS.map((_, i) => (
                <div key={i} className={`feast-tip-dot ${i === factIdx ? 'active' : ''}`} />
              ))}
            </div>
          </div>

          {/* Event preview */}
          <div className="feast-preview">
            <div className="feast-preview-emoji">{getEventEmoji(eventName)}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="feast-preview-title" style={{ textTransform: 'capitalize' }}>{eventName} Preview</div>
              <div className="feast-preview-body">With {totalBanked} kcal banked, enjoy your {eventName} — no guilt, no tracking.</div>
            </div>
            <div className="feast-preview-badge" style={isDone ? { background: 'rgba(34,197,94,0.25)', color: '#4ade80' } : {}}>
              {isDone ? '✓ READY' : 'SOON →'}
            </div>
          </div>

          <Ticker />
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════
  // STATE 3 – ACTIVE (feast is live, persists across sessions/
  //           new chats until cancelled or event_date passes)
  // Data always comes from feastStatus (API) so it's always fresh.
  // ══════════════════════════════════════════════════════════════
  const isFeastDay = feastStat === 'FEAST_DAY';
  const statusLabel = isFeastDay ? '🎊 FEAST DAY!' : `🏦 ${daysRemaining}d left`;
  const statusColor = isFeastDay ? '#fbbf24' : '#a5b4fc';

  return (
    <div className="feast-right-panel">
      <div className="feast-rp-inner">

        {/* Hero — static active state */}
        <div className="feast-hero-card">
          <div className="feast-hero-bg-glow done" />
          <div className="feast-orb-wrap">
            <div className="feast-orb done">🔥</div>
            <div className="feast-orbit-ring">
              <div className="feast-orbit-dot done" />
            </div>
          </div>
          <div className="feast-hero-title">🎉 Feast Mode Active!</div>
          <div className="feast-hero-sub" style={{ color: statusColor }}>{statusLabel}</div>
          {/* Fully-filled ring */}
          <div className="feast-ring-wrap">
            <svg viewBox="0 0 100 100">
              <circle className="feast-ring-track" cx="50" cy="50" r="42" />
              <circle className="feast-ring-fill done" cx="50" cy="50" r="42" style={{ strokeDashoffset: 0 }} />
            </svg>
            <div className="feast-ring-pct">✓</div>
          </div>
          <div className="feast-step-dots">
            {STEPS.map((_, i) => (
              <div key={i} className="feast-step-dot active done" />
            ))}
          </div>
        </div>

        {/* Event details card */}
        <div className="feast-section-card">
          <div className="feast-eyebrow">YOUR FEAST PLAN</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <FeastDetailRow label="Event" val={eventName} capitalize />
            <FeastDetailRow label="Date" val={eventDate} />
            <FeastDetailRow label="Adjusting" val={getMealLabel(selectedMeals)} />
            <FeastDetailRow label="Daily Cut" val={`-${dailyDeduction} kcal`} color="#f87171" />
            <FeastDetailRow label="Banked" val={`+${totalBanked} kcal`} color="#4ade80" />
            <FeastDetailRow label="Workout" val={getWorkoutLabel(workoutPref)} color="#a5b4fc" />
          </div>
        </div>

        {/* Unlocks — all revealed */}
        <div className="feast-section-card">
          <div className="feast-eyebrow">ACTIVE UNLOCKS</div>
          <div className="feast-unlock-grid">
            {UNLOCKS.map((u, i) => (
              <div key={i} className="feast-unlock-item revealed">
                <div className="feast-unlock-name">{u.name}</div>
                <div className="feast-unlock-val" style={{ color: u.color }}>{u.val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Tips */}
        <div className="feast-section-card">
          <div className="feast-eyebrow">DID YOU KNOW?</div>
          <div className={`feast-tip-inner ${tipHidden ? 'feast-tip-hidden' : ''}`}>
            <div className="feast-tip-emoji">{currentFact.icon}</div>
            <div>
              <div className="feast-tip-title">{currentFact.title}</div>
              <div className="feast-tip-body">{currentFact.body}</div>
            </div>
          </div>
          <div className="feast-tip-dots">
            {FACTS.map((_, i) => (
              <div key={i} className={`feast-tip-dot ${i === factIdx ? 'active' : ''}`} />
            ))}
          </div>
        </div>

        {/* Event preview — always READY */}
        <div className="feast-preview">
          <div className="feast-preview-emoji">{getEventEmoji(eventName)}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="feast-preview-title" style={{ textTransform: 'capitalize' }}>{eventName} Preview</div>
            <div className="feast-preview-body">With {totalBanked} kcal banked, enjoy your {eventName} — no guilt, no tracking.</div>
          </div>
          <div className="feast-preview-badge" style={{ background: 'rgba(34,197,94,0.25)', color: '#4ade80' }}>✓ READY</div>
        </div>

        <Ticker />
      </div>
    </div>
  );
};

// ── Shared sub-components ──

const Ticker = () => (
  <div className="feast-ticker">
    <span className="feast-ticker-label">LIVE</span>
    <div className="feast-ticker-divider" />
    <div className="feast-ticker-scroll">
      <span className="feast-ticker-inner">
        🏃 Sarah just completed Feast Mode &nbsp;·&nbsp;
        🔥 Mike burned 420 extra kcal &nbsp;·&nbsp;
        🎉 Feast Mode users are 3× more likely to stay on track &nbsp;·&nbsp;
        💡 Drink water before the party to reduce cravings &nbsp;·&nbsp;
        🏆 You're in the top 15% of users this week &nbsp;·&nbsp;
      </span>
    </div>
  </div>
);

const FeastDetailRow = ({ label, val, color, capitalize }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
    <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{label}</span>
    <span style={{
      fontSize: 12, fontWeight: 700,
      color: color ?? 'white',
      textTransform: capitalize ? 'capitalize' : undefined,
      maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
    }}>{val}</span>
  </div>
);

export default FeastModePanel;
