import os
import time
import jwt
import requests
from azure.identity import ClientSecretCredential

# GitHub App credentials
app_id = os.getenv("APP_ID")
private_key = os.getenv("PRIVATE_KEY").replace("\\n", "\n")

# Azure credentials
client_id = os.getenv("AZURE_CLIENT_ID")
client_secret = os.getenv("AZURE_CLIENT_SECRET")
tenant_id = os.getenv("AZURE_TENANT_ID")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
resource_group = os.getenv("AZURE_RESOURCE_GROUP")
logic_app_name = os.getenv("AZURE_LOGIC_APP_NAME")

# Generate GitHub JWT
payload = {
    "iat": int(time.time()) - 60,
    "exp": int(time.time()) + (10 * 60),
    "iss": app_id
}
jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

# Get installation ID
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Accept": "application/vnd.github+json"
}
installations = requests.get("https://api.github.com/app/installations", headers=headers)
installations.raise_for_status()
installation_id = installations.json()[0]["id"]

# Get access token
access_token_resp = requests.post(
    f"https://api.github.com/app/installations/{installation_id}/access_tokens",
    headers=headers
)
access_token_resp.raise_for_status()
access_token = access_token_resp.json()["token"]

print("✅ GitHub token generated.")

# Authenticate to Azure
credential = ClientSecretCredential(
    client_id=client_id,
    client_secret=client_secret,
    tenant_id=tenant_id
)
access_token_azure = credential.get_token("https://management.azure.com/.default").token

# Update Logic App parameters via Azure REST API
url = (
    f"https://management.azure.com/subscriptions/{subscription_id}"
    f"/resourceGroups/{resource_group}/providers/Microsoft.Logic/workflows/{logic_app_name}"
    f"?api-version=2016-06-01"
)

headers_azure = {
    "Authorization": f"Bearer {access_token_azure}",
    "Content-Type": "application/json"
}

# Get current Logic App definition
logicapp_response = requests.get(url, headers=headers_azure)
logicapp_response.raise_for_status()
logicapp = logicapp_response.json()

# Update the parameter value
logicapp["properties"]["parameters"]["githubToken"]["value"] = access_token

# Send update request
update_response = requests.put(url, headers=headers_azure, json=logicapp)
update_response.raise_for_status()

print("✅ Logic App parameter 'githubToken' updated successfully.")
