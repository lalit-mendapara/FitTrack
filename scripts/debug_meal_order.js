// Debug the exact meal ordering at current time
const MEAL_TIME_THRESHOLDS = {
  breakfast: 10, // 10 AM
  lunch: 13,     // 1 PM
  snack: 17,     // 5 PM
  dinner: 21     // 9 PM
};

const meals = [
  { meal_id: 'breakfast', dish_name: 'Breakfast' },
  { meal_id: 'lunch', dish_name: 'Lunch' },
  { meal_id: 'snack', dish_name: 'Snacks' },
  { meal_id: 'dinner', dish_name: 'Dinner' }
];

const sortMealsByTime = (meals, currentHour) => {
  console.log(`\nCurrent Hour: ${currentHour}:00`);
  console.log('='.repeat(60));
  
  const mealsWithPriority = meals.map(meal => {
    const mealType = meal.meal_id;
    const threshold = MEAL_TIME_THRESHOLDS[mealType] || 24;
    
    // OLD LOGIC (WRONG): const isPast = currentHour >= threshold;
    const isPast = currentHour > threshold;
    
    let priority;
    if (isPast) {
      priority = 100 + threshold;
    } else {
      priority = threshold;
    }
    
    console.log(`${meal.dish_name.padEnd(10)} | Threshold: ${threshold}:00 | currentHour > ${threshold} = ${isPast} | Priority: ${priority}`);
    
    return {
      ...meal,
      priority,
      isPast,
      threshold
    };
  });
  
  const sorted = mealsWithPriority.sort((a, b) => a.priority - b.priority);
  
  console.log('\n' + '='.repeat(60));
  console.log('SORTED ORDER:');
  sorted.forEach((meal, index) => {
    console.log(`${index + 1}. ${meal.dish_name} (Priority: ${meal.priority})`);
  });
  
  return sorted;
};

// Test at different times
console.log('\n### TEST 1: At 3:04 PM (15:04) - Current Time ###');
sortMealsByTime(meals, 15);

console.log('\n\n### TEST 2: At 5:00 PM (17:00) - Snack Time ###');
sortMealsByTime(meals, 17);

console.log('\n\n### TEST 3: At 5:01 PM (17:01) - After Snack Time ###');
sortMealsByTime(meals, 17.01);

console.log('\n\n### ANALYSIS ###');
console.log('At 3:04 PM (15:04):');
console.log('  - Breakfast (10 AM): 15 > 10 = TRUE (past) → Priority 110');
console.log('  - Lunch (1 PM):      15 > 13 = TRUE (past) → Priority 113');
console.log('  - Snack (5 PM):      15 > 17 = FALSE (upcoming) → Priority 17');
console.log('  - Dinner (9 PM):     15 > 21 = FALSE (upcoming) → Priority 21');
console.log('\nExpected Order: Snack (17) → Dinner (21) → Breakfast (110) → Lunch (113)');
