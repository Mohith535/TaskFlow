import json
import requests
import time

def test_mission_deployment():
    url = "http://127.0.0.1:18083/api/tasks"
    payload = {
        "title": "Quantum Connection Verification",
        "priority": "high",  # This was causing issues (lowercase)
        "tags": ["verification", "fix"]
    }
    
    print(f"Testing Mission Deployment at {url}...")
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            print("✅ Success! Task created with 201 Created.")
            print("Response:", response.json())
            return True
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print("Error:", response.text)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error! Is the server running on port 18083?")
        print("   Try running 'python task_manager/server.py' in a separate terminal.")
        return False

if __name__ == "__main__":
    test_mission_deployment()
