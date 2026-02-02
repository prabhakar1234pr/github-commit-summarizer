# LinkedIn Post Automation Setup Guide

This guide explains how to set up and use the LinkedIn posting automation scripts.

## Overview

This project allows you to:
- Authenticate with LinkedIn OAuth 2.0
- Get your LinkedIn Person URN
- Post content to your LinkedIn profile programmatically

## Prerequisites

1. A LinkedIn Developer account
2. A LinkedIn app created at [LinkedIn Developers](https://www.linkedin.com/developers/apps)
3. Python 3.12+ installed
4. `uv` package manager (or `pip`)

## Files Overview

### Core Files

- **`linkedin_oauth.py`** - Handles OAuth 2.0 authentication and token retrieval
- **`linkedin_post.py`** - Posts content to your LinkedIn profile
- **`get_person_urn.py`** - Helper script to extract your LinkedIn Person URN
- **`.env`** - Stores your credentials and tokens (never commit this file!)

### Configuration Files

- **`pyproject.toml`** - Python project dependencies
- **`.gitignore`** - Ensures `.env` is not committed to git

## Step-by-Step Setup

### Step 1: Create a LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Click "Create app"
3. Fill in the required information
4. Note down your **Client ID** and **Client Secret**

### Step 2: Add Required Products

In your LinkedIn app settings, go to the **"Products"** tab and add:

1. **Share on LinkedIn** - Grants `w_member_social` permission (required for posting)
2. **Sign In with LinkedIn using OpenID Connect** - Grants `openid profile` permissions (required to get Person URN)

### Step 3: Set Up Environment Variables

Create a `.env` file in the project root with the following:

```env
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
access_token=your_access_token_here
id_token=your_id_token_here
PERSON_URN=urn:li:person:your_person_id
```

**Important:** Never commit the `.env` file to git. It contains sensitive credentials.

### Step 4: Install Dependencies

```bash
uv sync
```

Or with pip:
```bash
pip install python-dotenv requests
```

### Step 5: Get Your Access Token

Run the OAuth script to get your access token:

```bash
uv run linkedin_oauth.py
```

This will:
1. Open your browser to LinkedIn's authorization page
2. Ask you to authorize the app
3. Redirect you to a callback URL
4. Copy the **full redirect URL** and paste it into the terminal
5. Display your `access_token` and `id_token`

**Update your `.env` file** with the new `access_token` and `id_token`.

### Step 6: Get Your Person URN

Run the helper script to extract your Person URN:

```bash
uv run get_person_urn.py
```

This script will:
- Try to get your Person URN from `/v2/me` endpoint
- If that fails (403 error), extract it from the `id_token` in your `.env` file
- Display your `PERSON_URN` in the format: `urn:li:person:YOUR_ID`

**Add the `PERSON_URN` to your `.env` file.**

### Step 7: Post to LinkedIn

Now you can post to LinkedIn:

```bash
uv run linkedin_post.py
```

This will post the default message: "Hello from github-commit-summarizer! This is a sample post."

## Customizing Posts

### Post Custom Text

Edit `linkedin_post.py` and modify the `upload_sample_post()` function call:

```python
if __name__ == "__main__":
    result = upload_sample_post("Your custom post text here!")
    print("Post created:", result)
```

### Use in Your Own Code

```python
from linkedin_post import upload_sample_post

# Post custom text
result = upload_sample_post("Check out my latest project!")
print(f"Post created: {result}")
```

## How It Works

### Authentication Flow (`linkedin_oauth.py`)

1. Constructs OAuth authorization URL with scopes: `w_member_social openid profile`
2. Opens browser for user authorization
3. User authorizes and gets redirected with an authorization code
4. Exchanges authorization code for access token and id_token
5. Returns tokens for use in API calls

### Getting Person URN (`get_person_urn.py`)

1. First tries to call `/v2/me` endpoint (requires `r_liteprofile` permission)
2. If that fails (403), extracts Person ID from the `id_token` JWT
3. The `id_token` contains a `sub` field with your LinkedIn Person ID
4. Formats it as `urn:li:person:YOUR_ID`

### Posting (`linkedin_post.py`)

1. Loads credentials from `.env` file
2. Gets author URN (from `PERSON_URN` env var or `/v2/me` endpoint)
3. Constructs UGC Post payload with:
   - Author URN
   - Post text (commentary)
   - Visibility (PUBLIC)
   - Lifecycle state (PUBLISHED)
4. POSTs to `/v2/ugcPosts` endpoint
5. Returns the created post details

## API Endpoints Used

- **Authorization:** `https://www.linkedin.com/oauth/v2/authorization`
- **Token Exchange:** `https://www.linkedin.com/oauth/v2/accessToken`
- **Get Profile:** `https://api.linkedin.com/v2/me`
- **Create Post:** `https://api.linkedin.com/v2/ugcPosts`

## Required Permissions/Scopes

- `w_member_social` - Create posts on behalf of authenticated member
- `openid` - OpenID Connect authentication
- `profile` - Access to basic profile information (includes `r_liteprofile`)

## Troubleshooting

### 403 Forbidden on `/v2/me`

**Problem:** Your access token doesn't have `r_liteprofile` permission.

**Solution:** 
- Ensure you've added "Sign In with LinkedIn using OpenID Connect" product to your app
- Re-run `linkedin_oauth.py` to get a new token with `openid profile` scopes
- The `get_person_urn.py` script will extract from `id_token` as a fallback

### 401 Unauthorized / Revoked Token

**Problem:** Your access token has expired or been revoked.

**Solution:** Re-run `linkedin_oauth.py` to get a fresh token.

### Missing PERSON_URN

**Problem:** `linkedin_post.py` can't find your Person URN.

**Solution:** Run `get_person_urn.py` and add the `PERSON_URN` to your `.env` file.

## Security Notes

- **Never commit `.env` file** - It contains sensitive credentials
- **Keep tokens secure** - Access tokens can be used to post on your behalf
- **Rotate tokens regularly** - Tokens expire, but you should refresh them periodically
- **Use environment variables** - Never hardcode credentials in your code

## Rate Limits

LinkedIn API rate limits:
- **Member:** 150 requests per day
- **Application:** 100,000 requests per day

Be mindful of these limits when posting frequently.

## References

- [LinkedIn Share on LinkedIn Documentation](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- [LinkedIn OAuth 2.0 Guide](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [LinkedIn UGC Posts API](https://learn.microsoft.com/en-us/linkedin/compliance/integrations/shares/ugc-post-api)
