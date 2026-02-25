# Feast Mode Testing & Management Scripts

## Overview

This directory contains comprehensive testing and management tools for the Feast Mode feature. These scripts help you:
- Test feast mode functionality
- Diagnose issues
- Manage feast mode interactively
- Verify data integrity

## Prerequisites

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

## Scripts

### 1. test_feast_mode.py - Comprehensive Testing Suite

**Purpose**: Automated testing of feast mode with state verification

**Features**:
- ✅ Test activation flow
- ✅ Test mid-day activation (after eating meals)
- ✅ Test cancellation and restoration
- ✅ Test data integrity across operations
- ✅ Snapshot comparison before/after changes

**Usage**:
```bash
# Run all tests
python scripts/test_feast_mode.py --user-id 1 --scenario all

# Test activation only
python scripts/test_feast_mode.py --user-id 1 --scenario activation

# Test mid-day activation
python scripts/test_feast_mode.py --user-id 1 --scenario midday

# Test cancellation
python scripts/test_feast_mode.py --user-id 1 --scenario cancel

# Test data integrity
python scripts/test_feast_mode.py --user-id 1 --scenario integrity
```

**Output Example**:
```
============================================================
           TEST 1: Feast Mode Activation
============================================================

ℹ Step 1: Capturing original state...
✓ Original calories: 2000
✓ Original meal plan items: 4

ℹ Step 2: Proposing feast mode...
✓ Proposal created:
ℹ   Event: Test Event on 2026-02-15
ℹ   Daily deduction: 200 kcal
ℹ   Total banked: 600 kcal

ℹ Step 3: Activating feast mode...
✓ Event created with ID: 123

...
```

### 2. feast_mode_manager.py - Interactive Management Tool

**Purpose**: User-friendly CLI for managing feast mode

**Features**:
- ✅ Check feast mode status
- ✅ Activate feast mode with interactive prompts
- ✅ Cancel feast mode with confirmation
- ✅ View user profile and meal plan
- ✅ View feast mode history

**Usage**:
```bash
python scripts/feast_mode_manager.py
```

**Interactive Menu**:
```
Feast Mode Manager
────────────────────────────────────────
1. Check Feast Mode Status
2. Activate Feast Mode
3. Cancel Feast Mode
4. View User Profile
5. View Meal Plan
6. View Feast Mode History
0. Exit
────────────────────────────────────────
Select option:
```

**Example Flow**:
```bash
# Start the manager
python scripts/feast_mode_manager.py

# Select user (shows list of users)
Enter User ID: 1

# Check status
Select option: 1
# Shows current feast mode status, effective calories, recent events

# Activate feast mode
Select option: 2
# Interactive prompts guide you through:
# - Event name
# - Event date
# - Confirmation with proposal details

# Cancel feast mode
Select option: 3
# Shows what will be restored
# Confirms cancellation
```

### 3. diagnose_feast_mode.py - Diagnostic Tool

**Purpose**: Quickly diagnose feast mode issues

**Features**:
- ✅ Verify user and profile exist
- ✅ Check feast mode status
- ✅ Validate calorie calculations
- ✅ Check meal plan consistency
- ✅ Verify workout modifications
- ✅ Detect expired or duplicate events
- ✅ Auto-fix common issues

**Usage**:
```bash
# Run diagnostics
python scripts/diagnose_feast_mode.py --user-id 1

# Run diagnostics with auto-fix
python scripts/diagnose_feast_mode.py --user-id 1 --fix

# Verbose output
python scripts/diagnose_feast_mode.py --user-id 1 --verbose
```

**Output Example**:
```
======================================================================
                   Diagnostic Report
======================================================================

Checks Performed:

✓ User Exists
  User: John Doe (john@example.com)
✓ User Profile
  Calories: 2000, Goal: weight_loss
✓ Feast Mode Status
  BANKING - Event: Wedding (2026-02-20)
✓ Event Date
  Event in 8 days
✓ Calorie Adjustment
  Base: 2000 → Effective: 1750 (-250)
✓ Meal Plan Consistency
  Total: 1800 kcal (Target: 1750)
⚠ Workout Modification
  No workout found for event day (Saturday)

Warnings:

1. Feast mode should add workout on event day

Summary:
  Total Checks: 7
  Passed: 6
  Failed: 0
  Warnings: 1
  Issues: 0
```

## Common Testing Scenarios

### Scenario 1: Fresh Activation
```bash
# 1. Check current status
python scripts/diagnose_feast_mode.py --user-id 1

# 2. Activate feast mode
python scripts/feast_mode_manager.py
# Select option 2, follow prompts

# 3. Verify activation
python scripts/test_feast_mode.py --user-id 1 --scenario activation
```

### Scenario 2: Mid-Day Activation
```bash
# 1. Simulate eating meals (use manager or app)
# Log breakfast and lunch

# 2. Test mid-day activation
python scripts/test_feast_mode.py --user-id 1 --scenario midday

# 3. Verify only remaining meals adjusted
python scripts/diagnose_feast_mode.py --user-id 1
```

### Scenario 3: Cancellation & Restoration
```bash
# 1. Ensure feast mode is active
python scripts/diagnose_feast_mode.py --user-id 1

# 2. Test cancellation
python scripts/test_feast_mode.py --user-id 1 --scenario cancel

# 3. Verify restoration
python scripts/diagnose_feast_mode.py --user-id 1
# Should show "No active feast mode"
```

### Scenario 4: Data Integrity
```bash
# Run comprehensive integrity tests
python scripts/test_feast_mode.py --user-id 1 --scenario integrity

# This tests:
# - Activate → Cancel → Verify restoration
# - Activate → Activate again → Verify replacement
# - Multiple operations → Verify no data corruption
```

### Scenario 5: Fixing Issues
```bash
# 1. Diagnose issues
python scripts/diagnose_feast_mode.py --user-id 1

# 2. Auto-fix common issues
python scripts/diagnose_feast_mode.py --user-id 1 --fix

# Common issues fixed automatically:
# - Expired events (event_date < today)
# - Duplicate active events (keeps most recent)
```

## Manual Testing with AI Coach

### Test 1: Initial Proposal
```
User: "I have a wedding on Saturday"

Expected Bot Response:
- Detects feast mode intent
- Proposes banking strategy
- Shows clear breakdown:
  * Event details
  * Daily deduction
  * Total banked
  * What will change
- Asks for confirmation
```

### Test 2: Confirmation
```
User: "Yes" or "Activate"

Expected Bot Response:
- Activates feast mode
- Confirms activation
- Shows adjusted values
- If mid-day: mentions which meals affected
```

### Test 3: Cancellation
```
User: "Cancel feast mode"

Expected Bot Response:
- Asks for confirmation
- Explains what will be restored
- Cancels and restores data
```

## Troubleshooting

### Issue: "User not found"
**Solution**: Verify user ID exists
```bash
# Check users in database
psql -U your_username -d fitness_track -c "SELECT id, name, email FROM users;"
```

### Issue: "No profile found"
**Solution**: User needs to complete profile setup
```bash
# Check if profile exists
python scripts/diagnose_feast_mode.py --user-id 1
```

### Issue: "Meal plan not adjusting"
**Solution**: Run diagnostics to identify the issue
```bash
python scripts/diagnose_feast_mode.py --user-id 1 --fix
```

### Issue: "Multiple active events"
**Solution**: Auto-fix will keep most recent
```bash
python scripts/diagnose_feast_mode.py --user-id 1 --fix
```

### Issue: "Expired event still active"
**Solution**: Auto-fix will deactivate expired events
```bash
python scripts/diagnose_feast_mode.py --user-id 1 --fix
```

## Script Output Color Guide

- **Green (✓)**: Success, passed checks
- **Red (✗)**: Failure, critical issues
- **Yellow (⚠)**: Warnings, non-critical issues
- **Cyan (ℹ)**: Information, progress updates

## Best Practices

1. **Always run diagnostics first** before attempting fixes
   ```bash
   python scripts/diagnose_feast_mode.py --user-id 1
   ```

2. **Test with a test user** before production
   ```bash
   # Create test user or use existing test account
   python scripts/test_feast_mode.py --user-id TEST_USER_ID --scenario all
   ```

3. **Backup database** before running fixes
   ```bash
   docker exec -t diet_planner_db pg_dump -U lalit -d fitness_track > backup.sql
   ```

4. **Use interactive manager** for safe operations
   ```bash
   # Interactive prompts prevent mistakes
   python scripts/feast_mode_manager.py
   ```

5. **Check data integrity** after major operations
   ```bash
   python scripts/test_feast_mode.py --user-id 1 --scenario integrity
   ```

## Integration with CLAUDE.md

These scripts are documented in CLAUDE.md for easy reference:
- See "Common Commands" section for quick usage
- Scripts are located in `backend/scripts/`
- Always activate venv before running

## Next Steps

After testing with these scripts:

1. **If issues found**: Check FEAST_MODE_IMPROVEMENTS.md for solutions
2. **If all tests pass**: Proceed with manual testing via AI Coach
3. **If fixes needed**: Implement recommended code changes
4. **If production ready**: Deploy and monitor

## Getting Help

If you encounter issues not covered here:
1. Check diagnostic output for specific errors
2. Review FEAST_MODE_IMPROVEMENTS.md for known issues
3. Check application logs: `docker-compose logs -f backend`
4. Run with verbose flag: `--verbose`

## Summary

These scripts provide comprehensive testing and management for the feast mode feature:

- **test_feast_mode.py** → Automated testing with snapshots
- **feast_mode_manager.py** → Interactive management CLI
- **diagnose_feast_mode.py** → Quick issue detection and fixes

Use them together to ensure feast mode works correctly for your users!
