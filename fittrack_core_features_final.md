# FitTrack Admin Panel — Core Features

> Focused on what an admin **actually needs to control** — master data, user oversight, platform config, and monitoring.

---

## 1. 👥 User Management
**The most essential admin function.** Every support request starts here.

- **View & search all users** — find by name, email, registration date
- **View user detail** — profile stats, fitness config, calculated macros
- **Deactivate / delete user** — with cascade to all related data
- **Reset password** — admin-triggered reset

---

## 2. 🥗 Food Item Database
**This is the brain of the meal planner.** Bad food data = bad meal plans.

- **View all foods** — search, filter by diet type (veg/non-veg), meal type, region
- **Add new food item** — with all nutritional fields (calories, protein, carbs, fat, serving size)
- **Edit food item** — correct wrong nutritional data, fix diet type
- **Delete food item** — remove incorrect or duplicate foods
- **Bulk import / export** — CSV upload for large datasets

---

## 3. 💪 Exercise Database
**The source of truth for workout recommendations and AI Coach suggestions.**

- **View all exercises** — filter by muscle group, category (strength/cardio), difficulty
- **Add new exercise** — name, muscle group, category, difficulty, image URL
- **Edit exercise** — correct data, upload/replace image
- **Delete exercise**
- **Bulk import / export** — CSV upload

---

## 4. 🎉 Feast Mode Oversight
**Feast Mode is a core differentiator — admin must be able to monitor and intervene.**

- **View all active & completed feasts** — across all users
- **View feast detail** — event name, dates, daily deduction, calories banked, current status
- **View banking progress** — calories banked vs. target

---

## 5. 📈 Analytics Dashboard
**High-level visibility into how the platform is performing.**

- **User stats** — total users, new signups (weekly/monthly), active users
- **Plan generation stats** — how many diet & workout plans generated
- **AI Coach usage** — total messages, sessions, avg per user
- **Feast Mode stats** — active feasts, completion rate
- **Top foods & exercises** — most logged items across all users

---

## 6. ⚙️ System Settings
**Operational control over the app's core engine.**

- **LLM configuration** — switch provider (Ollama / OpenAI), choose model, update API key
- **Celery task monitor** — view scheduled background tasks, check if they are running
- **Database health** — connection status, Alembic migration status

---

> **Paused / Deferred:**
> - Notifications — on hold, not part of current build scope

---

## Recommended Build Order

> Updated based on current scope. Notifications are paused and excluded from V1.

| Priority | Module | Why |
|---|---|---|
| 1 | User Management | Foundation — every support task needs this |
| 2 | Food Item Database | Powers meal plans; bad data = broken plans |
| 3 | Exercise Database | Powers workout plans and AI Coach suggestions |
| 4 | Feast Mode Oversight | Core feature that needs monitoring |
| 5 | Analytics Dashboard | Visibility into platform health |
| 6 | System Settings | LLM + infra control |

---

> **Paused / Deferred:**
> - Notifications — on hold, not part of current build scope
