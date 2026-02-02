import os
import requests

from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.environ.get("access_token", "")
PERSON_URN = os.environ.get("PERSON_URN", "").strip()
BASE_URL = "https://api.linkedin.com/v2"


def _get_author_urn():
    """Get author URN: from /v2/me if allowed, else from PERSON_URN in .env."""
    if PERSON_URN:
        return PERSON_URN if PERSON_URN.startswith("urn:li:person:") else f"urn:li:person:{PERSON_URN}"
    resp = requests.get(
        f"{BASE_URL}/me",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
    )
    if resp.status_code == 403:
        raise ValueError(
            "GET /v2/me returned 403 (your token has w_member_social but not r_liteprofile). "
            "Add PERSON_URN to .env. To get it: in LinkedIn Developer Portal add 'Sign In with LinkedIn using OpenID Connect' to your app, "
            "get a new access token (re-run linkedin_oauth.py with openid profile in scope), then run: "
            "curl -H \"Authorization: Bearer YOUR_ACCESS_TOKEN\" https://api.linkedin.com/v2/me . "
            "Use the 'id' from the response: PERSON_URN=urn:li:person:<id>"
        )
    resp.raise_for_status()
    me = resp.json()
    raw_id = me.get("id", "")
    return raw_id if raw_id.startswith("urn:li:person:") else f"urn:li:person:{raw_id}"


def upload_sample_post(text: str = "Hello from github-commit-summarizer! This is a sample post."):
    """Post a sample text post to your LinkedIn using env access_token."""
    if not ACCESS_TOKEN:
        raise ValueError("access_token not set in .env")

    author_urn = _get_author_urn()

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(
        f"{BASE_URL}/ugcPosts",
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    result = upload_sample_post()
    print("Post created:", result)
