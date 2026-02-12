#!/usr/bin/env python3
"""
Feast Mode Diagnostic Tool
==========================
Quickly diagnose feast mode issues for a user.
Checks:
- Current feast mode status
- Meal plan consistency
- Workout plan modifications
- Data integrity
- Common issues

Usage:
    python scripts/diagnose_feast_mode.py --user-id 1
    python scripts/diagnose_feast_mode.py --user-id 1 --fix  # Auto-fix common issues
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.meal_plan import MealPlan
from app.models.workout_plan import WorkoutPlan
from app.models.social_event import SocialEvent
from app.models.tracking import FoodLog
from app.services.social_event_service import get_active_event, get_effective_daily_targets
from app.services.stats_service import StatsService
import json

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

class DiagnosticReport:
    def __init__(self):
        self.checks = []
        self.issues = []
        self.warnings = []

    def add_check(self, name, status, details=""):
        self.checks.append({
            'name': name,
            'status': status,  # 'pass', 'fail', 'warning'
            'details': details
        })

    def add_issue(self, issue):
        self.issues.append(issue)

    def add_warning(self, warning):
        self.warnings.append(warning)

    def print_report(self):
        print_header("Diagnostic Report")

        # Print checks
        print(f"{Colors.BOLD}Checks Performed:{Colors.ENDC}\n")
        for check in self.checks:
            status = check['status']
            icon = "✓" if status == 'pass' else ("⚠" if status == 'warning' else "✗")
            color = Colors.OKGREEN if status == 'pass' else (Colors.WARNING if status == 'warning' else Colors.FAIL)

            print(f"{color}{icon} {check['name']}{Colors.ENDC}")
            if check['details']:
                print(f"  {check['details']}")

        # Print issues
        if self.issues:
            print(f"\n{Colors.FAIL}{Colors.BOLD}Issues Found:{Colors.ENDC}\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"{Colors.FAIL}{i}. {issue}{Colors.ENDC}")

        # Print warnings
        if self.warnings:
            print(f"\n{Colors.WARNING}{Colors.BOLD}Warnings:{Colors.ENDC}\n")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{Colors.WARNING}{i}. {warning}{Colors.ENDC}")

        # Summary
        print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
        passed = sum(1 for c in self.checks if c['status'] == 'pass')
        failed = sum(1 for c in self.checks if c['status'] == 'fail')
        warnings = sum(1 for c in self.checks if c['status'] == 'warning')

        print(f"  Total Checks: {len(self.checks)}")
        print(f"  {Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
        print(f"  {Colors.FAIL}Failed: {failed}{Colors.ENDC}")
        print(f"  {Colors.WARNING}Warnings: {warnings}{Colors.ENDC}")
        print(f"  Issues: {len(self.issues)}")

def diagnose_user(db: Session, user_id: int) -> DiagnosticReport:
    """Run comprehensive diagnostics"""
    report = DiagnosticReport()

    print_info(f"Running diagnostics for user {user_id}...")

    # Check 1: User exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        report.add_check("User Exists", "fail", "User not found in database")
        report.add_issue(f"User ID {user_id} does not exist")
        return report

    report.add_check("User Exists", "pass", f"User: {user.name} ({user.email})")

    # Check 2: Profile exists
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        report.add_check("User Profile", "fail", "No profile found")
        report.add_issue("User has no profile - cannot use feast mode")
        return report

    report.add_check("User Profile", "pass", f"Calories: {profile.calories}, Goal: {profile.fitness_goal}")

    # Check 3: Feast mode status
    active_event = get_active_event(db, user_id)

    if not active_event:
        report.add_check("Feast Mode Status", "pass", "No active feast mode")
        report.add_warning("No feast mode active - some checks skipped")
        return report

    # Feast mode is active - detailed checks
    days_remaining = (active_event.event_date - date.today()).days
    is_feast_day = (date.today() == active_event.event_date)
    is_banking = (active_event.start_date <= date.today() < active_event.event_date)

    status_text = "FEAST_DAY" if is_feast_day else ("BANKING" if is_banking else "EXPIRED")
    report.add_check("Feast Mode Status", "pass" if is_banking or is_feast_day else "warning",
                     f"{status_text} - Event: {active_event.event_name} ({active_event.event_date})")

    # Check 4: Event validity
    if active_event.event_date < date.today():
        report.add_check("Event Date", "warning", f"Event is in the past: {active_event.event_date}")
        report.add_warning("Feast mode event is expired - should be auto-deactivated")
    else:
        report.add_check("Event Date", "pass", f"Event in {days_remaining} days")

    # Check 5: Calorie targets consistency
    base_targets = {
        'calories': profile.calories,
        'protein': profile.protein,
        'carbs': profile.carbs,
        'fat': profile.fat
    }

    effective_targets = get_effective_daily_targets(db, user_id, base_targets, date.today())

    # During banking phase, effective should be less than base
    if is_banking:
        expected_calories = profile.calories - active_event.daily_deduction
        actual_effective = effective_targets['calories']

        if abs(actual_effective - expected_calories) < 10:
            report.add_check("Calorie Adjustment", "pass",
                           f"Base: {profile.calories} → Effective: {actual_effective} (-{active_event.daily_deduction})")
        else:
            report.add_check("Calorie Adjustment", "fail",
                           f"Expected: {expected_calories}, Got: {actual_effective}")
            report.add_issue(f"Calorie calculation mismatch - expected {expected_calories} but got {actual_effective}")

    # During feast day, effective should be more than base
    elif is_feast_day:
        expected_calories = profile.calories + active_event.target_bank_calories
        actual_effective = effective_targets['calories']

        if abs(actual_effective - expected_calories) < 10:
            report.add_check("Calorie Bonus", "pass",
                           f"Base: {profile.calories} → Effective: {actual_effective} (+{active_event.target_bank_calories})")
        else:
            report.add_check("Calorie Bonus", "fail",
                           f"Expected: {expected_calories}, Got: {actual_effective}")
            report.add_issue(f"Feast day bonus not applied correctly")

    # Check 6: Meal plan consistency
    meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()

    if not meal_plans:
        report.add_check("Meal Plan", "warning", "No meal plan found")
        report.add_warning("User has no meal plan - feast mode may not be working properly")
    else:
        total_meal_calories = sum(mp.calories for mp in meal_plans)
        expected_total = effective_targets['calories']

        # Allow 10% tolerance
        tolerance = expected_total * 0.1

        if abs(total_meal_calories - expected_total) <= tolerance:
            report.add_check("Meal Plan Consistency", "pass",
                           f"Total: {total_meal_calories} kcal (Target: {expected_total})")
        else:
            report.add_check("Meal Plan Consistency", "fail",
                           f"Total: {total_meal_calories} kcal, Expected: {expected_total}")
            report.add_issue(f"Meal plan total ({total_meal_calories}) doesn't match target ({expected_total})")

    # Check 7: Workout plan modifications
    workout = db.query(WorkoutPlan).filter(WorkoutPlan.user_profile_id == profile.id).first()

    if not workout:
        report.add_check("Workout Plan", "warning", "No workout plan found")
    else:
        schedule = workout.schedule
        event_day = active_event.event_date.strftime('%A')

        if event_day in schedule or event_day.lower() in schedule:
            day_data = schedule.get(event_day) or schedule.get(event_day.lower())

            if isinstance(day_data, dict):
                focus = day_data.get('focus', '')
                if 'depletion' in focus.lower() or 'leg' in focus.lower():
                    report.add_check("Workout Modification", "pass",
                                   f"Event day ({event_day}) has glycogen depletion workout")
                else:
                    report.add_check("Workout Modification", "warning",
                                   f"Event day workout exists but may not be modified: {focus}")
                    report.add_warning(f"Expected glycogen depletion workout on {event_day}")
            else:
                report.add_check("Workout Modification", "warning",
                               f"Event day workout format unclear: {day_data}")
        else:
            report.add_check("Workout Modification", "warning",
                           f"No workout found for event day ({event_day})")
            report.add_warning(f"Feast mode should add workout on event day")

    # Check 8: Food logs consistency
    logs_today = db.query(FoodLog).filter(
        FoodLog.user_id == user_id,
        FoodLog.date == date.today()
    ).all()

    if logs_today:
        total_logged = sum(l.calories for l in logs_today)
        completed_meals = list(set([l.meal_type.lower() for l in logs_today]))

        report.add_check("Food Logs", "pass",
                       f"{len(logs_today)} logs, {total_logged} kcal, Meals: {', '.join(completed_meals)}")

        # Check if completed meals are still in meal plan
        meal_ids = [mp.meal_id.lower() for mp in meal_plans]
        for meal_type in completed_meals:
            if meal_type not in meal_ids:
                report.add_warning(f"Logged meal '{meal_type}' not in current meal plan")
    else:
        report.add_check("Food Logs", "pass", "No food logs today")

    # Check 9: Multiple active events
    all_active = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id,
        SocialEvent.is_active == True
    ).all()

    if len(all_active) > 1:
        report.add_check("Multiple Events", "fail", f"Found {len(all_active)} active events")
        report.add_issue("Multiple feast mode events are active - should only be 1")
    else:
        report.add_check("Multiple Events", "pass", "Only one active event")

    # Check 10: Data integrity
    if profile.calories <= 0 or profile.protein <= 0:
        report.add_check("Data Integrity", "fail", "Profile has invalid nutrition values")
        report.add_issue("Profile calories or macros are zero or negative")
    else:
        report.add_check("Data Integrity", "pass", "Profile data looks valid")

    return report

def auto_fix_issues(db: Session, user_id: int, report: DiagnosticReport):
    """Attempt to auto-fix common issues"""
    print_header("Auto-Fix Attempt")

    fixed = 0

    # Fix 1: Deactivate expired events
    expired_events = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id,
        SocialEvent.is_active == True,
        SocialEvent.event_date < date.today()
    ).all()

    if expired_events:
        print_info(f"Deactivating {len(expired_events)} expired events...")
        for event in expired_events:
            event.is_active = False
            print_success(f"Deactivated: {event.event_name} ({event.event_date})")
            fixed += 1

    # Fix 2: Deactivate duplicate events (keep most recent)
    all_active = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id,
        SocialEvent.is_active == True
    ).order_by(SocialEvent.created_at.desc()).all()

    if len(all_active) > 1:
        print_info(f"Found {len(all_active)} active events - keeping most recent...")
        for event in all_active[1:]:  # Keep first (most recent)
            event.is_active = False
            print_success(f"Deactivated duplicate: {event.event_name}")
            fixed += 1

    db.commit()

    if fixed > 0:
        print_success(f"\nFixed {fixed} issue(s)")
        print_info("Re-running diagnostics...")
        return diagnose_user(db, user_id)
    else:
        print_warning("No auto-fixable issues found")
        return report

def main():
    parser = argparse.ArgumentParser(description='Diagnose feast mode issues')
    parser.add_argument('--user-id', type=int, required=True, help='User ID to diagnose')
    parser.add_argument('--fix', action='store_true', help='Attempt to auto-fix issues')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    print_header(f"Feast Mode Diagnostics - User {args.user_id}")

    db = SessionLocal()

    try:
        # Run diagnostics
        report = diagnose_user(db, args.user_id)

        # Print report
        report.print_report()

        # Auto-fix if requested
        if args.fix and (report.issues or report.warnings):
            print()
            confirm = input(f"{Colors.WARNING}Attempt auto-fix? (yes/no): {Colors.ENDC}").strip().lower()

            if confirm == 'yes':
                report = auto_fix_issues(db, args.user_id, report)
                report.print_report()
            else:
                print_info("Auto-fix cancelled")

        # Exit code based on issues
        if report.issues:
            return 1
        else:
            return 0

    except Exception as e:
        print_error(f"Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
