# Feast Mode Feature Improvements

## Overview
This document outlines the issues with the current feast mode implementation and the improvements made to fix them.

## Current Issues

### 1. **AI Coach Flow Issues**
- ❌ Detection is inconsistent - feast mode intent not always recognized
- ❌ Confirmation flow is unclear - users don't understand what will happen
- ❌ No clear explanation of feast mode behavior before activation
- ❌ Regex extraction for confirmation can fail with different message formats

### 2. **Data Transparency Issues**
- ❌ Changed calorie targets not reflected in all components
- ❌ Adjusted meal plan not showing visual indicators of modification
- ❌ Dashboard doesn't show effective vs. base calories clearly
- ❌ Diet Plan page doesn't indicate meals were adjusted due to feast mode

### 3. **Backup & Restoration Issues**
- ❌ No explicit backup of original state before modification
- ❌ Cancellation doesn't fully restore all affected data
- ❌ Workout plan restoration may fail silently
- ❌ Meal plan restoration depends on recalculation, not explicit restore

### 4. **Mid-Day Activation Issues**
- ✅ Logic exists but not well tested
- ❌ User not clearly informed which meals will be affected
- ❌ No preview of adjustment before confirmation
- ❌ Consumed calories not factored into proposal calculation

## Improvements Made

### Backend Scripts

#### 1. **test_feast_mode.py**
Comprehensive testing script that verifies:
- ✅ Feast mode activation with state capture
- ✅ Mid-day activation scenarios
- ✅ Cancellation with restoration verification
- ✅ Data integrity across multiple operations
- ✅ Snapshot comparison before/after

**Usage:**
```bash
cd backend
source venv/bin/activate
python scripts/test_feast_mode.py --user-id 1 --scenario all
python scripts/test_feast_mode.py --user-id 1 --scenario activation
python scripts/test_feast_mode.py --user-id 1 --scenario midday
python scripts/test_feast_mode.py --user-id 1 --scenario cancel
```

#### 2. **feast_mode_manager.py**
Interactive CLI tool for managing feast mode:
- ✅ Check feast mode status
- ✅ Activate feast mode with interactive prompts
- ✅ Cancel feast mode with restoration
- ✅ View user profile and meal plan
- ✅ View feast mode history

**Usage:**
```bash
cd backend
source venv/bin/activate
python scripts/feast_mode_manager.py
```

### Recommended Code Changes

#### 1. **Enhanced Social Event Model**
Add backup fields to store original state:

```python
# backend/app/models/social_event.py

class SocialEvent(Base):
    # ... existing fields ...

    # NEW: Backup fields for restoration
    backup_meal_plan = Column(JSON)  # Store original meal plan
    backup_workout_schedule = Column(JSON)  # Store original workout
    backup_calories = Column(Float)  # Store original calorie target
    backup_protein = Column(Float)
    backup_carbs = Column(Float)
    backup_fat = Column(Float)
```

#### 2. **Enhanced Social Event Service**
Improve create and cancel functions:

```python
# backend/app/services/social_event_service.py

def create_social_event_with_backup(db: Session, user_id: int, proposal: dict):
    """
    Create event AND backup current state for restoration.
    """
    # 1. Capture current state
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()
    workout = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()

    backup = {
        'calories': profile.calories,
        'protein': profile.protein,
        'carbs': profile.carbs,
        'fat': profile.fat,
        'meal_plan': [
            {
                'meal_id': mp.meal_id,
                'dish': mp.dish,
                'calories': mp.calories,
                'protein': mp.protein,
                'carbs': mp.carbs,
                'fat': mp.fat,
                'portion_size': mp.portion_size
            }
            for mp in meal_plans
        ],
        'workout_schedule': workout.schedule if workout else {}
    }

    # 2. Create event with backup
    event = create_social_event(db, user_id, proposal)
    event.backup_meal_plan = backup['meal_plan']
    event.backup_workout_schedule = backup['workout_schedule']
    event.backup_calories = backup['calories']
    event.backup_protein = backup['protein']
    event.backup_carbs = backup['carbs']
    event.backup_fat = backup['fat']

    db.commit()
    return event

def restore_from_backup(db: Session, user_id: int, event: SocialEvent):
    """
    Restore EXACT state from backup (not recalculation).
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    # Restore profile targets
    if event.backup_calories:
        profile.calories = event.backup_calories
        profile.protein = event.backup_protein
        profile.carbs = event.backup_carbs
        profile.fat = event.backup_fat

    # Restore meal plan from backup
    if event.backup_meal_plan:
        # Clear current meal plan
        db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).delete()

        # Restore from backup
        for meal_data in event.backup_meal_plan:
            meal = MealPlan(
                user_profile_id=profile.id,
                meal_id=meal_data['meal_id'],
                dish=meal_data['dish'],
                calories=meal_data['calories'],
                protein=meal_data['protein'],
                carbs=meal_data['carbs'],
                fat=meal_data['fat'],
                portion_size=meal_data['portion_size']
            )
            db.add(meal)

    # Restore workout
    if event.backup_workout_schedule:
        workout = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()
        if workout:
            workout.schedule = event.backup_workout_schedule
            flag_modified(workout, "schedule")

    db.commit()
```

#### 3. **Enhanced AI Coach Detection**
Improve feast mode intent detection:

```python
# backend/app/services/ai_coach.py

def _detect_social_event_intent(self, message: str) -> dict:
    """
    Enhanced detection with better prompts and validation.
    """
    msg_lower = message.lower()

    # Expanded triggers
    triggers = [
        "party", "wedding", "birthday", "buffet", "cheat", "dinner",
        "event", "going out", "big meal", "feast", "celebration",
        "marriage", "function", "gathering", "heavy meal", "indulge"
    ]

    if not any(t in msg_lower for t in triggers):
        return None

    # Enhanced prompt with examples
    system_prompt = f"""
    Current Date: {datetime.now().strftime("%Y-%m-%d (%A)")}

    You are analyzing if the user is planning a FUTURE social event with high calorie intake.

    TASK: Extract event details if applicable.

    OUTPUT JSON:
    {{
        "is_social_event": true/false,
        "event_name": "Brief name" or null,
        "event_date": "YYYY-MM-DD" or null,
        "confidence": 0.0-1.0
    }}

    EXAMPLES:
    Input: "I have a wedding on Saturday and will eat a lot"
    Output: {{"is_social_event": true, "event_name": "Wedding", "event_date": "2026-02-14", "confidence": 0.9}}

    Input: "Going to a buffet tomorrow"
    Output: {{"is_social_event": true, "event_name": "Buffet", "event_date": "2026-02-13", "confidence": 0.85}}

    Input: "I had a party yesterday"
    Output: {{"is_social_event": false, "event_name": null, "event_date": null, "confidence": 1.0}}

    Input: "What should I eat for dinner?"
    Output: {{"is_social_event": false, "event_name": null, "event_date": null, "confidence": 1.0}}
    """

    # ... rest of the function
```

#### 4. **Enhanced Proposal Display**
Improve the feast mode proposal message:

```python
# backend/app/services/ai_coach.py

async def _node_process_social_event(self, state: GraphState) -> GraphState:
    # ... existing code ...

    # Enhanced proposal format
    response = (
        f"🍱 **Feast Mode Proposal**\n\n"
        f"I detected you have a **{event_name}** coming up on **{event_date.strftime('%A, %B %d')}**.\n\n"
        f"📊 **Here's my strategy:**\n"
        f"• Bank **{proposal['total_banked']} kcal** over {proposal['days_remaining']} days\n"
        f"• Reduce your daily calories by **{proposal['daily_deduction']} kcal**\n"
        f"• Add a **Glycogen Depletion workout** on event morning\n\n"
        f"📉 **What this means:**\n"
        f"• Your current target: **{profile.calories} kcal/day**\n"
        f"• New target: **{profile.calories - proposal['daily_deduction']} kcal/day**\n"
        f"• On event day: **{profile.calories + proposal['total_banked']} kcal** (enjoy guilt-free!)\n\n"
        f"🍽️ **How it works:**\n"
        f"• I'll adjust your remaining meals today to the new target\n"
        f"• Meals you've already eaten won't be changed\n"
        f"• Tomorrow onwards, new meal plans will match the reduced target\n"
        f"• On event day, you get the full banked bonus!\n\n"
        f"✅ Reply **'Yes'** or **'Activate'** to start\n"
        f"❌ Reply **'No'** or **'Cancel'** to skip"
    )
```

### Frontend Improvements Needed

#### 1. **Diet Plan Page - Feast Mode Indicator**
Add visual indicator when meals are adjusted:

```jsx
// frontend/src/pages/DietPlan.jsx

{feastModeActive && (
  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
    <div className="flex items-center gap-2">
      <Sparkles className="text-purple-600" />
      <p className="text-sm text-purple-900">
        <strong>Feast Mode Active:</strong> Your meal plan is adjusted to bank
        {feastEvent.daily_deduction} kcal/day for {feastEvent.event_name}
      </p>
    </div>
  </div>
)}

{/* Show original vs. adjusted calories on each meal card */}
<MealCard
  meal={meal}
  feastModeActive={feastModeActive}
  originalCalories={originalMealCalories}  // Pass from backup
  adjustedCalories={meal.calories}
/>
```

#### 2. **Dashboard - Effective Targets Display**
Show both base and effective targets:

```jsx
// frontend/src/components/dashboard/DashboardOverview.jsx

<div className="stats-card">
  <h3>Daily Target</h3>
  {feastModeActive ? (
    <div>
      <p className="text-2xl font-bold text-purple-600">
        {effectiveCalories} kcal
      </p>
      <p className="text-sm text-gray-500 line-through">
        {baseCalories} kcal
      </p>
      <p className="text-xs text-purple-600">
        Banking -{feastEvent.daily_deduction} kcal
      </p>
    </div>
  ) : (
    <p className="text-2xl font-bold">{baseCalories} kcal</p>
  )}
</div>
```

#### 3. **Workout Plan - Modified Indicator**
Show when workout is patched:

```jsx
// frontend/src/pages/WorkoutPlan.jsx

{eventDate && schedule[eventDate] && schedule[eventDate].patched && (
  <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mt-2">
    <p className="text-sm text-orange-900">
      🔥 <strong>Feast Mode:</strong> Glycogen Depletion workout added for event day
    </p>
  </div>
)}
```

### Database Migration

Add new columns to social_events table:

```sql
-- migrations/add_feast_mode_backup.sql

ALTER TABLE social_events
ADD COLUMN backup_meal_plan JSON,
ADD COLUMN backup_workout_schedule JSON,
ADD COLUMN backup_calories FLOAT,
ADD COLUMN backup_protein FLOAT,
ADD COLUMN backup_carbs FLOAT,
ADD COLUMN backup_fat FLOAT;
```

## Testing Workflow

### Step 1: Test Basic Activation
```bash
cd backend
source venv/bin/activate
python scripts/test_feast_mode.py --user-id 1 --scenario activation
```

### Step 2: Test Mid-Day Scenario
```bash
python scripts/test_feast_mode.py --user-id 1 --scenario midday
```

### Step 3: Test Cancellation
```bash
python scripts/test_feast_mode.py --user-id 1 --scenario cancel
```

### Step 4: Test Data Integrity
```bash
python scripts/test_feast_mode.py --user-id 1 --scenario integrity
```

### Step 5: Interactive Testing
```bash
python scripts/feast_mode_manager.py
# Select user
# Try: Activate → Check Status → Cancel → Check Status
```

## Manual Testing Checklist

### AI Coach Flow
- [ ] Say: "I have a wedding on Saturday"
- [ ] Verify bot proposes feast mode with clear explanation
- [ ] Reply: "Yes"
- [ ] Verify activation message shows what changed
- [ ] Check Dashboard - effective calories should be reduced
- [ ] Check Diet Plan - meals should show adjusted calories
- [ ] Check Workout Plan - event day should have special workout

### Mid-Day Activation
- [ ] Eat breakfast and lunch (log them)
- [ ] Say: "I have a birthday party in 3 days"
- [ ] Verify bot mentions already eaten meals won't change
- [ ] Reply: "Activate"
- [ ] Verify only dinner and snacks are adjusted
- [ ] Check meal plan - breakfast/lunch unchanged, dinner/snacks reduced

### Cancellation
- [ ] With active feast mode, say: "Cancel feast mode"
- [ ] Verify bot asks for confirmation
- [ ] Reply: "Yes"
- [ ] Check Dashboard - calories should be restored
- [ ] Check Diet Plan - meals should be back to original
- [ ] Check Workout Plan - special workout should be removed

### Data Integrity
- [ ] Activate feast mode
- [ ] Note down all values (calories, meal plan, workout)
- [ ] Cancel feast mode
- [ ] Verify ALL values restored exactly
- [ ] Activate again - should work without issues
- [ ] Cancel and activate multiple times - no data corruption

## Known Limitations

1. **Meal Plan Regeneration**: If user regenerates meal plan while feast mode is active, the backup is lost
2. **Profile Updates**: If user updates profile (weight, goal) during feast mode, restoration may use outdated targets
3. **Multiple Events**: Only one event can be active at a time (by design)
4. **Time Zones**: Event date uses server timezone, may not match user's local timezone

## Future Enhancements

1. **Smart Proposals**: Factor in user's current progress when proposing deductions
2. **Partial Banking**: Allow user to specify custom deduction amounts
3. **Multi-Day Events**: Support events spanning multiple days
4. **Feast Mode Templates**: Pre-defined strategies for common events (wedding, vacation, etc.)
5. **Notifications**: Remind user when feast mode starts, ends, or when event day arrives
6. **Analytics**: Track feast mode usage and success rate

## Summary

The enhanced feast mode feature now provides:
- ✅ Comprehensive testing scripts
- ✅ Interactive management tool
- ✅ Clear documentation of issues and solutions
- ✅ Recommended code improvements with backup/restore
- ✅ Frontend guidelines for data transparency
- ✅ Manual testing checklist

**Next Steps:**
1. Run test scripts to verify current behavior
2. Implement recommended backend changes (backup/restore)
3. Implement frontend improvements (visual indicators)
4. Run manual testing checklist
5. Deploy and monitor user feedback
