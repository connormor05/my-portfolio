import requests
from auth_client import BASE_URL 

email = "test@example.com"
password = "123456"

print(f"Testing API connection to {BASE_URL}...\n")

try:
    # 1. Try to create the user
    print("1. Creating user...")
    signup = requests.post(f"{BASE_URL}/signup", json={
        "email": email,
        "password": password
    })
    
    signup_data = signup.json()
    if signup_data.get("error") == "User already exists":
        print(" -> User already exists (Skipping creation)")
    else:
        print(" -> Signup response:", signup_data)

    # 2. Log in
    print("\n2. Logging in...")
    login = requests.post(f"{BASE_URL}/login", json={
        "email": email,
        "password": password
    })

    data = login.json()
    print(" -> Login response:", data)

    # 3. Save token
    if "token" in data:
        token = data["token"]
        print("\n✅ LOGIN SUCCESS. Token acquired.")
    else:
        print("\n❌ Login failed — check email/password.")
        exit()

    # 4. Call a protected route using the token
    print("\n3. Calling protected route (/me)...")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    protected = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if protected.status_code == 200:
        print(" -> Protected route response:", protected.json())
        print("\n🎉 ALL TESTS PASSED! Your Auth system is working perfectly.")
    else:
        print(f" -> Protected route failed with status {protected.status_code}:", protected.text)

except requests.exceptions.ConnectionError:
    print("\n❌ CONNECTION ERROR: Could not connect to the backend.")
    print("Make sure your Node server (server.js) is currently running!")
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")