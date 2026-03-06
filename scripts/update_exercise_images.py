#!/usr/bin/env python3
"""
Script to scrape new image URLs from burnfit.mycafe24.com and update the exercises table.
The old burnfit.io domain is down (HTTP 500), images moved to burnfit.mycafe24.com.
"""
import re
import subprocess
import urllib.request
import time
import json

BASE = "https://burnfit.mycafe24.com/en/library/"

# Manual mapping: DB exercise name -> library page slug
# Built from the library index at burnfit.mycafe24.com/en/library/
NAME_TO_SLUG = {
    "Deficit Deadlift": "deficit-deadlift",
    "Pull-Up": "pull-up",
    "Lat Pulldown": "lat-pull-down",
    "Single Arm DB Row": "one-arm-dumbbell-row",
    "T-Bar Row": "T-bar-Row-Machine",
    "Inverted Row": "inverted-row",
    "Renegade Row": "dumbbell-row",            # closest match
    "Hyperextensions": "hyperextension",
    "Barbell Row": "incline-barbell-row",
    "Seated Cable Row": "seated-cable-row",
    "Barbell Bicep Curl": "reverse-barbell-curl",   # closest barbell curl
    "Dumbbell Hammer Curl": "dumbbell-hammer-curl",
    "Cable Curl": "cable-curl",
    "Dumbbell Preacher Curl": "dumbbell-preacher-curl",
    "Dumbbell Bicep Curl": "dumbbell-bicep-curl",
    "EZ Bar Preacher Curl": "ez-bar-preacher-curl",
    "Incline DB Curl": "incline-dumbbell-curl",
    "Arm Curl Machine": "arm-curl-machine",
    "Preacher Curl Machine": "preacher-curl-machine",
    "Cable Hammer Curl": "cable-hammer-curl",
    "Barbell Bench Press": "barbell-bench-press",
    "Push-Up": "push-up",
    "Incline Dumbbell Bench Press": "incline-dumbbell-bench-press",
    "Pec Deck Fly Machine": "pec-deck-fly-machine",
    "Dips (Chest focus)": "dips",
    "Floor Press": "barbell-floor-chest-press",
    "Cable Crossover": "standing-cable-fly",
    "Close-grip Push Up": "close-grip-push-up",
    "Barbell Decline Bench Press": "barbell-bench-press",  # no exact decline
    "Hindu Push Up": "hindu-push-up",
    "Skull Crushers": "skull-crusher",
    "Cable Push Down": "cable-push-down",
    "Cable Overhead Tricep Extension": "cable-overhead-tricep-extension",
    "Bench Dips": "bench-dips",
    "Close-grip Bench Press": "close-grip-bench-press",
    "Dumbbell Kickback": "dumbbell-kickback",
    "Cable Tricep Extension": "cable-tricep-extension",
    "Seated Dumbbell Tricep Extension": "seated-dumbbell-tricep-extension",
    "Clap Push Up": "clap-push-up",
    "Plank": "plank",
    "Hanging Leg Raise": "hanging-leg-raise",
    "Russian Twist": "cable-twist",             # closest
    "Air Bicycle Abs": "air-bicycle-abs",
    "Abs Roll Out": "abs-roll-out",
    "V-up": "v-up",
    "Cable Crunch": "abdominal-crunch-machine",  # closest
    "Side Plank": "side-plank",
    "Hanging Knee Raise": "hanging-knee-raise",
    "Abdominal Hip Thrust": "abdominal-hip-thrust",
    "Overhead Press": "overhead-press",
    "Dumbbell Lateral Raise": "dumbbell-lateral-raise",
    "Arnold Dumbbell Press": "arnold-dumbbell-press",
    "Face Pull": "face-pull",
    "Pike Push Up": "pike-push-up",
    "Dumbbell Front Raise": "dumbbell-front-raise",
    "Handstand Push-Up": "handstand-push-up",
    "Dumbbell Upright Row": "dumbbell-upright-row",
    "Reverse Pec Deck Fly Machine": "reverse-pec-deck-fly-machine",
    "Push Press": "push-press",
    "Back Squat": "back-squat",
    "Lunges": "lunge",
    "Barbell Bulgarian Split Squat": "barbell-bulgarian-split-squat",
    "Leg Press": "leg-press",
    "Leg Curl": "leg-curl",
    "Glute Bridge": "glute-bridge",
    "Goblet Squat": "dumbbell-goblet-squat",
    "Box Jump": "box-jump",
    "Pistol Squat": "pistol-squat",
    "Calf Raise": "standing-calf-raise",
    "Wrist Curl": "barbell-wrist-curl",
    "Reverse Wrist Curl": "reverse-barbell-wrist-curl",
    "Reverse Barbell Curl": "reverse-barbell-curl",
    "Reverse Dumbbell Wrist Curl": "reverse-dumbbell-wrist-curl",
    "Wrist Roller": "wrist-roller",
    "EZ Bar Wrist Curlf": "ez-bar-wrist-curl",
    "Burpees": "burpee",
    "Mountain Climbers": "mountain-climber",
    "Jumping Jacks": "jumping-jack",
    "Treadmill Sprints": "treadmill",
    "Battling Ropes": "jumping-rope",            # no exact match
    "Jumping Rope": "jumping-rope",
    "Inchworm": "inchworm",
    "High-knee Skip": "high-knee-skip",
    "Kettlebell Swing": "kettlebell-swing",
    "Assault Bike": "assault-bike",
    "Climbing Stairs": "climbing-stairs",
    "Running": "running",
    "Stepmill Machine": "stepmill-machine",
    "Rowing machine": "rowing-machine",
    "Elliptical Machine": "elliptical-machine",
}


def fetch_gif_url(slug):
    """Fetch the GIF URL from an exercise library page."""
    url = BASE + slug + "/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # Find all gif URLs on the page
        gifs = re.findall(r'https?://[^\s"\'<>]+\.gif', html)
        if gifs:
            return gifs[0]
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
    return None


def main():
    results = {}
    failed = []
    total = len(NAME_TO_SLUG)

    print(f"Scraping {total} exercise pages from burnfit.mycafe24.com ...\n")

    for i, (name, slug) in enumerate(NAME_TO_SLUG.items(), 1):
        print(f"[{i}/{total}] {name} -> {slug} ... ", end="", flush=True)
        gif = fetch_gif_url(slug)
        if gif:
            results[name] = gif
            print(f"OK  {gif}")
        else:
            failed.append(name)
            print("FAILED")
        time.sleep(0.3)  # be polite

    print(f"\n--- Results ---")
    print(f"Success: {len(results)}/{total}")
    print(f"Failed:  {len(failed)}")
    if failed:
        print(f"Failed exercises: {failed}")

    # Generate SQL file
    sql_lines = []
    for name, gif_url in results.items():
        escaped_name = name.replace("'", "''")
        escaped_url = gif_url.replace("'", "''")
        sql_lines.append(
            f"UPDATE exercises SET \"Image URL\" = '{escaped_url}' WHERE \"Exercise Name\" = '{escaped_name}';"
        )

    sql_path = "/tmp/update_exercise_images.sql"
    with open(sql_path, "w") as f:
        f.write("\n".join(sql_lines) + "\n")

    print(f"\nSQL written to {sql_path}")
    print(f"Run: docker compose exec -T postgres psql -U lalit -d fitness_track < {sql_path}")

    # Also dump a JSON mapping for reference
    json_path = "/tmp/exercise_image_mapping.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"JSON mapping: {json_path}")


if __name__ == "__main__":
    main()
