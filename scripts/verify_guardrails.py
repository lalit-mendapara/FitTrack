import sys
import os
import time

# Add backend directory to path
import sys, os; from pathlib import Path; sys.path.insert(0, str([p for p in Path(__file__).resolve().parents if (p / 'backend').exists()][0] / 'backend')) # modified

from app.database import SessionLocal
from app.services.ai_coach import FitnessCoachService
from sqlalchemy import text

def verify_guardrails():
    db = SessionLocal()
    # Use a dummy session ID
    coach = FitnessCoachService(db, session_id="test_guardrails_v1")
    
    # We need a user context to build the prompt.
    user_stmt = "SELECT id FROM users LIMIT 1"
    valid_user_id = db.execute(text(user_stmt)).scalar() or 1
    print(f"Using User ID: {valid_user_id}")
    
    # Manually invoke _build_system_prompt to inspect its content
    # We will mock the context data for a deterministic test
    
    context = {
        "profile": {"name": "TestUser", "age": 30, "goal": "Health"},
        "diet_plan": [],
        "workout_plan": {},
        "preferences": {},
        "progress": {}
    }
    
    foods = []
    exercises = []
    
    system_prompt = coach._build_system_prompt(context, foods, exercises)
    
    print("\n--- 🛡️ GUARDRAIL SYSTEM PROMPT VERIFICATION ---")
    
    checks = [
        ("Medical/Injury", "MEDICAL WALL (ABSOLUTE REFUSAL)"),
        ("Medical Keyword", "doctor"),
        ("Out of Scope", "OUT OF SCOPE"),
        ("Out of Scope Keyword", "Politics"),
        ("Extreme Advice", "EXTREME/UNSAFE ADVICE"),
        ("Extreme Keyword", "Starvation"),
        ("Single Meal Limit", "SINGLE meal > 1000 kcal")
    ]
    
    all_passed = True
    for name, keyword in checks:
        if keyword in system_prompt:
             print(f"✅ {name} Guardrail FOUND")
        else:
             print(f"❌ {name} Guardrail MISSING")
             all_passed = False
             
    if all_passed:
        print("\n🎉 ALL GUARDRAILS CONFIRMED IN SYSTEM PROMPT")
    else:
        print("\n⚠️ SOME GUARDRAILS ARE MISSING")

    db.close()

if __name__ == "__main__":
    verify_guardrails()
