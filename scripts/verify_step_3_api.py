import requests
import json

# Configuration
API_URL = "http://localhost:8000/chat"
LOGIN_URL = "http://localhost:8000/login"

def test_chat_api():
    print("\n--- Testing Chat API Endpoint ---")

    # 1. Login to get token (Assuming a test user exists, e.g., lalit@test.com / password)
    # We'll try to find a valid user or just fail gracefully if login fails
    # NOTE: Using an existing user from the database
    username = "lalit@gmail.com" 
    password = "password123" # Assumption: standard test password

    print(f"Logging in as {username}...")
    try:
        login_payload = {"email": username, "password": password}
        # Use JSON login endpoint
        response = requests.post("http://localhost:8000/login/json", json=login_payload)

        if response.status_code != 200:
            print(f"Login Failed: {response.status_code} {response.text}")
            print("Skipping API test due to auth failure. Please perform manual test.")
            return

        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("Login Successful.")

        # 2. Send Chat Message
        chat_payload = {
            "message": "What is a good post-workout meal?",
            "session_id": "api_test_session"
        }
        
        print(f"Sending Message: '{chat_payload['message']}'")
        chat_response = requests.post(API_URL, json=chat_payload, headers=headers)
        
        if chat_response.status_code == 200:
            data = chat_response.json()
            print("\n[SUCCESS] AI Response:")
            print(data.get("response"))
            print(f"Session ID: {data.get('session_id')}")
        else:
            print(f"\n[FAILURE] Status: {chat_response.status_code}")
            print(chat_response.text)

    except Exception as e:
        print(f"Error during API test: {e}")

if __name__ == "__main__":
    test_chat_api()
