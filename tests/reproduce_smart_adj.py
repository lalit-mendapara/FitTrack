
import json
from typing import List, Dict, Any

# --- MOCK DATA & FUNCTIONS ---

def calculate_meal_macros_mock(portion_str: str) -> Dict:
    """Mock parser that knows a few ingredients."""
    items = []
    total_metrics = {"p": 0, "c": 0, "f": 0, "cal": 0}
    
    # Simple parser: "100g Chicken"
    parts = portion_str.split(" + ")
    
    db = {
        "Chicken": {"p": 0.27, "c": 0.0, "f": 0.14, "cal": 2.39}, 
        "Rice":    {"p": 0.025, "c": 0.28, "f": 0.003, "cal": 1.30}, 
        "Roti":    {"p": 0.07, "c": 0.45, "f": 0.02, "cal": 2.30}, 
        "Oil":     {"p": 0.0, "c": 0.0, "f": 1.0, "cal": 9.00}, 
        "Paneer":  {"p": 0.18, "c": 0.01, "f": 0.20, "cal": 2.65}, 
        "Dal":     {"p": 0.06, "c": 0.18, "f": 0.01, "cal": 1.05}, 
        "Salad":   {"p": 0.01, "c": 0.05, "f": 0.0, "cal": 0.25}
    }
    
    for part in parts:
        try:
            if not part.strip(): continue
            qty_str, name = part.strip().split(" ", 1)
            weight = float(qty_str.replace("g", "").replace("ml", ""))
            
            clean_name = name.strip()
            density = {"p": 0, "c": 0, "f": 0, "cal": 0}
            
            for k, v in db.items():
                if k.lower() in clean_name.lower():
                    density = v
                    break
            
            items.append({
                "name": clean_name,
                "weight": weight,
                "density": density
            })
            
            total_metrics["p"] += weight * density["p"]
            total_metrics["c"] += weight * density["c"]
            total_metrics["f"] += weight * density["f"]
            total_metrics["cal"] += weight * density["cal"]
            
        except Exception as e:
            pass

    return {
        "items": items,
        "total_p": total_metrics["p"],
        "total_c": total_metrics["c"],
        "total_f": total_metrics["f"],
        "total_cal": total_metrics["cal"]
    }

# --- IMPROVED LOGIC ---

def adjust_portions_smart(meals: List[Dict], targets: Dict) -> List[Dict]:
    print("\n[Smart Adjustment] Attempting to fix macro deviations (Iterative + Scoring)...")
    
    adjusted_meals = [m.copy() for m in meals]
    max_passes = 3
    
    for pass_idx in range(max_passes):
        print(f"\n--- Pass {pass_idx + 1} ---")
        
        # 1. Calc Current State
        current_totals = {"p": 0, "c": 0, "f": 0, "cal": 0}
        for m in adjusted_meals:
            # We must recalc from portion_size string to be sure
            a = calculate_meal_macros_mock(m["portion_size"])
            m["nutrients"] = {"p": a["total_p"], "c": a["total_c"], "f": a["total_f"], "cal": a["total_cal"]}
            for k in current_totals: current_totals[k] += m["nutrients"][k]

        current_deviations = []
        locked_metrics = []
        
        for metric, target in targets.items():
            val = current_totals[metric[:1]] if metric != "calories" else current_totals["cal"]
            diff = val - target
            pct = (diff / target) * 100
            if abs(pct) > 5:
                current_deviations.append({"metric": metric, "diff": diff, "pct": pct})
            else:
                locked_metrics.append(metric)
        
        print(f"  Totals: P:{current_totals['p']:.0f} C:{current_totals['c']:.0f} F:{current_totals['f']:.0f} Cal:{current_totals['cal']:.0f}")
        print(f"  Deviations: {[(d['metric'], round(d['pct'],1)) for d in current_deviations]}")
        
        if not current_deviations:
            print("  Converged!")
            break
            
        current_deviations.sort(key=lambda x: abs(x["pct"]), reverse=True)
        focus = current_deviations[0]
        metric = focus["metric"]
        deficit = -focus["diff"]
        
        print(f"  > Focusing: {metric.upper()} (Deficit: {deficit:.1f})")
        
        meal_target = deficit / len(adjusted_meals)
        
        for meal in adjusted_meals:
            parsed = calculate_meal_macros_mock(meal["portion_size"])
            items = parsed["items"]
            if not items: continue
            
            # Find Candidates (items that have density > 0 for target metric)
            m_key = metric[:1] if metric != "calories" else "cal"
            candidates = [x for x in items if x["density"][m_key] > 0]
            
            if not candidates: continue
            
            # Score Candidates
            scored = []
            for cand in candidates:
                d = cand["density"]
                score = d[m_key] * 10 # Base score: efficiency
                
                # Side Effects
                for other in current_deviations:
                    if other["metric"] == metric: continue
                    om_key = other["metric"][:1] if other["metric"] != "calories" else "cal"
                    impact = d[om_key]
                    
                    # If Adding (Deficit > 0): 
                    # Bonus if other is Low (diff < 0), Penalty if other is High (diff > 0)
                    if deficit > 0:
                        if other["diff"] < 0: score += impact * 5 
                        else: score -= impact * 20
                    else: # Removing
                        if other["diff"] > 0: score += impact * 5
                        else: score -= impact * 20
                
                scored.append((score, cand))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            best_cand = scored[0][1]
            
            # Calculate Change
            needed = meal_target / best_cand["density"][m_key]
            needed *= 0.8 # Learning rate
            
            old_w = best_cand["weight"]
            new_w = max(10, old_w + needed)
            if new_w > 500: new_w = 500
            actual_delta = new_w - old_w
            
            best_cand["weight"] = new_w
            
            # Compensate Calories?
            if "calories" in locked_metrics:
                cal_delta = actual_delta * best_cand["density"]["cal"]
                if abs(cal_delta) > 10:
                    needed_offset = -cal_delta
                    comps = [x for x in items if x["name"] != best_cand["name"]]
                    if comps:
                        # Score Compensators
                        s_comps = []
                        for c in comps:
                            s = 0
                            cd = c["density"]
                            for dev in current_deviations:
                                om_key = dev["metric"][:1] if dev["metric"] != "calories" else "cal"
                                imp = cd[om_key]
                                if needed_offset > 0: 
                                    if dev["diff"] < 0: s += imp * 10
                                    else: s -= imp * 20
                                else:
                                    if dev["diff"] > 0: s += imp * 10
                                    else: s -= imp * 20
                            s_comps.append((s, c))
                        
                        s_comps.sort(key=lambda x: x[0], reverse=True)
                        best_comp = s_comps[0][1]
                        if best_comp["density"]["cal"] > 0:
                            cw = best_comp["weight"] + (needed_offset / best_comp["density"]["cal"])
                            best_comp["weight"] = max(10, cw)

            # Rebuild String
            parts = [f"{int(x['weight'])}g {x['name']}" for x in items]
            meal["portion_size"] = " + ".join(parts)
            
    return adjusted_meals

def run():
    targets = {"calories": 2000, "protein": 150, "carbs": 200, "fat": 67}
    print("TARGETS:", targets)
    
    # CASE: High Fat, Low Protein
    meals = [
        {"meal_id": "1", "portion_size": "50g Chicken + 10g Oil + 50g Roti", "nutrients": {}},
        {"meal_id": "2", "portion_size": "50g Chicken + 10g Oil + 100g Rice", "nutrients": {}},
        {"meal_id": "3", "portion_size": "50g Paneer + 10g Oil + 50g Roti", "nutrients": {}},
        {"meal_id": "4", "portion_size": "50g Dal + 5g Oil + 50g Salad", "nutrients": {}}
    ]
    
    final_meals = adjust_portions_smart(meals, targets)
    
    # Report
    t = {"p": 0, "c": 0, "f": 0, "cal": 0}
    for m in final_meals:
         a = calculate_meal_macros_mock(m["portion_size"])
         for k in t: t[k] += a[f"total_{k}"]
         
    print("\nFINAL RESULT:")
    print(f"P: {t['p']:.1f} (Target 150)")
    print(f"C: {t['c']:.1f} (Target 200)")
    print(f"F: {t['f']:.1f} (Target 67)")
    print(f"Cal: {t['cal']:.0f} (Target 2000)")
    
    devs = []
    for m, tag in [('p',150),('c',200),('f',67),('cal',2000)]:
        diff = (t[m]-tag)/tag*100
        print(f"{m.upper()}: {diff:+.1f}%")

if __name__ == "__main__":
    run()
