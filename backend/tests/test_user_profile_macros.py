import unittest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.user_profile import UserProfile, refresh_nutrition_plan

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

# Use an in-memory SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Fix JSONB for SQLite
@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestUserProfileMacros(unittest.TestCase):
    def setUp(self):
        # Create tables
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        
        # Manually register the event listener if it's not picked up automatically by the import
        # (Though typically importing the model is enough)
        
    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_weight_loss_macros(self):
        # Create profile: 85kg -> 65kg (Weight Loss)
        profile = UserProfile(
            user_id=1,
            weight=85.0,
            height=175.0,
            weight_goal=65.0,
            fitness_goal="weight_loss",  # Explicitly chosen
            activity_level="moderate",
            diet_type="non_veg"
        )
        self.db.add(profile)
        self.db.commit()
        
        # Verify Calories (BMR ~1860, TDEE ~2880, Deficit -750 -> ~2130)
        # BMR = 10*85 + 6.25*175 - 5*25 + 5 = 850 + 1093.75 - 125 + 5 = 1823.75
        # TDEE = 1823.75 * 1.55 = 2826.8
        # Target = 2826 - 750 = 2076
        
        print(f"Calculated Calories: {profile.calories}")
        self.assertTrue(1900 < profile.calories < 2200) 
        self.assertEqual(profile.fitness_goal, "weight_loss")

    def test_muscle_gain_logic_conflict(self):
        # Create profile: 85kg -> 65kg (Weight Loss needed) BUT user chose "muscle_gain"
        # Current behavior: It respects "muscle_gain" (Surplus)
        # Desired behavior (implied): Backend *could* force it, or just frontend hides it.
        # This test documents CURRENT behavior before we decide if backend should enforce it.
        
        profile = UserProfile(
            user_id=2,
            weight=85.0,
            height=175.0,
            weight_goal=65.0, # Wants to lose 20kg
            fitness_goal="muscle_gain", # But chose muscle gain
            activity_level="moderate"
        )
        self.db.add(profile)
        self.db.commit()
        
        # BMR ~1823. TDEE ~2826. 
        # Muscle Gain = +300 -> ~3126
        
        print(f"Conflicted Profile Calories: {profile.calories}")
        
        # Now it should be forced to "Fat Loss"
        self.assertEqual(profile.fitness_goal, "fat_loss")
        
        # And calories should be in deficit range (Maintenance - 500)
        # TDEE ~2826. Target ~2326.
        # Should be definitely less than maintenance (2826)
        self.assertLess(profile.calories, 2826)
        self.assertTrue(2200 < profile.calories < 2400)

    def test_auto_recalculation_on_update(self):
        profile = UserProfile(
            user_id=3,
            weight=70.0,
            height=170.0,
            weight_goal=70.0,
            fitness_goal="maintenance",
            activity_level="sedentary"
        )
        self.db.add(profile)
        self.db.commit()
        initial_cals = profile.calories
        
        # Update weight to increase BMR
        profile.weight = 90.0
        self.db.commit() # Should trigger before_update
        
        self.assertGreater(profile.calories, initial_cals)

if __name__ == '__main__':
    unittest.main()
