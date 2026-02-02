import os
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.environ.get("access_token", "")
ID_TOKEN = os.environ.get("id_token", "")

if not ACCESS_TOKEN:
    print("ERROR: access_token not found in .env")
    exit(1)

def extract_from_id_token():
    """Try to extract person ID from id_token."""
    if not ID_TOKEN:
        return None
    try:
        # Decode JWT (id_token has 3 parts separated by dots)
        parts = ID_TOKEN.split('.')
        if len(parts) >= 2:
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            person_id = data.get("sub", "")
            if person_id:
                return f"urn:li:person:{person_id}"
    except Exception as e:
        print(f"Could not extract from id_token: {e}")
    return None

print("Attempting to get your LinkedIn Person URN...")
print("=" * 60)

# Try /v2/me first
resp = requests.get(
    "https://api.linkedin.com/v2/me",
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    },
)

if resp.status_code == 200:
    data = resp.json()
    person_id = data.get("id", "")
    if person_id:
        person_urn = f"urn:li:person:{person_id}" if not person_id.startswith("urn:li:person:") else person_id
        print(f"✓ Success! Your Person URN is: {person_urn}")
        print(f"\nAdd this line to your .env file:")
        print(f"PERSON_URN={person_urn}")
        exit(0)
    else:
        print("ERROR: Could not find 'id' in response")
        print("Response:", resp.json())
        exit(1)
elif resp.status_code == 403:
    print("✗ Your access token doesn't have permission to access /v2/me")
    # Try extracting from id_token as fallback
    person_urn = extract_from_id_token()
    if person_urn:
        print(f"\n✓ Success! Extracted Person URN from id_token: {person_urn}")
        print(f"\nAdd this line to your .env file:")
        print(f"PERSON_URN={person_urn}")
        exit(0)
    
    print("\nTo get your PERSON_URN, you need to:")
    print("1. Go to https://www.linkedin.com/developers/apps")
    print("2. Select your app")
    print("3. Go to the 'Products' tab")
    print("4. Add 'Sign In with LinkedIn using OpenID Connect' product")
    print("5. Update linkedin_oauth.py to include 'openid profile' in the scope")
    print("6. Re-run linkedin_oauth.py to get a new access token")
    print("7. Run this script again")
    print("\nAlternatively, you can manually find your LinkedIn Person ID:")
    print("- Visit your LinkedIn profile")
    print("- Check the URL or use browser developer tools")
    print("- Or use LinkedIn's API explorer if you have access")
    exit(1)
else:
    # Try extracting from id_token as fallback
    person_urn = extract_from_id_token()
    if person_urn:
        print(f"\n✓ Success! Extracted Person URN from id_token: {person_urn}")
        print(f"\nAdd this line to your .env file:")
        print(f"PERSON_URN={person_urn}")
        exit(0)
    
    print(f"ERROR: Got status code {resp.status_code}")
    print("Response:", resp.text)
    exit(1)
