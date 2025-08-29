import os
import time
import jwt
import requests
from azure.identity import ClientSecretCredential

# --- GitHub App Credentials ---
app_id = os.getenv("APP_ID")
private_key = os.getenv("PRIVATE_KEY", "").replace("\\n", "\n")

# --- Azure App Registration Credentials ---
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
tenant_id = os.getenv("AZURE_TENANT_ID")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
resource_group = os.getenv("LOGIC_APP_RG")
logic_app_name = os.getenv("LOGIC_APP_NAME")

# --- Validate Required Vars ---
required_vars = [app_id, private_key, client_id, client_secret, tenant_id,
                 subscription_id, resource_group, logic_app_name]
if not all(required_vars):
    raise EnvironmentError("❌ One or more required environment variables are missing.")

# --- Generate GitHub App JWT ---
payload = {
    "iat": int(time.time()) - 60,
    "exp": int(time.time()) + (10 * 60),
    "iss": app_id
}
jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

# --- Get GitHub App Installation ID ---
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Accept": "application/vnd.github+json"
}
resp = requests.get("https://api.github.com/app/installations", headers=headers)
resp.raise_for_status()
installation_id = resp.json()[0]["id"]

# --- Get GitHub App Access Token ---
resp = requests.post(f"https://api.github.com/app/installations/{installation_id}/access_tokens", headers=headers)
resp.raise_for_status()
access_token = resp.json()["token"]

print("✅ GitHub token generated.")

# --- Authenticate to Azure ---
try:
    credential = ClientSecretCredential(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id
    )
    token = credential.get_token("https://management.azure.com/.default").token
except Exception as e:
    raise RuntimeError(f"❌ Failed to get Azure token: {str(e)}")

# --- Update Logic App parameter ---
url = (
    f"https://management.azure.com/subscriptions/{subscription_id}"
    f"/resourceGroups/{resource_group}/providers/Microsoft.Logic/workflows/{logic_app_name}"
    f"?api-version=2016-06-01"
)

headers_azure = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Prepare PATCH payload
patch_body = {
    "properties": {
        "parameters": {
            "githubToken": {
                "value": access_token
            }
        }
    }
}

# Send PATCH request to update the parameter
print(f"🔄 Sending PATCH to update Logic App parameter...")
resp = requests.patch(url, headers=headers_azure, json=patch_body)
try:
    resp.raise_for_status()
    print("✅ Logic App parameter 'githubToken' updated successfully.")
except requests.exceptions.HTTPError:
    print(f"❌ Azure API Error {resp.status_code}: {resp.text}")
    raise
