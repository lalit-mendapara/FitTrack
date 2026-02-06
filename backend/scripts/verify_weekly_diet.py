import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.api.auth import get_current_user
from app.models.user import User

# Mock User
def mock_get_current_user():
    # Attempt to find a user in DB or just mock ID 1
    # We'll just return a mock object. The endpoint queries DB using this ID.
    # If ID 1 doesn't exist in DB, results will be empty but no crash.
    # Updated to ID 6 for Lalit
    return User(id=6, email="lalit@gmail.com") 

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

print("Testing GET /tracking/weekly-diet...")
response = client.get("/tracking/weekly-diet")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Response Type: {type(data)}")
    print(f"Item Count: {len(data)}")
    if len(data) > 0:
        print(f"First Item: {data[0]}")
        # Verify keys
        required_keys = ["day", "date", "calories", "target"]
        if all(k in data[0] for k in required_keys):
            print("SUCCESS: Response structure is correct.")
        else:
            print(f"FAILURE: Missing keys. Found {data[0].keys()}")
    else:
        print("WARNING: Response is empty list (User ID 1 might have no logs or target). but endpoint works.")
else:
    print(f"FAILURE: Request failed with {response.text}")
