# send_jwt.py

import os
import time
import jwt
import requests

# Get env variables
app_id = os.getenv("APP_ID")
private_key = os.getenv("PRIVATE_KEY").replace("\\n", "\n")  # decode newline characters
logic_app_url = os.getenv("LOGIC_APP_URL")

# Step 1: Create a JWT
payload = {
    "iat": int(time.time()) - 60,
    "exp": int(time.time()) + (10 * 60),  # 10 min token lifetime
    "iss": app_id
}
jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

# Step 2: Get installation ID
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Accept": "application/vnd.github+json"
}
installation_url = "https://api.github.com/app/installations"
installations = requests.get(installation_url, headers=headers)
installations.raise_for_status()

installation_data = installations.json()
if not installation_data:
    raise Exception("No GitHub App installations found.")

installation_id = installation_data[0]["id"]

# Step 3: Exchange JWT for an access token
access_token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
access_token_response = requests.post(access_token_url, headers=headers)
access_token_response.raise_for_status()

access_token = access_token_response.json()["token"]

# Step 4: Send the access token to your Logic App
response = requests.post(logic_app_url, json={"token": access_token})
response.raise_for_status()

print("✅ GitHub App token sent successfully to Logic App.")
