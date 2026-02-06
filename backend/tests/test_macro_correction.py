import unittest
from unittest.mock import MagicMock
from app.utils.nutrition_calc import parse_portion_grams, calculate_macros_from_db, enforce_consistency

class TestNutritionCalc(unittest.TestCase):
    
    def test_parse_portion_grams(self):
        self.assertEqual(parse_portion_grams("100g"), 100.0)
        self.assertEqual(parse_portion_grams("100 g"), 100.0)
        self.assertEqual(parse_portion_grams("200grams"), 200.0)
        self.assertEqual(parse_portion_grams("2 pcs (150g)"), 150.0)
        self.assertEqual(parse_portion_grams("Serving: 50g"), 50.0)
        self.assertIsNone(parse_portion_grams("1 cup"))
        self.assertIsNone(parse_portion_grams("2 slices"))

    def test_enforce_consistency(self):
        # P=10, C=10, F=10 -> 40+40+90 = 170
        
        # Case 1: Accurate
        n1 = {"p": 10, "c": 10, "f": 10, "calories": 170}
        self.assertEqual(enforce_consistency(n1)['calories'], 170)
        
        # Case 2: Inaccurate (Low)
        n2 = {"p": 10, "c": 10, "f": 10, "calories": 100} 
        self.assertEqual(enforce_consistency(n2)['calories'], 170)
        
        # Case 3: Inaccurate (High)
        n3 = {"p": 10, "c": 10, "f": 10, "calories": 1000}
        self.assertEqual(enforce_consistency(n3)['calories'], 170)

    def test_calculate_macros_from_db(self):
        # Mock DB Item
        mock_item = MagicMock()
        mock_item.name = "Oatmeal"
        mock_item.protein_g = 10
        mock_item.carb_g = 60
        mock_item.fat_g = 5
        mock_item.calories_kcal = 300 # Per 100g
        
        # Mock DB Session
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item
        
        # Test 50g portion (Should be half)
        result = calculate_macros_from_db("Oatmeal", "50g", mock_db)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['p'], 5.0)
        self.assertEqual(result['c'], 30.0)
        self.assertEqual(result['f'], 2.5)
        self.assertEqual(result['calories'], 150.0)

if __name__ == '__main__':
    unittest.main()
