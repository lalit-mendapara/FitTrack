
import re
from typing import Dict, List, Tuple

# --- MOCKED CONSTANTS & HELPERS ---
UNIT_WEIGHTS = {
    "apple": 150, "roti": 40, "chapati": 40, "egg": 50, "slice": 35
}

FALLBACK_MACROS = {
    "roti": {"p": 7.0, "c": 45.0, "f": 2.0, "cal": 230}, # Per 100g
    "paneer": {"p": 18.0, "c": 1.2, "f": 20.0, "cal": 265},
    "rice": {"p": 2.5, "c": 28, "f": 0.3, "cal": 130}
}
# Roti 40g = ~92kcal. 2 Roti = 184kcal.

def calculate_meal_macros_mock(portion_str: str) -> Dict:
    analysis = {"items": [], "total_cal": 0, "total_p": 0, "total_c": 0, "total_f": 0}
    
    clean_str = portion_str.replace('+', ',')
    parts = [p.strip() for p in clean_str.split(',') if p.strip()]
    
    for part in parts:
        weight = 0
        name = ""
        is_fixed = False
        source = ""
        density = {"p": 0, "c": 0, "f": 0, "cal": 0}

        # Regex for count (simulating app logic)
        count_match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:(slice|pc|pcs)\b)?\s*(.+)$', part, re.IGNORECASE)
        strict_match = re.match(r'^(\d+(?:\.\d+)?)\s*(g|ml)\s+(.+)$', part, re.IGNORECASE)

        if strict_match:
            qty, unit, n = strict_match.groups()
            weight = float(qty)
            name = n.strip()
            is_fixed = False # Strict is Variable
            source = "Strict"
        elif count_match:
            qty, unit, n = count_match.groups()
            count = float(qty)
            name = n.strip()
            # Determine weight
            u_w = 100
            if "roti" in name.lower(): u_w = 40
            if "chapati" in name.lower(): u_w = 40
            
            weight = count * u_w
            is_fixed = True # Count is Fixed!
            source = f"Count({count})"
        else:
            name = part
            weight = 100
            is_fixed = True
            source = "Implicit"
            
        # Get Density
        for k, v in FALLBACK_MACROS.items():
            if k in name.lower():
                density = {k2: v2/100 for k2, v2 in v.items()}
                break
        
        # Add item
        analysis["items"].append({
            "name": name, "weight": weight, "density": density, "source": source, "is_fixed": is_fixed
        })
        analysis["total_cal"] += weight * density["cal"]
        
    return analysis

def _identify_sources(analysis):
    items = analysis["items"]
    variable_items = [i for i in items if not i.get("is_fixed", False)]
    if not variable_items: return None
    p_source = max(variable_items, key=lambda x: x["density"]["p"])
    remaining = [i for i in variable_items if i != p_source]
    c_source = max(remaining, key=lambda x: x["density"]["c"]) if remaining else p_source
    return {"p_item": p_source, "c_item": c_source}

def _optimize_weights_least_squares(p_item, c_item, fixed_cal, target_cal):
    # Simplified optimizer for test: just tries to match calories
    # Real one is more complex but this tests if it RUNS
    rem_cal = target_cal - fixed_cal
    if rem_cal < 0: return 0, 0 # Impossible to match if fixed > target
    
    # Just return dummy valid weights if it worked
    return 100, 100 

def test_optimization():
    # Case 1: "2 Roti, 200g Paneer"
    # Target: 300 kcal.
    # 2 Roti (Fixed) = 2 * 40g * 2.3kcal/g = 184 kcal.
    # 200g Paneer (Variable) = 200 * 2.65 = 530 kcal.
    # Total Init = 714 kcal.
    # Target = 300.
    
    # Paneer is Variable. Roti is Fixed.
    # Fixed Cal = 184. Remaining allowed = 116.
    # Paneer should reduce to ~44g (116 kcal).
    
    analysis = calculate_meal_macros_mock("2 Roti, 200g Paneer")
    print("Initial Analysis:", analysis)
    
    sources = _identify_sources(analysis)
    print("Sources Identified:", sources)
    
    if not sources:
        print("FAIL: No sources (All fixed?)")
        return

    fixed_cal = sum(i["weight"] * i["density"]["cal"] for i in analysis["items"] if i["is_fixed"])
    print(f"Fixed Cal: {fixed_cal}")
    
    # Case 2: "2 Roti, 100g Rice" (Target 150)
    # 2 Roti = 184 (Fixed).
    # Target = 150.
    # Remaining = -34.
    # Optimizer receives target < fixed.
    
    analysis2 = calculate_meal_macros_mock("2 Roti, 100g Rice")
    fixed_cal2 = sum(i["weight"] * i["density"]["cal"] for i in analysis2["items"] if i["is_fixed"])
    print(f"\nCase 2 Fixed Cal: {fixed_cal2} vs Target 150")
    if fixed_cal2 > 150:
        print("FAIL: Fixed items exceed target. Optimizer cannot reduce.")
        
test_optimization()
