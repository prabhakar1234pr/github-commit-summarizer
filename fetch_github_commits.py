import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GIT_TOKEN", "").strip()
GITHUB_USERNAME = os.environ.get("GIT_USERNAME", "").strip()

BASE_URL = "https://api.github.com"


def get_user_repos(username, token=None):
    """Get all repositories for a GitHub user."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    repos = []
    page = 1
    per_page = 100
    
    while True:
        url = f"{BASE_URL}/users/{username}/repos?page={page}&per_page={per_page}&sort=updated"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        page_repos = response.json()
        if not page_repos:
            break
        
        repos.extend(page_repos)
        page += 1
        
        # If we got fewer than per_page, we're done
        if len(page_repos) < per_page:
            break
    
    return repos


def get_repo_commits(owner, repo, since, token=None):
    """Get commits from a repository since a specific time."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    commits = []
    page = 1
    per_page = 100
    
    while True:
        url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
        params = {
            "since": since.isoformat(),
            "page": page,
            "per_page": per_page,
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 409:  # Empty repository
            break
        response.raise_for_status()
        
        page_commits = response.json()
        if not page_commits:
            break
        
        commits.extend(page_commits)
        page += 1
        
        if len(page_commits) < per_page:
            break
    
    return commits


def get_commit_details(owner, repo, sha, token=None):
    """Get detailed commit information including diff."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()


def summarize_diff(files):
    """Create a summary of changed files with code changes."""
    summary = []
    for file in files:
        status = file.get("status", "")
        filename = file.get("filename", "")
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)
        changes = file.get("changes", 0)
        patch = file.get("patch", "")  # Full diff content
        
        summary.append({
            "file": filename,
            "status": status,  # added, removed, modified, renamed
            "additions": additions,
            "deletions": deletions,
            "changes": changes,
            "patch": patch,  # Actual code diff
        })
    
    return summary


def format_commits_for_analysis(commits):
    """Format commits into a clear, detailed summary for AI analysis."""
    if not commits:
        return "No commits found in the last 24 hours."
    
    summary_parts = []
    summary_parts.append(f"📊 GitHub Activity Summary - Last 24 Hours")
    summary_parts.append(f"Total Commits: {len(commits)}\n")
    
    for i, commit in enumerate(commits, 1):
        summary_parts.append(f"{'='*80}")
        summary_parts.append(f"Commit #{i}: {commit['repository']}")
        summary_parts.append(f"{'='*80}")
        summary_parts.append(f"🔗 URL: {commit['url']}")
        summary_parts.append(f"👤 Author: {commit['author']}")
        summary_parts.append(f"📅 Date: {commit['date']}")
        summary_parts.append(f"💬 Message: {commit['message']}")
        
        stats = commit.get('stats', {})
        summary_parts.append(f"\n📈 Statistics:")
        summary_parts.append(f"  • Files Changed: {len(commit['files'])}")
        summary_parts.append(f"  • Total Additions: +{stats.get('additions', 0)}")
        summary_parts.append(f"  • Total Deletions: -{stats.get('deletions', 0)}")
        summary_parts.append(f"  • Total Changes: {stats.get('total', 0)} lines")
        
        summary_parts.append(f"\n📁 Files Changed:")
        for file_info in commit['files']:
            status_emoji = {
                "added": "➕",
                "removed": "➖",
                "modified": "✏️",
                "renamed": "📝",
            }.get(file_info['status'], "📄")
            
            summary_parts.append(f"\n  {status_emoji} {file_info['file']} ({file_info['status'].upper()})")
            summary_parts.append(f"     +{file_info['additions']} -{file_info['deletions']} lines")
            
            # Include code diff if available (truncate if too long)
            if file_info.get('patch'):
                patch = file_info['patch']
                # Limit patch to first 500 lines to avoid token limits
                patch_lines = patch.split('\n')
                if len(patch_lines) > 500:
                    patch = '\n'.join(patch_lines[:500]) + f"\n... (truncated, {len(patch_lines) - 500} more lines)"
                summary_parts.append(f"\n     Code Changes:")
                summary_parts.append(f"     {patch[:2000]}")  # Limit to 2000 chars per file
                if len(patch) > 2000:
                    summary_parts.append(f"     ... (truncated)")
        
        summary_parts.append("\n")
    
    return "\n".join(summary_parts)


def fetch_commits_from_last_24_hours(username=None, token=None):
    """Fetch all commits from user's repositories in the last 24 hours."""
    if not username:
        username = GITHUB_USERNAME
    
    if not username:
        # Debug: Check what's actually in the environment
        env_vars = {k: v for k, v in os.environ.items() if 'GIT' in k or 'GITHUB' in k}
        raise ValueError(
            f"GitHub username required. Set GIT_USERNAME in .env or pass as argument.\n"
            f"Current env vars: {env_vars}\n"
            f"GIT_USERNAME value: '{GITHUB_USERNAME}'"
        )
    
    if not token:
        token = GITHUB_TOKEN
    
    if not token:
        raise ValueError("GitHub token required. Set GIT_TOKEN in .env or pass as argument.")
    
    # Calculate 24 hours ago
    since = datetime.utcnow() - timedelta(hours=24)
    
    print(f"Fetching commits from {username}'s repositories since {since.isoformat()}")
    print("=" * 80)
    
    # Get all repositories
    print(f"Fetching repositories for {username}...")
    repos = get_user_repos(username, token)
    print(f"Found {len(repos)} repositories\n")
    
    all_commits = []
    
    # Get commits from each repository
    for repo in repos:
        repo_name = repo["full_name"]
        owner = repo["owner"]["login"]
        repo_name_only = repo["name"]
        
        try:
            commits = get_repo_commits(owner, repo_name_only, since, token)
            if commits:
                print(f"Found {len(commits)} commit(s) in {repo_name}")
                all_commits.extend([(repo_name, commit) for commit in commits])
        except Exception as e:
            print(f"Error fetching commits from {repo_name}: {e}")
            continue
    
    print(f"\nTotal commits found: {len(all_commits)}\n")
    
    # Get detailed information for each commit
    results = []
    for repo_name, commit in all_commits:
        owner, repo = repo_name.split("/")
        sha = commit["sha"]
        
        try:
            details = get_commit_details(owner, repo, sha, token)
            
            commit_info = {
                "repository": repo_name,
                "sha": sha[:7],
                "message": commit["commit"]["message"],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"],
                "files": summarize_diff(details.get("files", [])),
                "stats": details.get("stats", {}),  # Total additions, deletions, changes
            }
            
            results.append(commit_info)
        except Exception as e:
            print(f"Error fetching details for {repo_name}/{sha[:7]}: {e}")
            continue
    
    return results


def print_commit_summary(commits):
    """Print a formatted summary of commits."""
    if not commits:
        print("No commits found in the last 24 hours.")
        return
    
    for i, commit in enumerate(commits, 1):
        print(f"\n{'='*80}")
        print(f"Commit #{i}")
        print(f"{'='*80}")
        print(f"Repository: {commit['repository']}")
        print(f"SHA: {commit['sha']}")
        print(f"Author: {commit['author']}")
        print(f"Date: {commit['date']}")
        print(f"URL: {commit['url']}")
        print(f"\nMessage:")
        print(f"  {commit['message']}")
        print(f"\nFiles Changed ({len(commit['files'])}):")
        
        for file_info in commit['files']:
            status_emoji = {
                "added": "➕",
                "removed": "➖",
                "modified": "✏️",
                "renamed": "📝",
            }.get(file_info['status'], "📄")
            
            print(f"  {status_emoji} {file_info['status'].upper():8} | "
                  f"+{file_info['additions']:3} -{file_info['deletions']:3} | "
                  f"{file_info['file']}")


if __name__ == "__main__":
    try:
        commits = fetch_commits_from_last_24_hours()
        print_commit_summary(commits)
        
        # Return commits as structured data for further processing
        print(f"\n\n{'='*80}")
        print(f"Summary: Found {len(commits)} commit(s) in the last 24 hours")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
