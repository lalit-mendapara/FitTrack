#!/usr/bin/env python3
"""
Feast Mode Manager Script
=========================
Interactive CLI tool to manage feast mode for users.
Provides a user-friendly interface to:
- Check feast mode status
- Activate feast mode with validation
- Cancel feast mode with restoration
- View history

Usage:
    python scripts/feast_mode_manager.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.social_event import SocialEvent
from app.models.meal_plan import MealPlan
from app.models.tracking import FoodLog
from app.services.social_event_service import (
    propose_banking_strategy,
    create_social_event,
    get_active_event,
    cancel_active_event
)
from app.services.workout_service import patch_limit_day_workout, restore_workout_plan
from app.services.meal_service import adjust_todays_meal_plan
from app.services.stats_service import StatsService

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

def print_menu():
    print(f"{Colors.OKBLUE}Feast Mode Manager{Colors.ENDC}")
    print("─" * 40)
    print("1. Check Feast Mode Status")
    print("2. Activate Feast Mode")
    print("3. Cancel Feast Mode")
    print("4. View User Profile")
    print("5. View Meal Plan")
    print("6. View Feast Mode History")
    print("0. Exit")
    print("─" * 40)

def get_user_input(prompt, input_type=str, default=None):
    """Get validated user input"""
    while True:
        try:
            user_input = input(f"{prompt}: ").strip()
            if not user_input and default is not None:
                return default
            if input_type == int:
                return int(user_input)
            elif input_type == date:
                return datetime.strptime(user_input, "%Y-%m-%d").date()
            return user_input
        except ValueError:
            print(f"{Colors.FAIL}Invalid input. Please try again.{Colors.ENDC}")

def select_user(db: Session) -> int:
    """Interactive user selection"""
    print_header("Select User")

    # Show available users
    users = db.query(User).limit(10).all()
    print(f"Available users:")
    for user in users:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        status = "✓ Has profile" if profile else "✗ No profile"
        print(f"  {user.id}. {user.name} ({user.email}) - {status}")

    print()
    user_id = get_user_input("Enter User ID", int)

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        print(f"{Colors.FAIL}User not found!{Colors.ENDC}")
        return None

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        print(f"{Colors.FAIL}User has no profile!{Colors.ENDC}")
        return None

    print(f"{Colors.OKGREEN}Selected: {user.name}{Colors.ENDC}")
    return user_id

def check_status(db: Session, user_id: int):
    """Check current feast mode status"""
    print_header("Feast Mode Status")

    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    print(f"{Colors.BOLD}User:{Colors.ENDC} {user.name} (ID: {user_id})")
    print(f"{Colors.BOLD}Current Calories:{Colors.ENDC} {profile.calories} kcal")
    print(f"{Colors.BOLD}Fitness Goal:{Colors.ENDC} {profile.fitness_goal}")
    print()

    # Check for active event
    active_event = get_active_event(db, user_id)

    if active_event:
        days_remaining = (active_event.event_date - date.today()).days
        status = "BANKING" if days_remaining > 0 else "FEAST_DAY"

        print(f"{Colors.WARNING}⚡ Feast Mode is ACTIVE{Colors.ENDC}")
        print(f"  Event: {active_event.event_name}")
        print(f"  Event Date: {active_event.event_date}")
        print(f"  Days Remaining: {max(0, days_remaining)}")
        print(f"  Status: {status}")
        print(f"  Daily Deduction: {active_event.daily_deduction} kcal")
        print(f"  Total Banking: {active_event.target_bank_calories} kcal")

        # Calculate effective calories
        stats = StatsService(db)
        user_profile = stats.get_user_profile(user_id)
        effective_calories = user_profile['caloric_target']
        print(f"  Effective Calories Today: {effective_calories} kcal")

    else:
        print(f"{Colors.OKGREEN}✓ No active feast mode{Colors.ENDC}")

    # Show recent events
    recent_events = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id
    ).order_by(SocialEvent.created_at.desc()).limit(3).all()

    if recent_events:
        print(f"\n{Colors.BOLD}Recent Events:{Colors.ENDC}")
        for evt in recent_events:
            status_icon = "✓" if evt.is_active else "✗"
            print(f"  {status_icon} {evt.event_name} ({evt.event_date}) - {evt.target_bank_calories} kcal")

def activate_feast_mode(db: Session, user_id: int):
    """Interactive feast mode activation"""
    print_header("Activate Feast Mode")

    # Check if already active
    active_event = get_active_event(db, user_id)
    if active_event:
        print(f"{Colors.WARNING}⚠ Feast mode is already active!{Colors.ENDC}")
        print(f"  Current event: {active_event.event_name} ({active_event.event_date})")
        replace = get_user_input("Replace with new event? (yes/no)", str, "no")
        if replace.lower() != "yes":
            return

    # Get event details
    print("\nEnter event details:")
    event_name = get_user_input("Event name (e.g., 'Birthday Party')", str, "Special Event")

    print("\nEvent date (YYYY-MM-DD):")
    print(f"  Today: {date.today()}")
    print(f"  Tomorrow: {date.today() + timedelta(days=1)}")
    print(f"  Next Saturday: {date.today() + timedelta(days=(5 - date.today().weekday()) % 7)}")

    event_date = None
    while not event_date:
        try:
            date_input = get_user_input("Event date", str)
            event_date = datetime.strptime(date_input, "%Y-%m-%d").date()

            if event_date <= date.today():
                print(f"{Colors.FAIL}Event must be in the future!{Colors.ENDC}")
                event_date = None
            elif (event_date - date.today()).days > 14:
                print(f"{Colors.FAIL}Event is too far away (max 14 days)!{Colors.ENDC}")
                event_date = None
        except ValueError:
            print(f"{Colors.FAIL}Invalid date format. Use YYYY-MM-DD{Colors.ENDC}")

    # Generate proposal
    print(f"\n{Colors.OKCYAN}Generating proposal...{Colors.ENDC}")
    proposal = propose_banking_strategy(db, user_id, event_date, event_name)

    if "error" in proposal:
        print(f"{Colors.FAIL}Error: {proposal['error']}{Colors.ENDC}")
        return

    # Show proposal
    print(f"\n{Colors.BOLD}Feast Mode Proposal:{Colors.ENDC}")
    print("─" * 50)
    print(f"  Event: {proposal['event_name']}")
    print(f"  Date: {proposal['event_date']} ({proposal['days_remaining']} days away)")
    print(f"  Strategy:")
    print(f"    - Daily Deduction: {proposal['daily_deduction']} kcal/day")
    print(f"    - Total Banking: {proposal['total_banked']} kcal")
    print("─" * 50)

    # Get current profile info
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    print(f"\n  Current Target: {profile.calories} kcal")
    print(f"  New Daily Target: {profile.calories - proposal['daily_deduction']} kcal")

    # Check if user has eaten today
    logs = db.query(FoodLog).filter(
        FoodLog.user_id == user_id,
        FoodLog.date == date.today()
    ).all()

    if logs:
        completed_meals = list(set([l.meal_type for l in logs]))
        total_eaten = sum(l.calories for l in logs)
        print(f"\n  {Colors.WARNING}Note: You've already eaten today!{Colors.ENDC}")
        print(f"    Meals: {', '.join(completed_meals)}")
        print(f"    Calories: {total_eaten} kcal")
        print(f"    Remaining meals will be adjusted to meet new target")

    # Confirm
    print()
    confirm = get_user_input("Activate feast mode? (yes/no)", str, "no")

    if confirm.lower() != "yes":
        print(f"{Colors.WARNING}Cancelled{Colors.ENDC}")
        return

    # Activate
    print(f"\n{Colors.OKCYAN}Activating feast mode...{Colors.ENDC}")

    try:
        # Create event
        event = create_social_event(db, user_id, proposal)
        print(f"{Colors.OKGREEN}✓ Event created (ID: {event.id}){Colors.ENDC}")

        # Patch workout
        try:
            patch_limit_day_workout(db, user_id, event.event_date)
            print(f"{Colors.OKGREEN}✓ Workout plan patched{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠ Workout patch failed: {e}{Colors.ENDC}")

        # Adjust meal plan
        try:
            stats = StatsService(db)
            input_profile = stats.get_user_profile(user_id)
            new_target = input_profile["caloric_target"]

            completed_meals = list(set([l.meal_type.lower() for l in logs]))
            adjust_todays_meal_plan(db, user_id, new_target, completed_meals)
            print(f"{Colors.OKGREEN}✓ Meal plan adjusted{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠ Meal adjustment failed: {e}{Colors.ENDC}")

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Feast Mode Activated Successfully!{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}Failed to activate: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

def cancel_feast_mode_interactive(db: Session, user_id: int):
    """Interactive feast mode cancellation"""
    print_header("Cancel Feast Mode")

    # Check if active
    active_event = get_active_event(db, user_id)

    if not active_event:
        print(f"{Colors.WARNING}No active feast mode found{Colors.ENDC}")
        return

    # Show event details
    print(f"{Colors.BOLD}Current Feast Mode:{Colors.ENDC}")
    print(f"  Event: {active_event.event_name}")
    print(f"  Event Date: {active_event.event_date}")
    print(f"  Daily Deduction: {active_event.daily_deduction} kcal")
    print(f"  Total Banking: {active_event.target_bank_calories} kcal")

    # Calculate what will be restored
    days_remaining = (active_event.event_date - date.today()).days
    is_feast_day = (date.today() == active_event.event_date)
    is_banking = (active_event.start_date <= date.today() < active_event.event_date)

    print()
    if is_banking:
        print(f"{Colors.OKCYAN}Restoration: Will ADD {active_event.daily_deduction} kcal back to your daily target{Colors.ENDC}")
    elif is_feast_day:
        print(f"{Colors.OKCYAN}Restoration: Will REMOVE {active_event.target_bank_calories} kcal bonus from today{Colors.ENDC}")

    # Confirm
    print()
    confirm = get_user_input("Cancel feast mode and restore original plan? (yes/no)", str, "no")

    if confirm.lower() != "yes":
        print(f"{Colors.WARNING}Cancelled{Colors.ENDC}")
        return

    # Cancel
    print(f"\n{Colors.OKCYAN}Cancelling feast mode...{Colors.ENDC}")

    try:
        result = cancel_active_event(db, user_id)

        if "error" in result:
            print(f"{Colors.FAIL}Error: {result['error']}{Colors.ENDC}")
            return

        print(f"{Colors.OKGREEN}✓ Feast mode cancelled{Colors.ENDC}")
        print(f"  Message: {result.get('message', 'N/A')}")
        print(f"  Restored calories: {result.get('restored_calories', 0)}")

        # Restore workout
        try:
            restore_workout_plan(db, user_id, active_event.event_date)
            print(f"{Colors.OKGREEN}✓ Workout plan restored{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠ Workout restore failed: {e}{Colors.ENDC}")

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Feast Mode Cancelled Successfully!{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.FAIL}Failed to cancel: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

def view_profile(db: Session, user_id: int):
    """View user profile details"""
    print_header("User Profile")

    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    print(f"{Colors.BOLD}Personal Info:{Colors.ENDC}")
    print(f"  Name: {user.name}")
    print(f"  Email: {user.email}")
    print(f"  Age: {user.age} | Gender: {user.gender}")
    print(f"  Height: {profile.height} cm | Weight: {profile.weight} kg")
    print(f"  Goal: {profile.fitness_goal} | Activity: {profile.activity_level}")

    print(f"\n{Colors.BOLD}Nutrition Targets:{Colors.ENDC}")
    print(f"  Calories: {profile.calories} kcal")
    print(f"  Protein: {profile.protein} g")
    print(f"  Carbs: {profile.carbs} g")
    print(f"  Fat: {profile.fat} g")

    # Get effective targets (with feast mode)
    stats = StatsService(db)
    user_profile = stats.get_user_profile(user_id)
    effective_calories = user_profile['caloric_target']

    if abs(effective_calories - profile.calories) > 10:
        print(f"\n{Colors.WARNING}  Effective Today: {effective_calories} kcal (Feast Mode Active){Colors.ENDC}")

def view_meal_plan(db: Session, user_id: int):
    """View current meal plan"""
    print_header("Current Meal Plan")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    meal_plans = db.query(MealPlan).filter(MealPlan.user_profile_id == profile.id).all()

    if not meal_plans:
        print(f"{Colors.WARNING}No meal plan found{Colors.ENDC}")
        return

    total_cals = 0
    for mp in meal_plans:
        print(f"\n{Colors.BOLD}{mp.meal_id.upper()}{Colors.ENDC}")
        print(f"  Dish: {mp.dish}")
        print(f"  Portion: {mp.portion_size}")
        print(f"  Calories: {mp.calories} kcal")
        print(f"  Macros: P:{mp.protein}g | C:{mp.carbs}g | F:{mp.fat}g")
        total_cals += mp.calories

    print(f"\n{Colors.BOLD}Total Daily Calories: {total_cals} kcal{Colors.ENDC}")

def view_history(db: Session, user_id: int):
    """View feast mode history"""
    print_header("Feast Mode History")

    events = db.query(SocialEvent).filter(
        SocialEvent.user_id == user_id
    ).order_by(SocialEvent.created_at.desc()).all()

    if not events:
        print(f"{Colors.WARNING}No feast mode history found{Colors.ENDC}")
        return

    for evt in events:
        status = "ACTIVE" if evt.is_active else "COMPLETED"
        status_color = Colors.OKGREEN if evt.is_active else Colors.ENDC

        print(f"\n{status_color}{Colors.BOLD}{evt.event_name}{Colors.ENDC}")
        print(f"  Status: {status}")
        print(f"  Date: {evt.event_date}")
        print(f"  Created: {evt.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Banking: {evt.daily_deduction} kcal/day × {evt.target_bank_calories // evt.daily_deduction} days = {evt.target_bank_calories} kcal")

def main():
    print_header("Feast Mode Manager")
    print(f"{Colors.BOLD}Interactive CLI Tool{Colors.ENDC}\n")

    db = SessionLocal()
    current_user_id = None

    try:
        while True:
            # Select user if not selected
            if not current_user_id:
                current_user_id = select_user(db)
                if not current_user_id:
                    continue

            # Show menu
            print()
            print_menu()
            choice = get_user_input("Select option", int, 0)

            if choice == 0:
                print(f"\n{Colors.OKGREEN}Goodbye!{Colors.ENDC}")
                break
            elif choice == 1:
                check_status(db, current_user_id)
            elif choice == 2:
                activate_feast_mode(db, current_user_id)
            elif choice == 3:
                cancel_feast_mode_interactive(db, current_user_id)
            elif choice == 4:
                view_profile(db, current_user_id)
            elif choice == 5:
                view_meal_plan(db, current_user_id)
            elif choice == 6:
                view_history(db, current_user_id)
            else:
                print(f"{Colors.FAIL}Invalid option{Colors.ENDC}")

            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
