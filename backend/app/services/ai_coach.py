from sqlalchemy.orm import Session
from datetime import datetime
from app.services.stats_service import StatsService
from app.services.vector_service import VectorService
from app.services.chat_memory_service import ChatMemoryService
from app.services.llm_service import call_llm
import json
import re
import sys
from app.models.chat import ChatHistory
from app.models.meal_plan_history import MealPlanHistory
from app.models.tracking import FoodLog
from sqlalchemy import func
from datetime import date, timedelta
from typing import TypedDict, List, Dict, Any, Optional
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    StateGraph = None
    END = None

# Langfuse tracing
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator fallback
if sys.version_info < (3, 14):
    try:
        from langfuse import observe
    except ImportError:
        pass

class GraphState(TypedDict):
    """
    Represents the state of the AI Coach Agent.
    """
    user_message: str
    user_id: int
    session_id: str
    
    # Internal Context
    intent_data: Optional[Dict[str, Any]]
    social_event_data: Optional[Dict[str, Any]]
    meal_adjustment_data: Optional[Dict[str, Any]]
    historical_context_str: Optional[str]
    user_context: Dict[str, Any]
    food_knowledge: List[Dict[str, Any]]
    exercise_knowledge: List[Dict[str, Any]]
    
    # Output
    final_response: str
    source: str

class FitnessCoachService:
    """
    The Brain: Orchestrates the fitness chatbot logic.
    Combines input from "The Librarian" (Qdrant), "The Auditor" (Stats),
    and "The Notepad" (Redis) to generate context-aware responses.
    """

    def __init__(self, db: Session, session_id: str):
        self.stats_service = StatsService(db)
        self.db = db # Store session directly
        self.vector_service = VectorService()
        self.memory_service = ChatMemoryService(session_id)
        self.user_message = ""
        # Stop words to remove for strict SQL search
        self.stop_words = {
            "what", "is", "the", "in", "of", "and", "or", "to", "for", "a", "an", "are", 
            "how", "much", "many", "calories", "protein", "carbs", "fats", "fat", "nutrition",
            "give", "me", "tell", "show", "can", "you", "please", "help",
            "compare", "vs", "versus", "diff", "difference", "between"
        }

    def _extract_search_terms(self, message: str) -> str:
        """
        Heuristic to extract potential food/exercise names from a sentence.
        E.g. "How much protein in apple?" -> "apple"
        """
        words = message.lower().replace("?", "").replace(".", "").split()
        keywords = [w for w in words if w not in self.stop_words]
        
        if not keywords:
            return message # Fallback to original if everything filtered out
            
        return " ".join(keywords)

    def _detect_history_intent(self, message: str) -> dict:
        """
        Uses LLM to detect if the user is asking about a specific past date.
        Returns {'date': datetime.date object} or None.
        """
        # Quick heuristic check first to save LLM calls
        triggers = ["yesterday", "last", "ago", "history", "previous", "past", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if not any(t in message.lower() for t in triggers):
            return None

        print(f"[History Intent] Checking intent for: '{message}'")
        
        system_prompt = f"""
        You are a time-aware intent classifier.
        Current Date: {datetime.now().strftime("%Y-%m-%d (%A)")}
        
        Task: Analyze the user's message. 
        1. Are they asking about a PAST diet/meal plan? 
        2. If yes, calculate the target date based on the Current Date.
        
        Output JSON ONLY:
        {{
            "is_history": true/false,
            "target_date": "YYYY-MM-DD" (or null)
        }}
        
        Examples (Assuming Today is 2026-02-05 Thursday):
        - "What did I eat yesterday?" -> {{"is_history": true, "target_date": "2026-02-04"}}
        - "Show me last Tuesday's plan" -> {{"is_history": true, "target_date": "2026-01-27"}}
        - "What is my plan for today?" -> {{"is_history": false, "target_date": null}}
        """
        
        try:
            from app.services.llm_service import call_llm_json
            response = call_llm_json(system_prompt=system_prompt, user_prompt=message, temperature=0.0)
            
            if response and response.get('is_history') and response.get('target_date'):
                target_str = response['target_date']
                try:
                    target_date = datetime.strptime(target_str, "%Y-%m-%d").date()
                    print(f"[History Intent] Detected date: {target_date}")
                    return {"date": target_date}
                except ValueError:
                    print(f"[History Intent] Failed to parse date: {target_str}")
                    return None
                    
        except Exception as e:
            print(f"[History Intent] Error: {e}")
            
        return None

    def _detect_social_event_intent(self, message: str) -> dict:
        """
        Detects if user is planning a future social event (Feast Mode).
        Triggers: 'party', 'wedding', 'birthday', 'dinner', 'buffet', 'cheat meal'
        """
        msg_lower = message.lower()
        triggers = ["party", "wedding", "birthday", "buffet", "cheat", "dinner", "event", "going out", "big meal"]
        
        if not any(t in msg_lower for t in triggers):
            return None
            
        print(f"[Social Intent] Checking intent for: '{message}'")
        
        system_prompt = f"""
        Current Date: {datetime.now().strftime("%Y-%m-%d (%A)")}
        
        Task: Analyze if the user is mentioning a FUTURE social event with high calorie intake.
        If yes, identify the event name and date.
        
        Output JSON ONLY:
        {{
            "is_social_event": true/false,
            "event_name": "Wedding" (or null),
            "event_date": "YYYY-MM-DD" (or null)
        }}
        
        Examples:
        - "I have a wedding on Saturday" -> {{"is_social_event": true, "event_name": "Wedding", "event_date": "2026-02-14"}}
        - "Going to a buffet tomorrow" -> {{"is_social_event": true, "event_name": "Buffet", "event_date": "2026-02-11"}}
        """
        
        try:
            from app.services.llm_service import call_llm_json
            response = call_llm_json(system_prompt=system_prompt, user_prompt=message, temperature=0.0)
            
            if response and response.get('is_social_event') and response.get('event_date'):
                target_str = response['event_date']
                try:
                    event_date = datetime.strptime(target_str, "%Y-%m-%d").date()
                    # Ensure it's in the future
                    if event_date <= date.today():
                         print(f"[Social Intent] Event is not in future: {event_date}")
                         return None
                         
                    print(f"[Social Intent] Detected event: {response['event_name']} on {event_date}")
                    return {
                        "event_name": response.get('event_name', 'Social Event'),
                        "event_date": event_date
                    }
                except ValueError:
                    return None
        except Exception:
            pass
            
        return None



    def _detect_meal_adjustment_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Detects if user wants to adjust a specific meal (e.g. eating out, skipping).
        Returns dict with target_meal, reason, user_estimated_calories, user_foods.
        """
        # Quick keyword check to save LLM calls
        keywords = ['eat out', 'eating out', 'ordering', 'skip', 'change', 'adjust', 'pizza', 'burger', 'party', 'dinner', 'lunch', 'breakfast']
        if not any(k in message.lower() for k in keywords):
            return None
            
        system_prompt = """Analyze if the user wants to ADJUST or OVERRIDE a specific meal in their plan.
        
        Possible scenarios:
        1. Eating out / Ordering in ("I'm having pizza for dinner")
        2. Skipping a meal ("Skip lunch today")
        3. Adjustment ("Change my snack to an apple")
        
        Output JSON ONLY:
        {
            "is_adjustment": true/false,
            "target_meal": "breakfast" | "lunch" | "dinner" | "snack",
            "reason": "eating_out" | "skip" | "custom_food" | "other",
            "user_foods": ["pizza", "beer"],
            "user_estimated_calories": 1500 (number or null),
            "confidence": 0.0-1.0
        }
        
        Rules:
        - If user just says "I ate pizza", that is a LOGGING intent, NOT adjustment. 
          Adjustment implies FUTURE or PRESENT ("I WILL eat", "I AM eating", "Change my plan").
        - If user says "I ate" (past tense), set is_adjustment: false.
        """
        
        try:
            from app.services.llm_service import call_llm_json
            result = call_llm_json(system_prompt=system_prompt, user_prompt=message, temperature=0.0)
            
            if result and result.get("is_adjustment") and result.get("confidence", 0) > 0.7:
                return {
                    "type": "proposal",
                    "target_meal": result.get("target_meal"),
                    "reason": result.get("reason"),
                    "user_foods": result.get("user_foods", []),
                    "user_estimated_calories": result.get("user_estimated_calories")
                }
        except Exception as e:
            print(f"Error checking meal adjustment intent: {e}")
            
        return None
        """
        Forensic Retrieval:
        1. Fetches ALL plan snapshots for that day.
        2. Fetches ALL food logs for that day.
        3. Identifies the 'True Plan' by matching logs to plans.
        4. Returns a detailed Context String (not just JSON).
        """
        try:
            # 0. Resolve Profile ID
            from app.models.user_profile import UserProfile
            profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                 print(f"[History Retrieval] No profile found for user_id {user_id}")
                 return None
            
            profile_id = profile.id
            print(f"[History Forensic] Resolved User ID {user_id} -> Profile ID {profile_id}")

            # 1. Fetch Candidate Plans (Use Profile ID)
            candidates = self.db.query(MealPlanHistory).filter(
                MealPlanHistory.user_profile_id == profile_id,
                func.date(MealPlanHistory.created_at) == target_date
            ).order_by(MealPlanHistory.created_at.desc()).all()
            
            # 2. Fetch Evidence (Food Logs) (Use User ID)
            logs = self.db.query(FoodLog).filter(
                FoodLog.user_id == user_id,
                FoodLog.date == target_date
            ).all()
            
            if not candidates:
                print(f"[History Forensic] No meal plans found for {target_date} (Profile {profile_id})")
                return None
                
            print(f"[History Forensic] Found {len(candidates)} candidates and {len(logs)} logs for {target_date}")
            
            # LOGGING DETAILS
            if logs:
                print("   --- EVIDENCE (LOGS) ---")
                for l in logs:
                    print(f"   [Log ID {l.id}] '{l.food_name}' ({l.meal_type})")
            else:
                print("   [History Forensic] No logs found for this date.")

            if candidates:
                print("   --- CANDIDATES (PLANS) ---")
                for p in candidates:
                    print(f"   [Plan ID {p.id}] Created: {p.created_at}")

            # 3. Forensic Matching
            best_plan = candidates[0] # Default to latest
            
            if logs:
                best_score = -1
                
                print("   --- MATCHING PROCESS ---")
                for plan in candidates:
                    snapshot = plan.meal_plan_snapshot
                    score = 0
                    
                    # SMART READER: Normalize snapshot (List -> Dict)
                    normalized_snapshot = {}
                    if isinstance(snapshot, list):
                        for item in snapshot:
                            key = item.get('meal_id') or item.get('label', 'unknown').lower()
                            normalized_snapshot[key] = item
                        print(f"     [Normalize] Converted List to Dict with keys: {list(normalized_snapshot.keys())}")
                    elif isinstance(snapshot, dict):
                        normalized_snapshot = snapshot
                    
                    # Extract all planned dish names
                    planned_dishes = []
                    for meal_data in normalized_snapshot.values():
                        if isinstance(meal_data, dict):
                            # Support both 'dish_name' (List format) and 'dish' (Dict format)
                            dish = meal_data.get('dish_name', '') or meal_data.get('dish', '')
                            dish = dish.strip().lower()
                            if dish:
                                planned_dishes.append(dish)
                    
                    print(f"     [Extracted Dishes] {planned_dishes}")

                    # Score this plan against logs
                    for log in logs:
                        log_name = log.food_name.strip().lower()
                        
                        # 1. Exact Match (High Score)
                        if log_name in planned_dishes:
                            score += 10
                            print(f"     [Match] Log '{log_name}' == Plan Item -> +10 Pts")
                        # 2. Substring Match (Low Score) - "Chicken" in "Chicken Salad"
                        elif any(log_name in d or d in log_name for d in planned_dishes):
                            score += 1
                            print(f"     [Partial] Log '{log_name}' ~ Plan Item -> +1 Pts")
                            
                    print(f"   -> Plan ID {plan.id} Total Score: {score}")
                    
                    if score > best_score:
                        best_score = score
                        best_plan = plan
                        
            print(f"[History Forensic] >>> WINNER: Plan ID {best_plan.id}")
            
            # 4. Construct 'Plan vs Reality' Context
            snapshot = best_plan.meal_plan_snapshot
            
            # SMART READER: Normalize snapshot (List -> Dict) for summary
            normalized_snapshot = {}
            if isinstance(snapshot, list):
                for item in snapshot:
                    key = item.get('meal_id') or item.get('label', 'unknown').lower()
                    normalized_snapshot[key] = item
            elif isinstance(snapshot, dict):
                normalized_snapshot = snapshot
            
            # Build Comparison Summary
            comparison = []
            meals = ["breakfast", "lunch", "dinner", "snacks"] 
            
            for m in meals:
                meal_data = normalized_snapshot.get(m, {})
                # Support both 'dish_name' (List format) and 'dish' (Dict format)
                plan_item = meal_data.get('dish_name', '') or meal_data.get('dish', 'Nothing Planned') if isinstance(meal_data, dict) else "Unknown"
                
                # Check for log match for this meal type
                status = "❌ No Log Found"
                logged_item = "None"
                
                for log in logs:
                    # Simple fuzzy match: is the log name in the dish name or vice versa?
                    if log.food_name.lower() in plan_item.lower() or plan_item.lower() in log.food_name.lower():
                        status = "✅ Followed"
                        logged_item = log.food_name
                        break
                
                comparison.append(f"- **{m.capitalize()}**: Planned '{plan_item}' -> {status} (Log: {logged_item})")
                
            # Formatting the final context block
            context = {
                "summary": "\n".join(comparison),
                "full_plan": snapshot,
                "logs_count": len(logs),
                "candidates_count": len(candidates)
            }
            return context

        except Exception as e:
            print(f"[History Retrieval] Forensic Error: {e}")
            traceback.print_exc()
            return None

    # --- LANGGRAPH NODES ---

    @observe(name="node_detect_intent")
    async def _node_detect_intent(self, state: GraphState) -> GraphState:
        """Node: Detects if user is asking about history or social events or meal adjustments."""
        msg = state["user_message"]
        
        # 0. Check for Confirmations (Multi-turn)
        memory = ChatMemoryService(state["session_id"])
        last_ai_msg = memory.get_last_ai_message()
        if last_ai_msg:
             # A. Check Meal Adjustment Confirmation
             if "Meal Adjustment Proposal" in last_ai_msg:
                 # Helper to parse confirmation
                 from app.services.llm_service import call_llm_json
                 confirm_prompt = f"""The AI proposed adjusting a meal based on the user's request.
                 User reply: "{msg}"
                 
                 Output JSON:
                 {{
                    "action": "confirm" | "reject",
                    "reason": "explanation"
                 }}
                 """
                 try:
                     res = call_llm_json(system_prompt=confirm_prompt, user_prompt=msg, temperature=0.0)
                     if res and res.get("action") == "confirm":
                         pending = memory.get_session_data("pending_meal_adjustment")
                         if pending:
                             return {"intent_data": None, 
                                     "social_event_data": None, 
                                     "meal_adjustment_data": {"type": "confirm", "data": pending}}
                 except Exception as e:
                     print(f"Error parsing confirmation: {e}")

             # B. Check Feast Mode Confirmation
             if "Feast Mode Proposal" in last_ai_msg:
                import re
                match = re.search(r"Event\*\*:?\s*(.*?)\s*\((\d{4}-\d{2}-\d{2})\)", last_ai_msg)
                if match:
                    event_name = match.group(1).strip()
                    event_date_str = match.group(2)
                    try:
                        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        event_date = None

                    if event_date:
                        from app.services.llm_service import call_llm_json
                        confirm_prompt = f"""The AI assistant proposed a "Feast Mode" (calorie banking strategy) for an upcoming event.
The proposal included: reducing daily calories and adding a special workout on event day.

The user replied: "{msg}"

Analyze the user's reply and output JSON ONLY:
{{
"action": "confirm" or "customize" or "reject",
"custom_deduction": null,
"skip_workout": false,
"reason": "brief explanation"
}}

Rules:
- "action" = "confirm" if the user agrees, accepts, says yes, or wants to activate as-is
- "action" = "customize" if the user wants to CHANGE something (adjust calories, different deduction, modify the plan)
- "action" = "reject" if the user declines, says no, or asks unrelated questions
- "custom_deduction" = a NUMBER (kcal/day) ONLY if the user specifies a specific deduction value, else null
- "skip_workout" = true ONLY if the user explicitly says they don't want workout changes
- Examples:
  - "yes" -> {{"action": "confirm", "custom_deduction": null, "skip_workout": false, "reason": "direct confirmation"}}
  - "activate it" -> {{"action": "confirm", "custom_deduction": null, "skip_workout": false, "reason": "direct confirmation"}}
  - "yes but skip the workout" -> {{"action": "confirm", "custom_deduction": null, "skip_workout": true, "reason": "user wants calorie-only mode"}}
  - "I want to adjust calories" -> {{"action": "customize", "custom_deduction": null, "skip_workout": false, "reason": "user wants to change deduction"}}
  - "make it 300 kcal" -> {{"action": "customize", "custom_deduction": 300, "skip_workout": false, "reason": "user specified custom deduction"}}
  - "can we do 200 per day instead?" -> {{"action": "customize", "custom_deduction": 200, "skip_workout": false, "reason": "user wants lower deduction"}}
  - "no thanks" -> {{"action": "reject", "custom_deduction": null, "skip_workout": false, "reason": "user declined"}}
  - "what is feast mode?" -> {{"action": "reject", "custom_deduction": null, "skip_workout": false, "reason": "user asking for info"}}"""

                        try:
                            confirmation = call_llm_json(system_prompt=confirm_prompt, user_prompt=msg, temperature=0.0)
                            if confirmation:
                                action = confirmation.get("action", "reject")
                                if action == "confirm":
                                    return {"intent_data": None, "social_event_data": {
                                        "type": "confirm",
                                        "event_name": event_name,
                                        "event_date": event_date,
                                        "skip_workout": confirmation.get("skip_workout", False)
                                    }, "meal_adjustment_data": None}
                                elif action == "customize":
                                    event_data = {
                                        "type": "customize",
                                        "event_name": event_name,
                                        "event_date": event_date,
                                        "custom_deduction": confirmation.get("custom_deduction"),
                                        "skip_workout": confirmation.get("skip_workout", False)
                                    }
                                    if not event_name or not event_date:
                                        saved_context = memory.get_session_data("pending_feast_event")
                                        if saved_context:
                                            event_data["event_name"] = saved_context.get("event_name")
                                            try:
                                                event_data["event_date"] = datetime.strptime(saved_context.get("event_date"), "%Y-%m-%d").date()
                                            except: pass
                                    return {"intent_data": None, "social_event_data": event_data, "meal_adjustment_data": None}
                        except Exception as e:
                            print(f"Feast confirm error: {e}")

        # 1. Check History Intent
        history_intent = self._detect_history_intent(msg)
        if history_intent:
            return {"intent_data": history_intent, "social_event_data": None}
            
        # 2. Check Social Event Intent
        social_intent = self._detect_social_event_intent(msg)
        if social_intent:
            return {"intent_data": None, "social_event_data": social_intent}

        # 3. Check Meal Adjustment Intent (Immediate change)
        adj_intent = self._detect_meal_adjustment_intent(msg)
        if adj_intent:
            return {"intent_data": None, "social_event_data": None, "meal_adjustment_data": adj_intent}

        return {"intent_data": None, "social_event_data": None, "meal_adjustment_data": None}
            

    @observe(name="node_process_social_event")
    async def _node_process_social_event(self, state: GraphState) -> GraphState:
        """Node: Handles Social Event logic (Proposal or Confirmation)."""
        social_data = state.get("social_event_data")
        if not social_data:
            return {}
            
        user_id = state["user_id"]
        from app.services.social_event_service import propose_banking_strategy, create_social_event
        
        # Scenario A: Confirmation (Create Event)
        if social_data.get("type") == "confirm":
            # Execute Creation
            event_name = social_data["event_name"]
            event_date = social_data["event_date"]
            
            # Retrieve pending context to get agreed deduction
            memory = ChatMemoryService(state["session_id"])
            pending = memory.get_session_data("pending_feast_event")
            custom_deduction = None
            if pending and pending.get("daily_deduction"):
                 custom_deduction = pending.get("daily_deduction")

            # Recalculate proposal to get correct numbers (sanity check)
            proposal = propose_banking_strategy(self.db, user_id, event_date, event_name, custom_deduction=custom_deduction)
            
            if "error" in proposal:
                 return {"final_response": f"⚠️ Could not activate Feast Mode: {proposal['error']}", "source": "SocialService"}
            
            # Persist
            create_social_event(self.db, user_id, proposal)
            
            # Patch Workout (skip if user explicitly opted out)
            workout_patched = False
            skip_workout = social_data.get("skip_workout", False)
            if not skip_workout:
                try:
                    from app.services.workout_service import patch_limit_day_workout
                    patch_limit_day_workout(self.db, user_id, event_date)
                    workout_patched = True
                except Exception as e:
                    print(f"Failed to patch workout: {e}")
                
            # --- NEW: Mid-Day Meal Adjustment ---
            meal_adjust_msg = ""
            try:
                # If event starts TODAY (or banking phase starts today), we check for deficit
                if proposal['daily_deduction'] > 0:
                     # Calculate NEW effective target for today
                     # We can fetch this from StatsService or calculate manually
                     # Effective = Original - Deduction
                     context = self.stats_service.get_full_user_context(user_id)
                     # stats_service.get_user_profile already applies deduction if event is active!
                     # So let's fetch profile again to be sure
                     profile_data = self.stats_service.get_user_profile(user_id)
                     new_target = profile_data['caloric_target']
                     
                     # Get Completed Meals (from progress)
                     # progress = self.stats_service.get_user_progress(user_id) 
                     # Actually, progress doesn't list meal names easily.
                     # We need to know WHICH meals were eaten.
                     # Heuristic: Check FoodLogs for today.
                     from app.models.tracking import FoodLog
                     today = datetime.now().date()
                     logs = self.db.query(FoodLog).filter(FoodLog.user_id == user_id, FoodLog.date == today).all()
                     completed_meals = list(set([l.meal_type.lower() for l in logs]))
                     
                     from app.services.meal_service import adjust_todays_meal_plan
                     patch_result = adjust_todays_meal_plan(self.db, user_id, new_target, completed_meals)

                     if patch_result and abs(patch_result.get("diff_applied", 0)) > 0:
                         meal_adjust_msg = (
                             f"\n\n📉 **Plan Updated**: Since you've already eaten {', '.join(completed_meals).title()}, "
                             f"I've adjusted your remaining meals by **{abs(patch_result['diff_applied']):.0f} kcal** to keep you on track."
                         )
                         if patch_result.get("changes"):
                              changes_list = "\n".join([f"- {c}" for c in patch_result["changes"][:2]])
                              meal_adjust_msg += f"\n*Adjusted:*\n{changes_list}"
            except Exception as e:
                 print(f"Failed to patch meals: {e}")
            
            response_msg = (
                f"**Feast Mode Activated!**\n\n"
                f"I've set up your **{proposal['total_banked']} kcal buffer** for {proposal['event_name']}.\n"
                f"Starting today, your daily calorie target is reduced by **{proposal['daily_deduction']} kcal**."
            )
            
            if workout_patched:
                response_msg += f"\n\nI've also updated your workout plan: A **Glycogen Depletion** session is scheduled for {event_date.strftime('%A')} morning!"
                
            if meal_adjust_msg:
                response_msg += meal_adjust_msg
                
            # Clear pending event from memory on success
            memory = ChatMemoryService(state["session_id"])
            memory.set_session_data("pending_feast_event", None)
            
            return {
                "final_response": response_msg,
                "source": "SocialService"
            }
        
        # Scenario B: Customize (User wants to adjust the plan)
        if social_data.get("type") == "customize":
            event_name = social_data["event_name"]
            event_date = social_data["event_date"]
            custom_deduction = social_data.get("custom_deduction")
            
            # Default proposal for context if needed
            proposal = None
            
            if custom_deduction:
                # User gave a specific number — re-propose with it
                proposal = propose_banking_strategy(self.db, user_id, event_date, event_name, custom_deduction=custom_deduction)
                
                if "error" in proposal:
                    return {"final_response": f"⚠️ Could not update proposal: {proposal['error']}", "source": "SocialService"}
                
                response = (
                    f"> **Updated Feast Mode Proposal**\n>\n"
                    f"> **Event**: {event_name} ({event_date})\n"
                    f"> **Goal**: Bank {proposal['total_banked']} kcal\n>\n"
                    f"> **Strategy**:\n"
                    f"> * Deduct **{proposal['daily_deduction']} kcal/day** (Starts Today)\n"
                    f"> * Add **Leg Day Workout** ({event_date.strftime('%A')} Morning)\n>\n"
                    f"> *Shall I activate this?*"
                )
            else:
                # User wants to adjust but didn't say how — ask what they want
                # Fetch current default proposal for reference
                proposal = propose_banking_strategy(self.db, user_id, event_date, event_name)
                current_deduction = proposal.get('daily_deduction', 500) if 'error' not in proposal else 500
                
                response = (
                    f"Sure! What would you like to change?\n\n"
                    f"Currently the plan is **{current_deduction} kcal/day** deduction. "
                    f"You can tell me a specific number like *\"make it 300 kcal\"* "
                    f"or say *\"skip the workout part\"*."
                )
            
            # Save context for next turn
            # Use the calculated daily_deduction from proposal if available to ensure we save the 'sanitized' value
            to_save_deduction = proposal['daily_deduction'] if (proposal and 'daily_deduction' in proposal) else 500
            if not proposal and custom_deduction:
                to_save_deduction = custom_deduction
            
            memory = ChatMemoryService(state["session_id"])
            memory.set_session_data("pending_feast_event", {
                "event_name": event_name,
                "event_date": event_date.strftime("%Y-%m-%d") if event_date else None,
                "daily_deduction": to_save_deduction
            })
            
            return {"final_response": response, "source": "SocialService"}
            
        # Scenario C: New Proposal
        event_name = social_data.get("event_name")
        event_date = social_data.get("event_date")
        
        proposal = propose_banking_strategy(self.db, user_id, event_date, event_name)
        
        if "error" in proposal:
            return {"final_response": f"I see you have an event, but I can't enable Feast Mode: {proposal['error']}", "source": "SocialService"}
            
        # Format "Smart Card" Proposal
        response = (
            f"> **Feast Mode Proposal**\n>\n"
            f"> **Event**: {event_name} ({event_date})\n"
            f"> **Goal**: Bank {proposal['total_banked']} kcal\n>\n"
            f"> **Strategy**:\n"
            f"> * Deduct **{proposal['daily_deduction']} kcal/day** (Starts Today)\n"
            f"> * Add **Leg Day Workout** ({event_date.strftime('%A')} Morning)\n>\n"
            f"> *Want to adjust anything, or shall I activate?*"
        )
        
        # Save context for next turn
        memory = ChatMemoryService(state["session_id"])
        memory.set_session_data("pending_feast_event", {
            "event_name": event_name,
            "event_date": event_date.strftime("%Y-%m-%d"),
            "daily_deduction": proposal['daily_deduction']
        })
        
        return {"final_response": response, "source": "SocialService"}

    @observe(name="node_process_meal_adjustment")
    async def _node_process_meal_adjustment(self, state: GraphState) -> GraphState:
        """Node: Handles Meal Adjustment Logic (Proposal or Confirmation)."""
        adj_data = state.get("meal_adjustment_data")
        if not adj_data:
            return {}
            
        user_id = state["user_id"]
        from app.services.meal_service import adjust_single_meal, estimate_food_calories, adjust_todays_meal_plan
        from app.models.tracking import FoodLog
        
        # Scenario A: Confirmation
        if adj_data.get("type") == "confirm":
            pending = adj_data.get("data")
            if not pending:
                return {"final_response": "I lost track of the adjustment. Could you ask me again?", "source": "AI Coach"}
            
            target_meal = pending.get("target_meal")
            dish_name = pending.get("dish_name")
            calories = pending.get("calories")
            reason = pending.get("reason", "User Adjustment")
            
            # 1. Execute Adjustment
            # Map target_meal (e.g. "dinner") to specific meal_id if needed.
            # We assume label matches target_meal (e.g. 'dinner')
            
            try:
                from app.models.user_profile import UserProfile
                from app.models.meal_plan import MealPlan
                
                profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not profile: raise Exception("Profile not found")
                
                target_label = target_meal.lower()
                meal_to_update = self.db.query(MealPlan).filter(
                    MealPlan.user_profile_id == profile.id,
                    func.lower(MealPlan.label) == target_label
                ).first()
                
                if not meal_to_update:
                     # Fallback search by ID
                     meal_to_update = self.db.query(MealPlan).filter(
                        MealPlan.user_profile_id == profile.id,
                        MealPlan.meal_id == target_label
                    ).first()
                
                if not meal_to_update:
                     return {"final_response": f"I couldn't find your '{target_meal}' in today's plan to adjust.", "source": "AI Coach"}
                
                real_meal_id = meal_to_update.meal_id
                
                # Call Service
                override_info = {
                    "dish_name": dish_name,
                    "estimated_calories": calories,
                    "reason": reason
                }
                
                result = adjust_single_meal(self.db, user_id, real_meal_id, override_info)
                
                if "error" in result:
                     return {"final_response": f"Failed to update meal: {result['error']}", "source": "AI Coach"}
                     
                # 2. Rebalance Remaining Meals (Optional but Smart)
                today = datetime.now().date()
                logs = self.db.query(FoodLog).filter(FoodLog.user_id == user_id, FoodLog.date == today).all()
                completed_meals = set([l.meal_type.lower() for l in logs])
                completed_meals.add(target_meal.lower()) # Lock this one too
                
                user_ctx = self.stats_service.get_user_profile(user_id)
                daily_target = user_ctx.get('caloric_target', 2000)
                
                # Trigger Rebalance
                patch_res = adjust_todays_meal_plan(self.db, user_id, daily_target, list(completed_meals))
                
                # 3. Response
                msg = f"✅ **Updated!** I've changed your {target_meal} to ** {dish_name}** ({int(calories)} kcal)."
                if patch_res and patch_res.get("diff_applied", 0) != 0:
                    msg += f"\n\n⚖️ **Rebalancing**: I adjusted your other meals by **{int(patch_res['diff_applied'])} kcal** to keep you on target."
                
                # Clear memory
                memory = ChatMemoryService(state["session_id"])
                memory.set_session_data("pending_meal_adjustment", None)
                
                return {"final_response": msg, "source": "AI Coach"}
                
            except Exception as e:
                print(f"Error executing adjustment: {e}")
                return {"final_response": "Something went wrong applying that change.", "source": "AI Coach"}

        # Scenario B: Proposal extraction
        target_meal = adj_data.get("target_meal", "dinner")
        user_foods = adj_data.get("user_foods", [])
        user_cal = adj_data.get("user_estimated_calories")
        reason = adj_data.get("reason", "manual")
        
        # Estimate if needed
        final_cal = user_cal
        dish_name = ", ".join(user_foods).title() if user_foods else "User Meal"
        
        if not final_cal and user_foods:
            # Call Estimator
            est = estimate_food_calories(self.db, user_foods)
            final_cal = est.get("calories", 500) # Fallback 500
            
        elif not final_cal:
            final_cal = 600 # Generic fallback
            
        # Refine Dish Name if generic
        if dish_name == "User Meal" and not user_foods:
             dish_name = "Custom Meal"
             
        # Format confirmation message
        response = (
            f"> **Meal Adjustment Proposal**\n>\n"
            f"> **Meal**: {target_meal.title()}\n"
            f"> **New Dish**: {dish_name}\n"
            f"> **Calories**: ~{int(final_cal)} kcal\n>\n"
            f"> *Shall I update your plan?*"
        )
        
        # Save to memory
        memory = ChatMemoryService(state["session_id"])
        memory.set_session_data("pending_meal_adjustment", {
            "target_meal": target_meal,
            "dish_name": dish_name,
            "calories": final_cal,
            "reason": reason
        })
        
        return {"final_response": response, "source": "AI Coach"}

    @observe(name="node_fetch_user_context")
    async def _node_fetch_user_context(self, state: GraphState) -> GraphState:
        """Node: Fetches the 'Auditor' profile and progress."""
        user_id = state["user_id"]
        context = self.stats_service.get_full_user_context(user_id)
        return {"user_context": context}

    @observe(name="node_fetch_history")
    async def _node_fetch_history(self, state: GraphState) -> GraphState:
        """Node: Fetches historical plan/logs if intent detected."""
        intent = state.get("intent_data")
        if not intent:
            return {"historical_context_str": ""}
            
        target_date = intent['date']
        user_id = state["user_id"]
        
        historical_context = self._get_historical_plan(user_id, target_date)
        hist_str = ""
        
        if historical_context:
            target_str = target_date.strftime('%A, %B %d, %Y')
            if historical_context.get('logs_count', 0) > 0:
                hist_str = (
                    f"=== 📜 HISTORICAL FORENSIC REPORT ===\n"
                    f"Target Date: {target_str}\n\n"
                    f"Based on your meal records for {target_str}, here is the plan you followed:\n\n"
                    f"1. **Plan vs Reality Summary**:\n{historical_context['summary']}\n\n"
                    f"2. **The Identified 'Active' Plan Details**:\n{json.dumps(historical_context['full_plan'], indent=2)}\n\n"
                    f"INSTRUCTION: Answer using this verified context. Mention deviations if noted in the summary."
                )
            else:
                hist_str = (
                    f"=== 📜 HISTORICAL DATA RETRIEVED ===\n"
                    f"Target Date: {target_str}\n\n"
                    f"According to your diet schedule for {target_str}, here is the plan:\n"
                    f"{json.dumps(historical_context['full_plan'], indent=2)}\n\n"
                    f"INSTRUCTION: State the plan clearly. Do NOT mention missing logs."
                )
        else:
            hist_str = (
                f"=== 📜 HISTORICAL DATA LOOKUP ===\n"
                f"Target Date: {target_date.strftime('%A, %B %d, %Y')}\n"
                f"Result: NO RECORD FOUND.\n"
                f"Instruction: Inform the user you couldn't find a stored diet plan for this specific date."
            )
            
        return {"historical_context_str": hist_str}

    @observe(name="node_fetch_knowledge")
    async def _node_fetch_knowledge(self, state: GraphState) -> GraphState:
        """Node: Fetches relevant foods/exercises from Vector/SQL."""
        msg = state["user_message"]
        search_term = self._extract_search_terms(msg)
        
        # Foods
        sql_foods = self.stats_service.search_food_by_name(search_term)
        vector_foods = self.vector_service.search_food(msg, limit=5)
        
        seen_foods = set()
        food_knowledge = []
        for f in sql_foods + vector_foods:
            if f['name'] not in seen_foods:
                food_knowledge.append(f)
                seen_foods.add(f['name'])
                
        # Exercises
        sql_exercises = self.stats_service.search_exercise_by_name(search_term)
        vector_exercises = self.vector_service.search_exercises(msg, limit=5)
        
        seen_exercises = set()
        ex_knowledge = []
        for e in sql_exercises + vector_exercises:
            if e['name'] not in seen_exercises:
                ex_knowledge.append(e)
                seen_exercises.add(e['name'])
                
        return {"food_knowledge": food_knowledge, "exercise_knowledge": ex_knowledge}

    @observe(name="node_generate")
    async def _node_generate(self, state: GraphState) -> GraphState:
        """Node: Generates the final response."""
        # Unpack state
        user_context = state["user_context"]
        food_know = state.get("food_knowledge", [])
        ex_know = state.get("exercise_knowledge", [])
        hist_str = state.get("historical_context_str", "")
        msg = state["user_message"]
        session_id = state["session_id"]
        
        # Load Memory
        memory = ChatMemoryService(session_id=session_id)
        # Note: We assume message was already persisted to memory/DB before graph or inside.
        # In this design, we'll do it before calling graph for safety.
        
        # Suggestions (reusing logic from original)
        suggestions = []
        today_name = datetime.now().strftime("%A")
        todays_activity = user_context.get('workout_plan', {}).get('schedule', {}).get(today_name, {})
        if not todays_activity:
             todays_activity = user_context.get('workout_plan', {}).get('schedule', {}).get(today_name.lower(), {})
        
        if isinstance(todays_activity, dict):
            focus = todays_activity.get('focus', '')
            exclude_list = [e.get('exercise', '') for e in todays_activity.get('exercises', [])]
            if focus:
                 suggestions = self.stats_service.get_suggested_exercises(focus, exclude_list, limit=5)

        # 2. Scope Detection
        include_diet = True
        include_workout = True
        
        u_msg_lower = msg.lower()
        diet_keywords = ['eat', 'food', 'meal', 'diet', 'calorie', 'macro', 'snack', 'breakfast', 'lunch', 'dinner', 'recipe']
        workout_keywords = ['workout', 'exercise', 'gym', 'lift', 'run', 'cardio', 'muscle', 'set', 'rep', 'train']
        
        is_diet_query = any(k in u_msg_lower for k in diet_keywords)
        is_workout_query = any(k in u_msg_lower for k in workout_keywords)
        
        if is_diet_query and not is_workout_query:
            include_workout = False
        elif is_workout_query and not is_diet_query:
            include_diet = False

        # Build Prompt
        system_prompt = self._build_system_prompt(
            user_context, food_know, ex_know, suggestions,
            include_diet=include_diet, include_workout=include_workout
        )
        
        if hist_str:
            system_prompt += f"\n\n{hist_str}"
            
        history = memory.get_messages()
        context_history_str = "\n".join([f"{m.type.upper()}: {m.content}" for m in history[:-1]])

        full_user_prompt = f"CONTEXT - CHAT HISTORY:\n{context_history_str}\n\nCURRENT USER MESSAGE:\n{msg}"
        
        response = call_llm(system_prompt=system_prompt, user_prompt=full_user_prompt, temperature=0.7)
        
        if not response:
            response = "I'm having trouble connecting to my brain right now. Please try again."
            
        # Determine Source
        source = "General AI"
        if food_know or ex_know:
            source = "Library"
        if "not in our library" in response.lower():
            source = "General AI"
            
        return {"final_response": response, "source": source}

    def _build_graph(self):
        """Builds the LangGraph state machine."""
        if StateGraph is None:
            return None
            
        workflow = StateGraph(GraphState)
        
        # Add Nodes
        workflow.add_node("detect_intent", self._node_detect_intent)
        workflow.add_node("process_social_event", self._node_process_social_event)
        workflow.add_node("process_meal_adjustment", self._node_process_meal_adjustment)
        workflow.add_node("fetch_user_context", self._node_fetch_user_context)
        workflow.add_node("fetch_history", self._node_fetch_history)
        workflow.add_node("fetch_knowledge", self._node_fetch_knowledge)
        workflow.add_node("generate", self._node_generate)
        
        # Define Edges
        workflow.set_entry_point("detect_intent")
        
        # CONDITIONAL ROUTING
        def intent_router(state: GraphState):
            if state.get("social_event_data"):
                return "process_social_event"
            if state.get("meal_adjustment_data"):
                return "process_meal_adjustment"
            return "fetch_user_context"

        workflow.add_conditional_edges(
            "detect_intent",
            intent_router,
            {
                "process_social_event": "process_social_event",
                "process_meal_adjustment": "process_meal_adjustment",
                "fetch_user_context": "fetch_user_context"
            }
        )
        
        # Social Event Path -> END (It generates final response)
        workflow.add_edge("process_social_event", END)
        workflow.add_edge("process_meal_adjustment", END)
        
        # Standard Path
        workflow.add_edge("fetch_user_context", "fetch_history")
        workflow.add_edge("fetch_history", "fetch_knowledge")
        workflow.add_edge("fetch_knowledge", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()

    @observe(name="fitness_coach_get_response")
    async def get_response(self, user_message: str, user_id: int, session_id: str) -> dict:
        # Load memory for this specific session
        memory = ChatMemoryService(session_id=session_id)
        
        # HYDRATION STEP
        if memory.is_empty():
            print(f"[Memory] Session {session_id} is empty. Hydrating from DB...")
            self._hydrate_session_from_db(memory, user_id, session_id)
        
        # 0. Check for "List Questions" Intent
        low_msg = user_message.lower().strip()
        list_intents = [
            "list out all the question", "list all questions", "what did i ask", 
            "show my questions", "list my questions", "list out questions",
            "list questions", "show questions", "what have i asked"
        ]
        
        if any(intent in low_msg for intent in list_intents):
            questions = memory.get_session_questions()
            if not questions:
                 self._hydrate_session_questions_from_db(memory, session_id)
                 questions = memory.get_session_questions()

            if not questions:
                return {"content": "You haven't asked any questions in this session yet.", "source": "system"}
            
            q_list = "\n".join([f"- {q}" for q in questions])
            return {"content": f"Here are the questions you've asked in this chat:\n\n{q_list}", "source": "memory"}

        # 1. Capture User Query
        if user_message.strip():
            memory.add_question_to_session(user_message.strip())

        # 2. RUN GRAPH
        print(f"\n--- [Coach] Processing Message via LangGraph: '{user_message}' ---")
        
        # We add the user message to memory first (to match original logic)
        self.memory_service.add_user_message(user_message)
        self._persist_message(user_id, "user", user_message)
        
        # Build and Run Graph
        app = self._build_graph()
        if not app:
             return {"content": "Error: Graph could not be initialized.", "source": "error"}

        initial_state = {
            "user_message": user_message,
            "user_id": user_id,
            "session_id": session_id,
            "intent_data": None,
            "historical_context_str": "",
            "food_knowledge": [],
            "exercise_knowledge": []
        }
        
        try:
            # Invoke Graph
            inputs = initial_state
            result = await app.ainvoke(inputs)
            
            final_response = result.get("final_response", "I'm having trouble thinking right now.")
            source = result.get("source", "General AI")
            
            # 3. Update Memory with AI response
            self.memory_service.add_ai_message(final_response)
            self._persist_message(user_id, "assistant", final_response)
            
            return {"content": final_response, "source": source}
            
        except Exception as e:
            print(f"[Graph Error]: {e}")
            import traceback
            traceback.print_exc()
            return {"content": "Sorry, I encountered an error processing your request.", "source": "error"}

        return response

    def _persist_message(self, user_id: int, role: str, content: str):
        """Save a message to the long-term PostgreSQL database."""
        try:
            chat_record = ChatHistory(user_id=user_id, role=role, content=content)
            self.db.add(chat_record)
            self.db.commit()
        except Exception as e:
            print(f"Error saving chat history: {e}")
            self.db.rollback()

    def _hydrate_session_from_db(self, memory: ChatMemoryService, user_id: int, session_id: str):
        """
        Loads the last 10 messages from PostgreSQL and sets them in Redis.
        Also populates the questions list.
        """
        try:
            # 1. Get Messages
            # Ensure we strip the prefix if session_id passed has it (FitnessCoachService adds "user_X_")
            # But the DB stores usually the raw UUID.
            # Let's check session usage. in `chat.py`, `session_key` passed to Coach is `user_{id}_{uuid}`.
            # But in DB `ChatHistory.session_id` stores just `{uuid}` (from `request.session_id`).
            
            raw_session_id = session_id
            if session_id.startswith(f"user_{user_id}_"):
                raw_session_id = session_id.replace(f"user_{user_id}_", "")

            history = self.db.query(ChatHistory).filter(
                ChatHistory.session_id == raw_session_id
            ).order_by(ChatHistory.id.desc()).limit(10).all()
            
            if not history:
                return
            
            # Sort back to Chronological
            history.reverse()
            
            lc_messages = []
            from langchain_core.messages import HumanMessage, AIMessage
            
            for msg in history:
                if msg.role == "user":
                    lc_messages.append(HumanMessage(content=msg.content))
                else:
                     lc_messages.append(AIMessage(content=msg.content))
            
            memory.hydrate_messages(lc_messages)
            
            # 2. Hydrate Questions as well
            self._hydrate_session_questions_from_db(memory, raw_session_id)
            
        except Exception as e:
            print(f"[Hydration] Failed to sync session {session_id}: {e}")

    def _hydrate_session_questions_from_db(self, memory: ChatMemoryService, raw_session_id: str):
        """
        Scans DB history for user questions and populates Redis set.
        """
        try:
            # We want ALL user messages from this session to extract questions, 
            # effectively rebuilding the "Questions Asked" list.
            # Limit to reasonable amount (e.g. 50 last interaction) so we don't scan forever if huge.
            user_msgs = self.db.query(ChatHistory).filter(
                ChatHistory.session_id == raw_session_id,
                ChatHistory.role == "user"
            ).order_by(ChatHistory.id.desc()).limit(50).all()
            
            questions = []
            for msg in user_msgs:
                text = msg.content.strip()
                low_text = text.lower()
                is_q = text.endswith("?") or \
                       low_text.startswith(("what", "how", "why", "when", "where", "can", "is", "do", "does", "will", "list"))
                
                if is_q:
                    questions.append(text)
            
            if questions:
                memory.hydrate_questions(questions)
                print(f"[Hydration] Restored {len(questions)} questions for session {raw_session_id}")
                
        except Exception as e:
             print(f"[Hydration] Failed to sync questions: {e}")

    def _build_system_prompt(self, context, food_knowledge=None, exercise_knowledge=None, suggestions=None, include_diet=True, include_workout=True):
        """
        Constructs the system prompt based on user context.
        Supports conditional inclusion of sections.
        """
        profile = context.get("profile", {})
        diet = context.get("diet_plan", [])
        workout = context.get("workout_plan", {})
        prefs = context.get("preferences", {})

        # Format Profile
        profile_str = (
            f"User: {profile.get('name', 'User')}, {profile.get('age', 25)}y/{profile.get('gender', 'male')}, "
            f"{profile.get('height', 170)}cm, {profile.get('weight', 70)}kg. "
            f"Goal: {profile.get('goal', 'Health')}."
        )
        target_str = (
            f"Targets: {profile.get('targets', {}).get('calories', 0)} kcal, "
            f"P:{profile.get('targets', {}).get('protein', 0)}g, "
            f"C:{profile.get('targets', {}).get('carbs', 0)}g, "
            f"F:{profile.get('targets', {}).get('fat', 0)}g"
        )
    
        # Format Diet - Detailed Breakdown
        diet_str = "Daily Diet (CURRENT PLAN - USE THIS EXACT DATA):\n"
        if diet:
            for m in diet:
                diet_str += f"\n[{m['meal'].upper()}]\n"
                diet_str += f"Dish: {m['dish']}\n"
                diet_str += f"Portion: {m.get('portion_size', 'Standard serving')}\n"
                diet_str += f"Macros: {int(m.get('protein',0))}g P, {int(m.get('carbs',0))}g C, {int(m.get('fat',0))}g F ({int(m.get('calories',0))} kcal)\n"
                if m.get('guidelines'):
                    diet_str += f"Guidelines: {', '.join(m['guidelines'])}\n"
                if m.get('alternatives'):
                    diet_str += f"Alternatives: {', '.join(m['alternatives'])}\n"
        else:
            diet_str += "No diet plan generated."

        # Format Workout
        schedule = workout.get('schedule', {})
        schedule_str = "Weekly Workout Schedule:\n"
        if schedule:
            for day, activity in schedule.items():
                if isinstance(activity, dict):
                    # Detailed breakdown
                    day_name = activity.get('day_name', day)
                    focus = activity.get('focus', 'Unspecified')
                    schedule_str += f"- {day_name} ({focus}):\n"
                
                    # Exercises
                    exercises = activity.get('exercises', [])
                    for ex in exercises:
                        name = ex.get('exercise', 'Unknown')
                        sets = ex.get('sets', 0)
                        reps = ex.get('reps', '0')
                        schedule_str += f"    * {name}: {sets} sets x {reps}\n"
                    
                    # Cardio
                    cardio = activity.get('cardio_exercises', [])
                    for c in cardio:
                        name = c.get('exercise', 'Unknown')
                        dur = c.get('duration', '20min')
                        schedule_str += f"    * Cardio: {name} ({dur})\n"
                else:
                    # Legacy or string format
                    schedule_str += f"- {day}: {activity}\n"
        else:
            schedule_str += "No workout plan generated."
        
        prefs_str = f"Preferences: Level {prefs.get('level')}, {prefs.get('days_per_week')} days/week. Health Issues: {prefs.get('health_issues')}."

        # Knowledge Context
        food_context = "\n".join([f"- {f.get('name', 'Unknown')}: {f.get('calories',0)}kcal, Pro: {f.get('protein',0)}g" for f in food_knowledge])
        ex_context = "\n".join([f"- {e.get('name', 'Unknown')}: {e.get('muscle_group', 'General')}" for e in exercise_knowledge])

        # Format Progress (The Auditor)
        progress = context.get("progress", {})
        completed = progress.get("completed_exercises", [])
        completed_str = ", ".join(completed) if completed else "None"
    
        # Context: Smart Activity (Latest Workout if today is 0)
        latest = progress.get("latest_workout")
        previous = progress.get("previous_workout")
    
        last_log_str = ""
        # 1. If today is empty, remind of latest activity
        if int(progress.get('calories_burned_today', 0)) == 0 and latest:
             last_log_str += f"           Last Logged Activity: {latest['date']} ({latest['exercise']}, {int(latest['calories'])} kcal).\n"
    
        # 2. Comparison Context (Previous Session)
        if previous:
             last_log_str += f"           Previous Workout: {previous['date']} ({previous['exercise']}, {int(previous['calories'])} kcal).\n"

        progress_str = (
            f"Status Today: {int(progress.get('calories_eaten', 0))}/{int(profile.get('targets', {}).get('calories', 0))} kcal. "
            f"Macros: {int(progress.get('protein_eaten', 0))}g P, {int(progress.get('carbs_eaten', 0))}g C, {int(progress.get('fat_eaten', 0))}g F.\n"
            f"           Workouts (Last 7 Days): {progress.get('workouts_last_7_days', 0)}.\n"
            f"           Completed Exercises Today: {completed_str}.\n"
            f"           Calories Burned Today: {int(progress.get('calories_burned_today', 0))} kcal.\n"
            f"{last_log_str}"
            f"           Calories Burned Last 7 Days: {int(progress.get('calories_burned_last_7_days', 0))} kcal.\n"
            f"           Weight Goal: {profile.get('weight', 0)}kg -> {profile.get('weight_goal', 'Not Set')}kg."
        )

        # Date Context
        today_str = datetime.now().strftime("%A, %B %d, %Y")

        prompt = f"""
        # ROLE & IDENTITY
        You are FitCoach AI, a supportive and knowledgeable fitness assistant for {profile.get('name', 'User')}.
        You help with diet plans, workout routines, and the unique "Feast Mode" feature for social events.
        Current Date: {today_str}
    
        ## YOUR PERSONALITY
        - Encouraging and motivating, never judgmental (like a supportive gym buddy)
        - Casual, friendly language with occasional emojis (💪🎯🔥) but not excessive
        - Celebrate small wins enthusiastically
        - Empathetic when users struggle or fail
        - Balance being informative without being preachy
        - Match user's energy level (excited user = excited response)
        - If user is frustrated, be extra patient and solution-focused
    
        ## RESPONSE LENGTH GUIDELINES
        - Quick questions: 1-3 sentences
        - Explanations: 4-6 sentences with structure
        - Complex requests: Break into digestible chunks
        - Keep responses concise unless user asks for detailed explanation
    
        === USER DOSSIER (THE AUDITOR) ===
        1. PROFILE:
           {profile_str}
           {target_str}
           {prefs_str}
       
        2. REAL-TIME PROGRESS (THE AUDITOR):
           {progress_str}
        """
    
        if include_diet:
            prompt += f"""
        3. DIET PLAN (SCHEDULED):
           {diet_str}
        """
    
        if include_workout:
            prompt += f"""
        4. WORKOUT SCHEDULE:
           {schedule_str}
        """
    
        prompt += f"""
        === KNOWLEDGE BASE (THE LIBRARIAN) ===
        Relevant Data found for query:
        Foods:
        {food_context}
        Exercises:
        {ex_context}
    
        === VERIFIED SUGGESTIONS (DATABASE) ===
        Based on today's focus, here are valid extra exercises from our library:
        {chr(10).join([f"- {s['name']} (Target: {s['muscle']})" for s in suggestions])}
        Use these EXACT NAMES if the user asks for "more exercises" or variations.
    
        === CORE CAPABILITIES ===
        You can:
        1. Answer questions about nutrition, workouts, and fitness
        2. Explain user's current diet and workout plans (using the data above)
        3. Provide insights on progress and suggest improvements
        4. Suggest meal swaps and alternatives within calorie budgets
        5. Explain exercise form and techniques
        6. Calculate remaining calories and suggest foods that fit
        7. Handle Feast Mode (social buffer) for upcoming events
        8. Provide motivation and tactical recovery when users miss workouts
    
        You CANNOT:
        - Modify database directly (guide users to regenerate plans instead)
        - Provide medical diagnosis or treatment
        - Replace professional medical advice
        - Guarantee specific results
        - Make users feel guilty about choices
    
        === INSTRUCTIONS ===
    
        ## 1. OMNISCIENT PERSONALIZATION
        - Use the DOSSIER to answer specific questions like "What is my workout on Friday?" or "How much protein do I need?"
        - You know their height, weight, goal, and full schedule. Use it naturally.
        - Always use their name ({profile.get('name', 'User')}) in conversation naturally
        - Remember their dietary restrictions: {prefs.get('health_issues', 'None')}
    
        **PROFILE CONSISTENCY CHECK**:
        - IF user asks for something contradictory to their current profile (e.g., User goal is 'Weight Loss' but asks "How to gain weight?"):
          - **REPLY**: "Currently your priority and profile is {profile.get('goal', 'Health')}, but to update any profile data you need to update your profile from the profile section."
    
        ## 2. KNOWLEDGE RETRIEVAL
        - Use the KNOWLEDGE BASE for specific food/exercise stats provided above
        - When recommending foods, reference their actual calories and macros from the knowledge base
        - Show your calculations when relevant (builds trust)
    
        ## 3. CONTEXTUAL PLANNING
        **Remaining Calories Calculation**:
        - IF user asks "What should I eat?" or mentions "Calories left", CALCULATE their Remaining Limit (Target - Eaten)
        - Current remaining: {int(profile.get('targets', {}).get('calories', 0)) - int(progress.get('calories_eaten', 0))} kcal
        - RECOMMEND specific foods from the KNOWLEDGE BASE that fit
        - Example: "You have 400kcal left. Grilled Chicken (165kcal) or Greek Yogurt (120kcal) would fit perfectly 🎯"
    
        **Smart Suggestions**:
        - Anticipate follow-up questions and offer relevant suggestions
        - Example: After answering about protein, mention "Want breakfast ideas to boost that?"
        - Don't be pushy, just helpful
    
        ## 4. STRATEGIST (Plan Modifications)
        **Important**: You cannot modify the database directly.
    
        - IF user asks to CHANGE/SWAP/UPDATE their Diet or Workout (e.g., "I don't like eggs", "Change Friday to cardio", "Add more protein"):
          - **DO NOT** say you found it or changed it
          - **DO NOT** generate a specific command
          - **INSTEAD, GUIDE THEM**: "To make this change, please navigate to the **Diet Plan** or **Workout Plan** page and use the **Regenerate Plan** feature. You can provide your specific requirements there to get an updated plan."
    
        **Alternative Suggestions (Without Database Changes)**:
        - You CAN suggest immediate swaps using foods from the KNOWLEDGE BASE
        - Example: "Don't like eggs? Try Greek yogurt (similar protein) or cottage cheese instead for tomorrow. For a permanent change, regenerate your plan from the Diet Plan page."
    
        ## 5. RECOVERY MODE (Missed Workout)
        - IF user reports a MISSED session, stop being just "supportive". Be TACTICAL.
        - No guilt trips! Acknowledge it happens, then offer solutions:
      
          **Option A - Calorie Adjustment**: "Since you missed the gym, let's aim for -300kcal at dinner to stay on track."
      
          **Option B - Quick Home Circuit**: "Can you spare 15 mins? Do 3 rounds of: Pushups (10 reps), Squats (15 reps), Plank (30 sec). Better than nothing! 💪"
      
          **Option C - Make it up**: "No worries! Can you hit the gym tomorrow? We can shift today's workout there."
    
        ## 6. FEAST MODE (SOCIAL BUFFER) HANDLING
        **Trigger Words**: "wedding", "party", "dinner out", "birthday", "date night", "event", "celebration"
    
        **When User Mentions Social Event**:
        1. Immediately recognize and get excited! Use celebratory tone 🎉
        2. Ask clarifying questions:
           - "When's the event?"
           - "What type? (wedding/party/restaurant/other)"
           - "How indulgent are we talking? Light, moderate, or full celebration mode?"
        3. Explain Feast Mode benefits proactively
        4. Calculate banking plan and present it clearly
        5. Get explicit confirmation before "activating"
    
        **Example Response**:
        "Ooh, a wedding! 🎉 Perfect time for Feast Mode.
    
        Here's the plan:
        • I'll bank calories Tue-Fri (small unnoticeable cuts)
        • You'll save ~800 extra calories for Saturday
        • Morning of: glycogen-depletion leg workout
        • Result: Enjoy the wedding guilt-free!
    
        Sound good? Want me to walk you through the details?"
    
        **During Banking Period**:
        - Daily check-ins with encouragement
        - Acknowledge the subtle restrictions positively
        - Remind them WHY (the upcoming event)
        - Example: "Day 2/4 of Feast Mode! Bank balance: 350 cal saved. Almost halfway to that pizza party 🎯"
    
        **Event Day**:
        - Hype them up! Use celebratory language
        - Remind about prep workout (glycogen depletion)
        - Give PERMISSION to enjoy guilt-free
        - Example: "It's FEAST DAY! 🎉 You banked 700 calories. Go enjoy that wedding - you earned it! No guilt, no tracking, just fun."
        - NO calorie shaming or warnings
    
        **Post-Event**:
        - Celebrate that they enjoyed life AND stayed on track
        - Show the math briefly
        - Get back to normal without dwelling
        - Example: "How was the wedding? Your Feast Mode worked perfectly - banked 700 cal, enjoyed the night, net impact minimal. Back to regular programming today! 💪"
    
        === 🛡️ GUARDRAILS (STRICT ENFORCEMENT) ===
    
        ## 1. 🚑 MEDICAL WALL (ABSOLUTE REFUSAL)
        **Triggers**: "pain", "hurt", "swollen", "injury", "doctor", "medication", "supplement for pain", "healing", "recovery from injury"
    
        **ACTION**: You MUST refuse. Do not try to be helpful with "gentle exercises"
    
        **RESPONSE**: "I'm an AI fitness coach, not a doctor. Please consult a medical professional for any pain or injury before we work on fitness together. Your safety comes first! ⚠️"
    
        ## 2. 🚫 OUT OF SCOPE
        **Triggers**: Politics, Sports Scores, Coding, Homework, General Trivia, Non-fitness topics
    
        **ACTION**: Politely decline and redirect
    
        **RESPONSE**: "I'm here to help with your fitness and nutrition goals! I can't help with that, but let's get back to your {profile.get('goal', 'health journey')}. What can I help you with today?"
    
        ## 3. ⚠️ EXTREME/UNSAFE ADVICE
        **Triggers**: 
        - Very low calories (<1200kcal for women, <1500kcal for men)
        - Starvation diets or extreme fasting
        - Dangerous supplements or quick fixes
        - Overtraining (7+ days intense workouts without rest)
        - Single meal > 1000 kcal requests
    
        **ACTION**: Refuse and warn, then offer healthy alternative
    
        **RESPONSE**: "That approach isn't safe or sustainable, and I can't recommend it. Let's find a balanced way to reach your goal that keeps you healthy and energized. How about we aim for [safer alternative]?"
    
        ## 4. 😔 HANDLING USER STRUGGLES
        **When User Says**:
        - "I broke my diet" / "I overate" / "I failed"
    
        **❌ NEVER**: "You shouldn't have done that" or "That's a setback"
    
        **✅ ALWAYS**: Empathetic + Solution
        - "Hey, it happens to everyone! One meal doesn't define your journey. Want to do a light Feast Mode retroactively to balance things out?"
        - "No worries! You're still {progress.get('workouts_last_7_days', 0)} workouts strong this week. Let's get back on track today 💪"
    
        **When User is Demotivated**:
        - Acknowledge feelings first
        - Remind of past progress from their data
        - Suggest smaller, achievable goals
        - Offer to adjust plan to make it easier
        - Example: "I get it, some days are tough. But you've logged {progress.get('workouts_last_7_days', 0)} workouts this week - that's not luck, that's YOU showing up. What's feeling hardest right now?"
    
        ## 5. 🎯 CONVERSATION FLOW PATTERNS
    
        **Quick Query**:
        User: "Is oatmeal good for breakfast?"
        You: "Yes! Oatmeal is excellent - complex carbs for sustained energy, fiber for fullness. Add protein (Greek yogurt or protein powder) to make it more balanced 🥣"
    
        **Vague Request**:
        User: "I want to get fit"
        You: "Love the motivation! Let's get specific:
        - Lose fat, build muscle, or both?
        - What's your timeframe?
        - Any areas you want to focus on?
    
        The clearer your goal, the better I can help!"
    
        **Problem Solving**:
        User: "I'm always hungry on my diet"
        You: "Let's fix that! Looking at your stats... you're at {int(progress.get('protein_eaten', 0))}g protein today. Let's bump that to {int(profile.get('targets', {}).get('protein', 0))}g - protein keeps you full longer. Want meal ideas to boost it?"
    
        === FINAL REMINDERS ===
        - Use their name: {profile.get('name', 'User')}
        - Reference their specific data when relevant
        - Be conversational, not robotic
        - Show empathy and encouragement
        - No excessive formatting (avoid bullet points unless essential)
        - Respond in natural prose/paragraphs for casual conversation
        - Keep it concise and actionable
        - Safety first, always
    
        Respond directly to the user now.
        """
    
        return prompt
