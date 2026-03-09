# Analytics Dashboard - Quick Start Guide

## Access the Analytics Dashboard

1. **Login to Admin Panel:**
   ```
   URL: http://localhost:5173/admin/login
   Email: lalit@gmail.com
   Password: Lalit@123
   ```

2. **Navigate to Analytics:**
   - Click the **Analytics** (📈) menu item in the sidebar
   - Or go directly to: `http://localhost:5173/admin/analytics`

---

## Features Overview

### 📊 AI Coach Statistics (Top Row Cards)
- **Total Chat Sessions** - Total number of AI coach conversations
- **Total Messages** - Total messages exchanged
- **Avg Messages/Session** - Average messages per conversation
- **Active Sessions (7d)** - Recent activity in last 7 days

### 📈 Charts & Visualizations

1. **User Growth Chart** (Line Chart)
   - Shows user registration trends over 12 months
   - Helps identify growth patterns

2. **Plan Generation Chart** (Bar Chart)
   - Compares meal plans vs workout plans
   - Shows total and last 30 days activity

3. **Feast Mode Status** (Pie Chart)
   - Active, Completed, and Cancelled feasts
   - Displays average banking days

4. **Gender Distribution** (Pie Chart)
   - Male vs Female user breakdown
   - Color-coded visualization

5. **Age Distribution** (Bar Chart)
   - Age ranges: 18-25, 26-35, 36-45, 46-55, 56+
   - Helps understand user demographics

### 📋 Summary Cards

**Plan Generation Summary:**
- Total Meal Plans generated
- Total Workout Plans generated

**Feast Mode Summary:**
- Total Feasts created
- Currently Active feasts

---

## Backend API Endpoints

All endpoints require admin authentication (Bearer token):

```bash
# User Growth Data
GET /api/admin/analytics/user-growth

# Plan Generation Statistics
GET /api/admin/analytics/plan-generation-stats

# AI Coach Usage
GET /api/admin/analytics/ai-coach-usage

# Feast Mode Statistics
GET /api/admin/analytics/feast-mode-stats

# User Demographics
GET /api/admin/analytics/user-demographics
```

---

## Quick Testing Commands

### Verify Backend is Running:
```bash
docker compose ps backend
```

### Check Analytics Data:
```bash
# Total users
docker compose exec postgres psql -U lalit -d fitness_track -c "SELECT COUNT(*) FROM users;"

# Total feasts
docker compose exec postgres psql -U lalit -d fitness_track -c "SELECT COUNT(*) FROM feast_configs;"

# Gender distribution
docker compose exec postgres psql -U lalit -d fitness_track -c "SELECT gender, COUNT(*) FROM users WHERE gender IS NOT NULL GROUP BY gender;"
```

### View Backend Logs:
```bash
docker compose logs -f backend
```

### Restart Backend (if needed):
```bash
docker compose restart backend
```

---

## Troubleshooting

### Charts not loading?
1. Check browser console for errors (F12)
2. Verify backend is running: `docker compose ps`
3. Check network requests in DevTools

### Authentication errors?
1. Clear browser localStorage
2. Login again
3. Check token hasn't expired (24 hour validity)

### Data looks incorrect?
1. Verify database has data
2. Check backend logs for errors
3. Test API endpoints directly at `http://localhost:8000/docs`

---

## Technology Stack

- **Frontend:** React + Recharts (for charts)
- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL
- **Charts Library:** Recharts (Line, Bar, Pie charts)

---

## Next Steps

After reviewing analytics, you can:
- Navigate to **Users** to manage user accounts
- Go to **Foods** to manage food database
- Check **Exercises** for workout management
- View **Feast Mode** for feast configurations
- Access **Dashboard** for quick overview

---

**Need Help?** Check `ANALYTICS_TESTING_GUIDE.md` for comprehensive testing instructions.
