// Test the meal sorting logic
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
  const mealsWithPriority = meals.map(meal => {
    const mealType = meal.meal_id;
    const threshold = MEAL_TIME_THRESHOLDS[mealType] || 24;
    
    const isPast = currentHour > threshold;
    
    let priority;
    if (isPast) {
      priority = 100 + threshold;
    } else {
      priority = threshold;
    }
    
    return {
      ...meal,
      priority,
      isPast,
      threshold
    };
  });
  
  return mealsWithPriority.sort((a, b) => a.priority - b.priority);
};

// Test at 3:01 PM (15:01)
console.log('\n=== Testing at 3:01 PM (15:01) ===');
const currentHour = 15;
const sorted = sortMealsByTime(meals, currentHour);

sorted.forEach((meal, index) => {
  console.log(`${index + 1}. ${meal.dish_name.padEnd(10)} - Threshold: ${meal.threshold}:00, Priority: ${meal.priority}, isPast: ${meal.isPast}`);
});

console.log('\n=== Expected Order ===');
console.log('1. Snack (next at 5 PM)');
console.log('2. Dinner (next at 9 PM)');
console.log('3. Breakfast (past at 10 AM)');
console.log('4. Lunch (past at 1 PM)');
