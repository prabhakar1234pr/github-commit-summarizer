import os
import requests
import webbrowser
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
REDIRECT_URI = "https://example.com/auth/linkedin/callback"

AUTH_URL = (
    "https://www.linkedin.com/oauth/v2/authorization"
    "?response_type=code"
    f"&client_id={CLIENT_ID}"
    f"&redirect_uri={REDIRECT_URI}"
    "&scope=w_member_social openid profile"
    "&state=123456"
)

print("Opening LinkedIn authorization page...")
webbrowser.open(AUTH_URL)

redirected_url = input(
    "\nAfter clicking ALLOW, paste the FULL redirect URL here:\n"
)

parsed = urlparse(redirected_url)
code = parse_qs(parsed.query).get("code", [None])[0]

if not code:
    raise Exception("No authorization code found in URL")

token_response = requests.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
)

print("\nResponse:")
print(token_response.json())
