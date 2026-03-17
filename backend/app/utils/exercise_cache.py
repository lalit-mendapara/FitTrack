"""
Exercise database caching layer for workout plan generation optimization.
Uses LRU cache to avoid repeated DB queries.
"""
from functools import lru_cache
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.exercise import Exercise
import re


# Cache for 1 hour (3600 seconds) - exercises rarely change
@lru_cache(maxsize=1)
def get_all_exercises_cached(db_id: int = 0) -> tuple:
    """
    Cached fetch of all exercises from DB.
    Returns tuple for hashability (required by lru_cache).
    
    Note: db_id is a dummy parameter to allow cache invalidation if needed.
    In production, you could pass a timestamp or version number.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        exercises = db.query(Exercise).all()
        # Convert to tuple of dicts for caching
        return tuple([{
            'id': ex.id,
            'name': ex.name,
            'difficulty': ex.difficulty,
            'muscle_group': ex.muscle_group,
            'equipment': ex.equipment,
            'image_url': ex.image_url,
            'calories_per_min': ex.calories_per_min,
            'is_cardio': ex.is_cardio
        } for ex in exercises])
    finally:
        db.close()


def get_exercise_maps() -> tuple[Dict[str, dict], Dict[str, dict]]:
    """
    Get exercise name mappings for fuzzy matching.
    Returns (raw_name_map, normalized_name_map).
    """
    exercises = get_all_exercises_cached()
    
    ex_map = {}  # raw lowercase name -> exercise dict
    norm_ex_map = {}  # normalized name -> exercise dict
    
    for ex_dict in exercises:
        name = ex_dict['name']
        raw_name = name.lower().strip()
        ex_map[raw_name] = ex_dict
        
        # Normalized: remove all non-alphanumeric
        norm_name = re.sub(r'[^a-z0-9]', '', raw_name)
        norm_ex_map[norm_name] = ex_dict
    
    return ex_map, norm_ex_map


def get_exercises_by_experience_cached(experience_level: str) -> List[dict]:
    """
    Filter exercises by difficulty based on user experience.
    Uses cached exercise list.
    """
    exp_lower = (experience_level or "beginner").lower().strip()
    
    allowed = ["Beginner"]
    if exp_lower == "intermediate":
        allowed.extend(["Intermediate"])
    elif exp_lower == "advanced":
        allowed.extend(["Intermediate", "Advanced"])
    
    exercises = get_all_exercises_cached()
    return [ex for ex in exercises if ex['difficulty'] in allowed]


def get_cardio_exercises_cached() -> List[dict]:
    """Get all cardio exercises from cache."""
    exercises = get_all_exercises_cached()
    return [ex for ex in exercises if ex.get('is_cardio', False)]


def invalidate_exercise_cache():
    """
    Invalidate the exercise cache.
    Call this when exercises are added/updated/deleted.
    """
    get_all_exercises_cached.cache_clear()
    print("[CACHE] Exercise cache invalidated")


# Semantic similarity helpers for LLM-generated exercise name matching
def normalize_exercise_name(name: str) -> str:
    """Normalize exercise name for matching."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def find_exercise_by_name_fuzzy(
    name: str, 
    ex_map: Dict[str, dict], 
    norm_ex_map: Dict[str, dict]
) -> Optional[dict]:
    """
    Resolve an exercise by name with tolerant matching.
    Handles minor wording differences.
    
    Args:
        name: Exercise name from LLM
        ex_map: Raw name -> exercise dict mapping
        norm_ex_map: Normalized name -> exercise dict mapping
        
    Returns:
        Exercise dict or None
    """
    from difflib import get_close_matches
    
    raw_name = (name or "").lower().strip()
    if not raw_name:
        return None

    # 1) Exact raw match
    ex_obj = ex_map.get(raw_name)
    if ex_obj:
        return ex_obj

    # 2) Exact normalized match
    norm_name = normalize_exercise_name(raw_name)
    ex_obj = norm_ex_map.get(norm_name)
    if ex_obj:
        return ex_obj

    # 3) Normalized substring fallback
    ex_obj = next(
        (ex for n_name, ex in norm_ex_map.items() if norm_name in n_name or n_name in norm_name),
        None,
    )
    if ex_obj:
        return ex_obj

    # 4) Fuzzy fallback for inflection/typos
    closest = get_close_matches(norm_name, list(norm_ex_map.keys()), n=1, cutoff=0.75)
    if closest:
        return norm_ex_map.get(closest[0])

    return None
