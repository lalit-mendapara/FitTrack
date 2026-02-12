# Feast Mode - Quick Start Guide

## What Was Created

I've created a comprehensive testing and management suite for the feast mode feature:

### 📁 Files Created

1. **[test_feast_mode.py](test_feast_mode.py)** (17KB)
   - Automated testing with state snapshots
   - Tests activation, mid-day, cancellation, and data integrity

2. **[feast_mode_manager.py](feast_mode_manager.py)** (17KB)
   - Interactive CLI for managing feast mode
   - User-friendly menus and prompts

3. **[diagnose_feast_mode.py](diagnose_feast_mode.py)** (15KB)
   - Quick diagnostics and issue detection
   - Auto-fix common problems

4. **[FEAST_MODE_IMPROVEMENTS.md](FEAST_MODE_IMPROVEMENTS.md)**
   - Comprehensive documentation of issues and solutions
   - Recommended code improvements
   - Frontend enhancement guidelines

5. **[README_FEAST_MODE.md](README_FEAST_MODE.md)**
   - Detailed usage guide for all scripts
   - Testing scenarios and troubleshooting

## Quick Start (5 Minutes)

### Step 1: Activate Virtual Environment
```bash
cd backend
source venv/bin/activate
```

### Step 2: Run Quick Diagnostic
```bash
# Check if your user has feast mode active
python scripts/diagnose_feast_mode.py --user-id 1
```

### Step 3: Test Feast Mode
```bash
# Run all automated tests
python scripts/test_feast_mode.py --user-id 1 --scenario all
```

### Step 4: Try Interactive Manager
```bash
# Launch interactive CLI
python scripts/feast_mode_manager.py
```

## Understanding the Current Issues

### The Problem
Your feast mode feature has these issues:
1. **AI Coach Detection**: Inconsistent - sometimes misses feast mode intents
2. **Data Transparency**: Changed values not visible across all components
3. **Reversibility**: Cancellation doesn't fully restore original state
4. **Mid-day Activation**: Works but not well-tested or user-friendly

### The Solution
I've provided:
1. **Testing Scripts**: Verify current behavior and catch regressions
2. **Management Tool**: Safely test feast mode operations
3. **Diagnostic Tool**: Identify and fix issues automatically
4. **Documentation**: Clear roadmap for improvements

## Testing Workflow

### Test 1: Check Current State
```bash
python scripts/diagnose_feast_mode.py --user-id YOUR_USER_ID
```
**Expected**: Shows if feast mode is active, current calories, any issues

### Test 2: Activate Feast Mode
```bash
python scripts/feast_mode_manager.py
# Select option 2 (Activate Feast Mode)
# Follow the prompts:
#   - Enter event name: "Test Wedding"
#   - Enter date: 2026-02-20
#   - Confirm: yes
```
**Expected**: Feast mode activates, calories reduced, meal plan adjusted

### Test 3: Verify Changes
```bash
python scripts/diagnose_feast_mode.py --user-id YOUR_USER_ID
```
**Expected**:
- Feast mode status: BANKING
- Calorie adjustment: Shows base → effective
- Meal plan consistency: Pass

### Test 4: Cancel Feast Mode
```bash
python scripts/feast_mode_manager.py
# Select option 3 (Cancel Feast Mode)
# Confirm: yes
```
**Expected**: Feast mode cancelled, original values restored

### Test 5: Verify Restoration
```bash
python scripts/diagnose_feast_mode.py --user-id YOUR_USER_ID
```
**Expected**: No active feast mode, calories back to normal

## Manual Testing with AI Coach

After automated testing, test via the AI Coach chatbot:

### Scenario 1: Natural Language Activation
```
You: "I have a wedding next Saturday and will eat a lot"

Expected Bot:
- Detects feast mode intent
- Proposes banking strategy
- Shows clear breakdown
- Asks for confirmation

You: "Yes"

Expected Bot:
- Activates feast mode
- Confirms what changed
- Shows adjusted meal plan
```

### Scenario 2: Mid-Day Activation
```
# First, log breakfast and lunch in the app

You: "I have a birthday party in 3 days"

Expected Bot:
- Proposes feast mode
- Mentions breakfast/lunch already eaten
- Says only remaining meals will adjust

You: "Activate"

Expected Bot:
- Activates feast mode
- Confirms dinner/snacks adjusted
- Shows breakdown
```

### Scenario 3: Cancellation
```
You: "Cancel feast mode"

Expected Bot:
- Asks for confirmation
- Explains what will be restored

You: "Yes"

Expected Bot:
- Cancels feast mode
- Confirms restoration
- Shows original values back
```

## Understanding Test Output

### Diagnostic Report
```
✓ User Exists        → User found in database
✓ Feast Mode Status  → Active/inactive status
✓ Calorie Adjustment → Math is correct
⚠ Workout Modification → Warning: check manually
✗ Meal Plan Consistency → Failed: needs fixing
```

### Color Coding
- 🟢 **Green (✓)**: All good, test passed
- 🔴 **Red (✗)**: Critical issue, needs fixing
- 🟡 **Yellow (⚠)**: Warning, should check but not critical
- 🔵 **Cyan (ℹ)**: Information, progress updates

## Common Issues & Fixes

### Issue: "Multiple active events"
```bash
python scripts/diagnose_feast_mode.py --user-id 1 --fix
```
Auto-fix will keep the most recent event and deactivate others.

### Issue: "Expired event still active"
```bash
python scripts/diagnose_feast_mode.py --user-id 1 --fix
```
Auto-fix will deactivate events with past dates.

### Issue: "Meal plan total doesn't match target"
This indicates the adjustment logic may need tuning. Check logs:
```bash
docker-compose logs -f backend | grep -i "feast\|meal"
```

## Next Steps After Testing

### If All Tests Pass ✅
1. Test manually via AI Coach
2. Check frontend components show adjusted values
3. Monitor for any edge cases
4. Deploy to production

### If Tests Fail ❌
1. Review [FEAST_MODE_IMPROVEMENTS.md](FEAST_MODE_IMPROVEMENTS.md)
2. Implement recommended code changes
3. Re-run tests to verify fixes
4. Consider implementing backup/restore enhancements

## Key Improvements Recommended

### Backend
1. **Add backup fields** to SocialEvent model (store original state)
2. **Enhance AI Coach** detection with better prompts
3. **Improve restoration** logic to use backup instead of recalculation

### Frontend
1. **Add visual indicators** showing feast mode is active
2. **Show base vs. effective** targets in dashboard
3. **Display adjusted meals** with clear indicators
4. **Add feast mode banner** to diet plan page

See [FEAST_MODE_IMPROVEMENTS.md](FEAST_MODE_IMPROVEMENTS.md) for detailed code examples.

## Getting Help

### Read Documentation
- [README_FEAST_MODE.md](README_FEAST_MODE.md) - Full guide for all scripts
- [FEAST_MODE_IMPROVEMENTS.md](FEAST_MODE_IMPROVEMENTS.md) - Issues and solutions

### Check Logs
```bash
# Backend logs
docker-compose logs -f backend

# Database logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

### Run Diagnostics
```bash
# Always start with diagnostics
python scripts/diagnose_feast_mode.py --user-id YOUR_USER_ID

# Try auto-fix
python scripts/diagnose_feast_mode.py --user-id YOUR_USER_ID --fix
```

## Summary

You now have:
- ✅ **3 Testing Scripts** - Automated testing, interactive management, diagnostics
- ✅ **Comprehensive Documentation** - Issues, solutions, and testing guide
- ✅ **Quick Start Guide** - This file!
- ✅ **Executable Scripts** - Ready to run

**Your Next Action:**
```bash
cd backend
source venv/bin/activate
python scripts/feast_mode_manager.py
```

This will launch the interactive manager where you can safely test feast mode operations.

**Important**: Always test with a test user first before using on production data!

## Questions?

Refer to:
1. [README_FEAST_MODE.md](README_FEAST_MODE.md) for detailed script usage
2. [FEAST_MODE_IMPROVEMENTS.md](FEAST_MODE_IMPROVEMENTS.md) for code improvements
3. Script help: `python scripts/test_feast_mode.py --help`

Happy testing! 🎉
