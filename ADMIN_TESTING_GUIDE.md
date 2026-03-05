# FitTrack Admin Panel - Manual Testing Guide

## Prerequisites
- Docker containers running: `docker compose up -d`
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Default admin credentials created

---

## Phase 1: Admin Authentication Testing

### Test 1.1: Admin Login - Success Case
**Steps:**
1. Open browser and navigate to `http://localhost:5173/admin/login`
2. Enter credentials:
   - Email: `lalit@gmail.com`
   - Password: `Lalit@123`
3. Click "Sign In"

**Expected Results:**
- ✅ Redirects to `/admin/dashboard`
- ✅ Admin dashboard displays with sidebar navigation
- ✅ User email shown in sidebar footer
- ✅ Browser localStorage contains `admin_token` and `admin_user`

**Verification Commands:**
```bash
# Check browser console (F12)
localStorage.getItem('admin_token')  # Should return JWT token
localStorage.getItem('admin_user')   # Should return admin user object

# Verify in database
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT * FROM admins;"
```

---

### Test 1.2: Admin Login - Invalid Credentials
**Steps:**
1. Navigate to `http://localhost:5173/admin/login`
2. Enter wrong credentials:
   - Email: `wrong@email.com`
   - Password: `wrongpassword`
3. Click "Sign In"

**Expected Results:**
- ✅ Error message displayed: "Incorrect email or password"
- ✅ Stays on login page
- ✅ No token stored in localStorage

---

### Test 1.3: Admin Protected Routes
**Steps:**
1. Clear localStorage: `localStorage.clear()`
2. Try to access `http://localhost:5173/admin/dashboard` directly

**Expected Results:**
- ✅ Redirects to `/admin/login`
- ✅ Cannot access dashboard without authentication

---

### Test 1.4: Admin Logout
**Steps:**
1. Login as admin
2. Navigate to dashboard
3. Click "Logout" in sidebar footer

**Expected Results:**
- ✅ Redirects to `/admin/login`
- ✅ localStorage cleared (no `admin_token` or `admin_user`)
- ✅ Cannot access protected routes anymore

---

### Test 1.5: API Endpoint Testing
**Test admin login API directly:**
```bash
# Successful login
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"lalit@gmail.com","password":"Lalit@123"}'

# Expected: Returns access_token and admin object
```

**Test protected endpoint:**
```bash
# Get current admin info (replace TOKEN with actual token)
curl -X GET http://localhost:8000/api/admin/me \
  -H "Authorization: Bearer TOKEN"

# Expected: Returns admin user details
```

---

## Phase 2: User Management Module Testing

### Test 3.1: View Dashboard with Real Stats
**Steps:**
1. Login as admin
2. Navigate to dashboard at `http://localhost:5173/admin/dashboard`
3. Observe the stats cards

**Expected Results:**
- ✅ Total Users shows actual count from database
- ✅ Total Foods shows actual count
- ✅ Total Exercises shows actual count
- ✅ Active Feasts shows actual count
- ✅ Stats load dynamically (not hardcoded "-")

**Verification Commands:**
```bash
# Check user count
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT COUNT(*) FROM users;"

# Check food items count
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT COUNT(*) FROM food_items;"

# Check exercises count
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT COUNT(*) FROM exercises;"

# Check active feasts
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT COUNT(*) FROM feast_configs WHERE status='active';"
```

---

### Test 3.2: View User List
**Steps:**
1. Login as admin
2. Click "View Users" quick action OR navigate to `/admin/users`
3. Observe the user list table

**Expected Results:**
- ✅ Shows all registered users in a table
- ✅ Displays: ID, Name, Email, Age, Gender
- ✅ Shows total user count
- ✅ Pagination controls visible if more than 20 users
- ✅ Each user has "View Details" button

**API Test:**
```bash
# Get admin token first (from login response)
TOKEN="your_admin_token_here"

# List users
curl -X GET "http://localhost:8000/api/admin/users?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Returns users array with pagination info
```

---

### Test 3.3: Search Users
**Steps:**
1. On `/admin/users` page
2. Type a user's name or email in search box
3. Observe filtered results

**Expected Results:**
- ✅ Table updates with matching users only
- ✅ Search works for both name and email
- ✅ Total count updates to show filtered count
- ✅ Pagination resets to page 1

**API Test:**
```bash
# Search by email
curl -X GET "http://localhost:8000/api/admin/users?search=gmail" \
  -H "Authorization: Bearer $TOKEN"
```

---

### Test 3.4: View User Detail
**Steps:**
1. On user list page, click "View Details" for any user
2. Observe user detail page

**Expected Results:**
- ✅ Shows basic information (ID, name, email, age, gender, DOB)
- ✅ Shows fitness profile if exists (weight, height, goals, activity level)
- ✅ Shows calculated macros (calories, protein, carbs, fat)
- ✅ Shows activity summary (active feasts count)
- ✅ "Reset Password" button visible
- ✅ "Delete User" button visible
- ✅ "Back to Users" link works

**API Test:**
```bash
# Get user detail (replace 1 with actual user ID)
curl -X GET "http://localhost:8000/api/admin/users/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### Test 3.5: Reset User Password
**Steps:**
1. On user detail page
2. Click "Reset Password" button
3. Enter new password (min 8 characters)
4. Click "Reset Password" in modal

**Expected Results:**
- ✅ Modal appears with password input
- ✅ Shows validation for minimum 8 characters
- ✅ Success alert appears after reset
- ✅ Modal closes automatically
- ✅ User can now login with new password

**API Test:**
```bash
# Reset password for user ID 1
curl -X POST "http://localhost:8000/api/admin/users/1/reset-password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"new_password":"NewPass123"}'

# Expected: Success message
```

**Verification:**
```bash
# User should be able to login with new password
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@email.com","password":"NewPass123"}'
```

---

### Test 3.6: Delete User
**Steps:**
1. On user detail page
2. Click "Delete User" button
3. Confirm deletion in modal
4. Observe redirect to user list

**Expected Results:**
- ✅ Confirmation modal appears with warning
- ✅ Shows user name in confirmation message
- ✅ After confirmation, user is deleted
- ✅ Redirects to `/admin/users`
- ✅ User no longer appears in list
- ✅ All related data deleted (cascade)

**API Test:**
```bash
# Delete user (replace 1 with actual user ID)
curl -X DELETE "http://localhost:8000/api/admin/users/1" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Success message with deleted user ID
```

**Verification:**
```bash
# Check user is deleted
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT * FROM users WHERE id=1;"

# Expected: No rows returned
```

---

### Test 3.7: Pagination
**Steps:**
1. On user list page (if you have more than 20 users)
2. Click "Next" button
3. Observe page 2 results
4. Click "Previous" button

**Expected Results:**
- ✅ Shows "Page X of Y" indicator
- ✅ Next button loads next 20 users
- ✅ Previous button goes back
- ✅ Buttons disabled appropriately (Previous on page 1, Next on last page)
- ✅ URL updates with page parameter

---

## Database Migration Testing

### Test 2.1: Check Migration Status
```bash
# View current migration version
docker compose exec backend alembic current

# Expected output: Shows current revision (992161264b12)
```

### Test 2.2: View Migration History
```bash
# View all migrations
docker compose exec backend alembic history

# Expected: Shows migration history including "add_admin_table"
```

### Test 2.3: Verify Admin Table Structure
```bash
# Check admin table schema
docker compose exec postgres psql -U diet_user -d fitness_track -c "\d admins"

# Expected columns:
# - id (integer, primary key)
# - email (varchar, unique)
# - hashed_password (varchar)
# - full_name (varchar)
# - is_active (boolean)
# - is_super_admin (boolean)
# - created_at (timestamp)
# - updated_at (timestamp)
# - last_login (timestamp)
```

### Test 2.4: Verify Default Admin Created
```bash
# Check admin record
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT id, email, full_name, is_super_admin, is_active FROM admins;"

# Expected output:
# id | email              | full_name              | is_super_admin | is_active
# ----+--------------------+------------------------+----------------+-----------
#  1 | lalit@gmail.com    | Lalit (Super Admin)    | t              | t
```

---

## Docker Commands Reference

### Container Management
```bash
# View all running containers
docker compose ps

# View backend logs
docker compose logs -f backend

# Restart backend after code changes
docker compose restart backend

# Rebuild backend (after dependency changes)
docker compose build backend
docker compose up -d backend
```

### Database Operations
```bash
# Access PostgreSQL shell
docker compose exec postgres psql -U diet_user -d fitness_track

# Run SQL query
docker compose exec postgres psql -U diet_user -d fitness_track -c "SELECT * FROM admins;"

# Backup database
docker compose exec postgres pg_dump -U diet_user fitness_track > backup_$(date +%Y%m%d).sql
```

### Alembic Migration Commands
```bash
# Generate new migration (auto-detect model changes)
docker compose exec backend alembic revision --autogenerate -m "migration_name"

# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Rollback last migration
docker compose exec backend alembic downgrade -1

# View current migration version
docker compose exec backend alembic current

# View migration history
docker compose exec backend alembic history --verbose
```

### Admin Management Scripts
```bash
# Seed default admin (if not exists)
docker compose exec backend python scripts/seed_admin.py

# Expected output:
# ✓ Created default admin user: lalit@gmail.com
# OR
# ✓ Admin user 'lalit@gmail.com' already exists
```

---

## Common Issues & Troubleshooting

### Issue 1: "Module not found" errors
**Solution:**
```bash
# Rebuild backend container
docker compose build backend
docker compose restart backend
```

### Issue 2: Migration conflicts
**Solution:**
```bash
# Check current migration status
docker compose exec backend alembic current

# If needed, downgrade and re-apply
docker compose exec backend alembic downgrade -1
docker compose exec backend alembic upgrade head
```

### Issue 3: Admin login fails with 401
**Checklist:**
- ✅ Default admin created? Run `docker compose exec backend python scripts/seed_admin.py`
- ✅ Correct credentials? Email: `lalit@gmail.com`, Password: `Lalit@123`
- ✅ Backend running? Check `docker compose logs backend`

### Issue 4: CORS errors in browser
**Solution:**
- Verify frontend is accessing `http://localhost:8000` (not different port)
- Check backend CORS settings in `main.py` include `http://localhost:5173`

---

## Next Steps - Modules to Build

### Module 1: User Management (Priority 1)
- [ ] Backend: GET /api/admin/users (list with pagination)
- [ ] Backend: GET /api/admin/users/{id} (user details)
- [ ] Backend: PUT /api/admin/users/{id}/deactivate
- [ ] Backend: DELETE /api/admin/users/{id}
- [ ] Backend: POST /api/admin/users/{id}/reset-password
- [ ] Frontend: /admin/users (user list page)
- [ ] Frontend: /admin/users/{id} (user detail page)

### Module 2: Food Item Database (Priority 2)
- [ ] Backend: CRUD APIs for food items
- [ ] Backend: Bulk import/export CSV
- [ ] Frontend: Food list with filters
- [ ] Frontend: Add/Edit food forms

### Module 3: Exercise Database (Priority 3)
- [ ] Backend: CRUD APIs for exercises
- [ ] Backend: Bulk import/export CSV
- [ ] Frontend: Exercise list with filters
- [ ] Frontend: Add/Edit exercise forms

### Module 4: Feast Mode Oversight (Priority 4)
- [ ] Backend: GET /api/admin/feasts
- [ ] Backend: GET /api/admin/feasts/{id}
- [ ] Frontend: Feast list and detail pages

### Module 5: Analytics Dashboard (Priority 5)
- [ ] Backend: Analytics aggregation APIs
- [ ] Frontend: Dashboard with charts and stats

### Module 6: System Settings (Priority 6)
- [ ] Backend: LLM config APIs
- [ ] Backend: Celery task monitoring
- [ ] Backend: Database health check
- [ ] Frontend: Settings page

---

## Testing Checklist Summary

### ✅ Completed
- [x] Admin model created with Alembic migration
- [x] Admin table exists in database
- [x] Default admin seeded (lalit@gmail.com)
- [x] Admin login API working
- [x] JWT authentication implemented
- [x] Password hashing with argon2
- [x] Admin login frontend page
- [x] Protected route middleware
- [x] Admin dashboard layout
- [x] Sidebar navigation

### 🔄 In Progress
- [ ] User Management module
- [ ] Food Database module
- [ ] Exercise Database module
- [ ] Feast Mode Oversight
- [ ] Analytics Dashboard
- [ ] System Settings

---

## Security Notes

✅ **Implemented:**
- Passwords hashed with argon2
- JWT tokens for authentication
- Protected routes on frontend
- Admin-only API endpoints with Bearer token verification

⚠️ **Recommendations:**
- Use HTTPS in production
- Implement rate limiting on login endpoint
- Add refresh token mechanism
- Set appropriate JWT expiry (currently 24 hours)
- Enable CSRF protection for state-changing operations
