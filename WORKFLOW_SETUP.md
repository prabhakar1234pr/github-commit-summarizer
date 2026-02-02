# Daily GitHub Commit to LinkedIn Workflow

This workflow automatically fetches your GitHub commits from the last 24 hours, analyzes them with AI, generates an image, and posts to LinkedIn every day at 10 AM PST.

## Overview

The workflow consists of:
1. **Fetch GitHub Commits** - Gets all commits from your repositories in the last 24 hours
2. **AI Analysis** - Uses Groq (Llama 3.3 70B) to analyze commits and create an engaging LinkedIn post
3. **Image Generation** - Uses Gemini Imagen to generate a professional image for the post
4. **Post to LinkedIn** - Uploads the image and posts to your LinkedIn profile

## Files

- **`fetch_github_commits.py`** - Fetches commits with detailed code changes and diffs
- **`daily_workflow.py`** - Main workflow orchestrator
- **`.github/workflows/daily-pipeline.yml`** - GitHub Actions workflow (runs daily at 10 AM PST)

## Setup

### 1. Environment Variables

Add these to your `.env` file:

```env
# GitHub API
GIT_TOKEN=your_github_personal_access_token
GIT_USERNAME=your_github_username

# Groq API (for post generation)
Groq_Api_Key=your_groq_api_key

# Gemini API (for image generation)
Gemini_Api_Key=your_gemini_api_key

# LinkedIn API (existing)
CLIENT_ID=your_linkedin_client_id
CLIENT_SECRET=your_linkedin_client_secret
access_token=your_linkedin_access_token
PERSON_URN=urn:li:person:your_person_id
```

### 2. GitHub Secrets (for GitHub Actions)

Go to your repository → Settings → Secrets and variables → Actions, and add:

- `GIT_TOKEN` - Your GitHub personal access token (with `public_repo` scope)
- `GIT_USERNAME` - Your GitHub username
- `GROQ_API_KEY` - Your Groq API key
- `GEMINI_API_KEY` - Your Gemini API key
- `LINKEDIN_CLIENT_ID` - Your LinkedIn Client ID
- `LINKEDIN_CLIENT_SECRET` - Your LinkedIn Client Secret
- `LINKEDIN_ACCESS_TOKEN` - Your LinkedIn access token
- `LINKEDIN_PERSON_URN` - Your LinkedIn Person URN

### 3. Install Dependencies

```bash
uv sync
```

This installs:
- `groq` - For AI post generation
- `google-generativeai` - For Gemini image generation
- `python-dotenv` - For environment variables
- `requests` - For API calls

## How It Works

### Step 1: Fetch Commits (`fetch_github_commits.py`)

- Fetches all repositories for your GitHub username
- Gets commits from the last 24 hours
- Includes:
  - Commit messages
  - Files changed
  - Code diffs (actual patch content)
  - Statistics (additions, deletions, changes)

### Step 2: Format for Analysis

- Formats commits into a clear, detailed summary
- Includes code changes and file modifications
- Structured for AI analysis

### Step 3: Generate LinkedIn Post (Groq)

- Uses **Groq Llama 3.3 70B** model (fastest, best quality)
- Analyzes commits and creates an engaging LinkedIn post
- Professional tone, highlights achievements
- 200-300 words with proper formatting

### Step 4: Generate Image (Gemini Imagen)

- Uses **Gemini Imagen 3.0** for image generation
- Creates professional, tech-focused image
- Square format (1:1) optimized for LinkedIn
- Based on the post content

### Step 5: Post to LinkedIn

- Uploads generated image to LinkedIn
- Creates post with text and image
- Posts to your LinkedIn profile

## Running Locally

Test the workflow locally:

```bash
uv run daily_workflow.py
```

## GitHub Actions Schedule

The workflow runs automatically every day at **10:00 AM PST (18:00 UTC)** via GitHub Actions.

You can also trigger it manually:
- Go to Actions tab in your repository
- Select "Daily Pipeline"
- Click "Run workflow"

## Customization

### Modify Post Style

Edit `daily_workflow.py` → `analyze_commits_with_groq()` function to change the prompt and post style.

### Change Image Style

Edit `daily_workflow.py` → `generate_image_with_gemini()` function to modify the image prompt.

### Adjust Schedule

Edit `.github/workflows/daily-pipeline.yml` → Change the cron schedule:
- Current: `0 18 * * *` (10 AM PST)
- Format: `minute hour day month weekday`

## Troubleshooting

### No Commits Found

If there are no commits in the last 24 hours, the workflow will skip posting.

### Image Generation Fails

If Gemini Imagen API fails, the workflow will continue and post text-only.

### LinkedIn Post Fails

Check:
- LinkedIn access token is valid
- PERSON_URN is correct
- Token has `w_member_social` scope

### GitHub API Rate Limits

GitHub API allows 5,000 requests/hour for authenticated users. The workflow should stay within limits.

## Rate Limits

- **GitHub API**: 5,000 requests/hour (authenticated)
- **Groq API**: Check your plan limits
- **Gemini API**: Check your plan limits
- **LinkedIn API**: 150 posts/day per member

## Notes

- The workflow only processes commits from the last 24 hours
- If no commits are found, no post is created
- Image generation is optional - posts will work without images
- All API keys should be kept secure and never committed to git
