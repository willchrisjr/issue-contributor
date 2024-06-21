import os
from github import Github
from tqdm import tqdm
import re
from datetime import datetime, timezone

def analyze_repo(repo):
    """Analyze the repository for contribution-related information."""
    analysis = {
        "name": repo.name,
        "description": repo.description,
        "language": repo.language,
        "contributors": [c.login for c in repo.get_contributors()[:5]],
        "setup_instructions": get_setup_instructions(repo),
    }
    return analysis

def get_setup_instructions(repo):
    """Try to find setup instructions in README or CONTRIBUTING files."""
    files_to_check = ["README.md", "CONTRIBUTING.md", "SETUP.md"]
    for file_name in files_to_check:
        try:
            content = repo.get_contents(file_name).decoded_content.decode('utf-8')
            # Here you could use more sophisticated parsing to find setup instructions
            if "setup" in content.lower() or "getting started" in content.lower():
                return f"Setup instructions found in {file_name}. Please check the file for details."
        except:
            pass
    return "No clear setup instructions found. You may need to ask the maintainers for guidance."

def get_open_issues(repo, labels=None, keywords=None, limit=10):
    """
    Fetch open issues, filtered by labels and keywords, and scored for approachability.
    """
    issues = repo.get_issues(state='open', labels=labels)
    filtered_issues = []
    
    for issue in issues:
        if len(filtered_issues) >= limit:
            break
        
        # Filter by keywords if provided
        if keywords and not any(keyword.lower() in issue.title.lower() or keyword.lower() in (issue.body or '').lower() for keyword in keywords):
            continue
        
        # Score the issue for approachability
        score = score_issue(issue)
        
        filtered_issues.append((issue, score))
    
    # Sort issues by score (higher is more approachable)
    return sorted(filtered_issues, key=lambda x: x[1], reverse=True)

def score_issue(issue):
    """
    Score an issue based on various factors to determine approachability.
    Higher score means more approachable.
    """
    score = 0
    
    # Prefer issues with 'good first issue' or 'help wanted' labels
    if any(label.name.lower() in ['good first issue', 'help wanted'] for label in issue.labels):
        score += 5
    
    # Prefer issues with clearer descriptions (longer, but not too long)
    description_length = len(issue.body or '')  # Use empty string if body is None
    if 100 <= description_length <= 500:
        score += 3
    elif 50 <= description_length < 100:
        score += 2
    
    # Prefer issues with fewer comments (might be less complex or controversial)
    comment_count = issue.comments
    if comment_count == 0:
        score += 2
    elif comment_count < 5:
        score += 1
    
    # Prefer more recent issues
    days_old = (datetime.now(timezone.utc) - issue.created_at.replace(tzinfo=timezone.utc)).days
    if days_old < 30:
        score += 2
    elif days_old < 90:
        score += 1
    
    return score

def analyze_issue(repo, issue):
    """Analyze a single issue, including its context in the codebase."""
    analysis = {
        "title": issue.title or '',
        "body": issue.body or '',
        "labels": [l.name for l in issue.labels],
        "comments": [comment.body or '' for comment in issue.get_comments()],
        "mentioned_files": find_mentioned_files(issue.body or ''),
    }
    return analysis

def find_mentioned_files(text):
    """Find files mentioned in the issue text. This is a simple implementation and could be improved."""
    if not text:
        return []
    words = text.split()
    return [word for word in words if '.' in word and '/' in word]

def suggest_contribution(repo, issue):
    """Provide suggestions on how to approach solving the issue."""
    suggestion = f"To contribute to issue #{issue.number}:\n"
    suggestion += f"1. Read through the issue description and comments carefully.\n"
    if issue.labels:
        suggestion += f"2. Note that this issue is labeled as: {', '.join([l.name for l in issue.labels])}\n"
    if find_mentioned_files(issue.body or ''):
        suggestion += f"3. The issue mentions these files, which you should examine: {', '.join(find_mentioned_files(issue.body or ''))}\n"
    suggestion += f"4. Set up the project locally using the provided setup instructions.\n"
    suggestion += f"5. Create a new branch for your work.\n"
    suggestion += f"6. Make your changes, commit them, and push to your fork.\n"
    suggestion += f"7. Open a pull request referencing this issue.\n"
    return suggestion

def main():
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo_url = input("Please enter the GitHub repository URL: ")
    repo = g.get_repo(repo_url.split('github.com/')[-1])

    print("Analyzing repository...")
    repo_analysis = analyze_repo(repo)

    # Get user preferences for filtering
    labels = input("Enter labels to filter by (comma-separated, or press enter to skip): ").split(',')
    labels = [label.strip() for label in labels if label.strip()]
    
    keywords = input("Enter keywords to filter by (comma-separated, or press enter to skip): ").split(',')
    keywords = [keyword.strip() for keyword in keywords if keyword.strip()]

    print("Fetching and analyzing open issues...")
    issues = get_open_issues(repo, labels=labels, keywords=keywords)

    with open("contribution_guide.md", "w") as f:
        f.write(f"# Contribution Guide for {repo.name}\n\n")
        f.write(f"## Repository Analysis\n")
        f.write(f"- Name: {repo_analysis['name']}\n")
        f.write(f"- Description: {repo_analysis['description']}\n")
        f.write(f"- Primary Language: {repo_analysis['language']}\n")
        f.write(f"- Top Contributors: {', '.join(repo_analysis['contributors'])}\n")
        f.write(f"- Setup Instructions: {repo_analysis['setup_instructions']}\n\n")
        
        f.write(f"## Open Issues (Sorted by Approachability)\n")
        for issue, score in issues:
            issue_analysis = analyze_issue(repo, issue)
            contribution_suggestion = suggest_contribution(repo, issue)
            f.write(f"### Issue #{issue.number}: {issue.title} (Score: {score})\n")
            f.write(f"Labels: {', '.join([label.name for label in issue.labels])}\n")
            f.write(f"Description: {(issue.body or '')[:100]}...\n")
            f.write(f"Contribution Suggestion:\n{contribution_suggestion}\n\n")

    print("Analysis complete. Results written to contribution_guide.md")

if __name__ == "__main__":
    main()