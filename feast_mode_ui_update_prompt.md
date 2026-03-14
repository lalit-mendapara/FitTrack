# UI Update Prompt — Feast Mode Activation Panel

## Context

I have an existing chatbot application (AI Fitness Coach). I want you to **update only the UI** — do not change any backend logic, API calls, or bot response logic. A reference HTML file (`feast_mode_v2.html`) is attached. Use it as the visual and structural reference.

---

## What To Understand First — The Feast Mode Flow

Before touching any code, understand this specific flow:

1. **User mentions an upcoming event** (birthday party, wedding, festival, dinner, etc.) in the chat.
2. The **bot detects the event** and proactively suggests activating "Feast Mode" — a calorie-banking strategy that lets the user enjoy the event guilt-free.
3. The bot sends a **Feast Strategy Card** inside the chat bubble (inline card — not a popup). This card shows:
   - Event name + days away
   - Daily calorie deficit slider (adjustable)
   - Total calories banked & daily target
   - Workout type selector (Standard / Cardio / Skip)
   - Primary muscle group recommendation
4. The user responds positively (e.g. "Let's activate it!").
5. The bot confirms and says "activating now — watch the panel on the right."
6. The **right panel switches to Feast Mode Activation state**, showing:
   - An animated orb (breathing + orbit ring + spinning dot)
   - A circular progress ring filling from 0% → 100%
   - Step-by-step status text updating as progress fills (e.g. "Calculating calorie bank…", "Syncing workout history…", etc.)
   - Step indicator dots animating as each phase completes
   - Progressive unlock cards revealing at 20/40/60/80% (Bonus Calories, Meal Flexibility, Workout Credit, Streak Saved)
   - A "Did You Know?" rotating tips section
   - A Party/Event preview card at the bottom
   - A live activity ticker at the very bottom
7. When progress hits 100%, everything transitions to **"done" state**:
   - Orb changes from indigo/purple → amber/orange glow
   - Ring stroke turns amber
   - Step dots turn amber
   - Background glow shifts to warm amber
   - "SOON →" badge on party preview flips to "✓ READY" in green
   - Confetti burst fires
   - Bot sends a final confirmation message in chat: "🎉 Feast Mode is now active! Your X kcal bank is confirmed. On party day, forget calorie counting — just enjoy!"

This is the **one flow that must be pixel-perfect**. Everything else (header, chat bubbles, quick replies, input bar) just needs to adopt the same design language.

---

## What To Update

### 1. Overall App Shell & Layout
- **Split layout**: Chat area takes **70% width**, right panel takes **30% width**.
- Full viewport height, no scroll on the outer shell.
- Background: `#f0f2f5` for body; chat area is white; right panel is `#0f0d1f` (dark).

### 2. Header
Gradient: `linear-gradient(135deg, #6366f1, #8b5cf6)`  
- Bot avatar: rounded square (`border-radius: 12px`), semi-transparent white background, emoji icon.
- Title: white, bold. Subtitle: muted white with a pulsing green dot for "Online" status.
- Icons on right: history + new chat, white/muted.
- Box shadow: `0 2px 20px rgba(99,102,241,0.3)`

### 3. Chat Area (left 70%)
- Chat messages scroll area with subtle scrollbar.
- **Bot bubbles**: light gray background (`#f7f8fc`), thin border, top-left corner flat (`border-top-left-radius: 4px`).
- **User bubbles**: same indigo/purple gradient as header, white text, top-right corner flat.
- Bot avatar: same indigo gradient as header, rounded square.
- User avatar: light gray, rounded square.
- Typing indicator: three bouncing dots inside a bot-style bubble.
- **Feast Strategy Card** (inline in chat, max-width ~340px):
  - Card header: indigo/purple gradient with icon + title + subtitle
  - Card body: white background
  - Daily deficit slider with `accent-color: #6366f1`
  - Mini stats: 2-column grid — left cell purple-tinted (`#ede9fe`), right cell green-tinted (`#dcfce7`)
  - Workout type pills: 3 pills (Standard / Cardio / Skip), active pill is dark (`#1e293b`) with white text
  - Muscle group row: small key-value row at bottom of card
- Quick reply chips: pill-shaped buttons, active one uses indigo/purple gradient.
- Input bar: rounded input field, focus border turns indigo; round send button with indigo gradient.

### 4. Right Panel — Default State (no active flow)
When Feast Mode is NOT being activated, the right panel should show a neutral/default state — e.g. a simple summary of today's stats, streak, or a prompt card. Use the same dark panel (`#0f0d1f`) with frosted glass-style cards (`rgba(255,255,255,0.04)` background, `rgba(255,255,255,0.08)` border).

### 5. Right Panel — Feast Mode Activation State ⚡ (CRITICAL — pixel-perfect)

Trigger: when the bot starts activating Feast Mode, the right panel should transition into this state.

#### A. Hero Activation Card
- Dark card, `border-radius: 18px`, with a radial glow at the top that starts as indigo and transitions to amber on completion.
- **Orb**: 72×72px circle, breathing animation (`scale: 1 → 1.07`, loop), indigo radial gradient with purple glow. On done → amber/orange gradient with warm glow.
- **Orbit ring**: dashed circle around the orb, spinning slowly (9s). Contains a small dot that orbits. Dot is indigo → turns amber on done.
- **Title**: "Activating Feast Mode" → "🎉 Feast Mode Active!" on done.
- **Subtitle**: updates with each step text as progress advances.
- **Circular progress ring**: SVG circle, 80×80px, track is near-invisible (`rgba(255,255,255,0.08)`), fill is indigo (`#818cf8`) → amber (`#fbbf24`) on done. Shows percentage in center (monospace font).
- **Step dots**: pill-shaped dots, inactive = gray, active = indigo elongated pill. On done → amber.

#### B. Unlocks Grid
- `2×2` grid of unlock cards.
- Default: dimmed, scaled down slightly.
- Revealed progressively at 20/40/60/80% — animate in (opacity + scale).
- Each reveal shows the unlock name (small label) and value (bold, colored per unlock).

#### C. Did You Know Tips
- Rotates through fitness facts every ~3.4 seconds.
- Fade + slide-up transition between tips.
- Emoji icon in a frosted box, title + body text.
- Indicator dots at bottom, active dot turns indigo.

#### D. Event/Party Preview Card
- Gradient border card (indigo + amber tint).
- Shows event emoji, title ("Birthday Party Preview"), short description.
- Badge shows "SOON →" in indigo → transitions to "✓ READY" in green on activation complete.

#### E. Live Ticker
- Dark frosted card at the bottom of the right panel.
- "LIVE" label + scrolling text with social proof / tip messages (CSS marquee animation).

#### F. Confetti
- On activation complete: spawn ~55 confetti dots with random colors, falling from top of viewport, fade out. Clean up after 4 seconds.

---

## Styling Tokens (use these consistently everywhere)

| Token | Value |
|---|---|
| Primary gradient | `linear-gradient(135deg, #6366f1, #8b5cf6)` |
| Primary color | `#6366f1` |
| Done/amber color | `#fbbf24` |
| Dark panel bg | `#0f0d1f` |
| Card surface | `rgba(255,255,255,0.04)` |
| Card border | `rgba(255,255,255,0.08)` |
| Font — UI | `DM Sans` |
| Font — numbers | `JetBrains Mono` |
| Bot bubble bg | `#f7f8fc` |
| Bot bubble border | `#eaecf0` |
| User bubble | indigo/purple gradient |
| Border radius — cards | `16–18px` |
| Border radius — bubbles | `16px` |
| Border radius — avatars | `10–12px` |

---

## Animations Reference

| Name | Description |
|---|---|
| `breathe` | Orb scale 1 → 1.07 → 1, 2.2s loop |
| `spin` | Orbit ring 360° rotation, 9s linear |
| `ticker` | Horizontal scroll, 22s linear |
| `bounce` | Typing dots vertical bounce, 1.2s staggered |
| `pulse-dot` | Header online dot opacity pulse, 2s |
| `slideUp` | Chat message appear: translateY(10px) + opacity 0 → 1 |
| `fall` | Confetti dots fall from top + rotate + fade, 1.5–3.5s |

---

## What NOT To Change
- Do not modify any bot response logic or AI integration.
- Do not change the chat message data flow or state management.
- Do not alter any routing or screen navigation outside this chat view.
- Do not add new dependencies — use the existing stack.

---

## Deliverable

Update the existing chatbot UI to match the design system and Feast Mode activation flow described above, using `feast_mode_v2.html` as the pixel-level visual reference. The Feast Mode activation panel (right panel) must be an exact match. Other UI surfaces (header, chat bubbles, input bar) should adopt the same design language consistently.
