# issue_analyzer.py
from datetime import datetime, timedelta

def get_open_issues(repo, labels=None, keywords=None, limit=10):
    issues = repo.get_issues(state='open', labels=labels)
    filtered_issues = []
    
    for issue in issues:
        if len(filtered_issues) >= limit:
            break
        
        if keywords and not any(keyword.lower() in issue.title.lower() or keyword.lower() in (issue.body or '').lower() for keyword in keywords):
            continue
        
        score = score_issue(issue)
        filtered_issues.append((issue, score))
    
    return sorted(filtered_issues, key=lambda x: x[1], reverse=True)

def score_issue(issue):
    score = 0
    
    if any(label.name.lower() in ['good first issue', 'help wanted'] for label in issue.labels):
        score += 5
    
    description_length = len(issue.body or '')
    if 100 <= description_length <= 500:
        score += 3
    elif 50 <= description_length < 100:
        score += 2
    
    comment_count = issue.comments
    if comment_count == 0:
        score += 2
    elif comment_count < 5:
        score += 1
    
    days_old = (datetime.now(issue.created_at.tzinfo) - issue.created_at).days
    if days_old < 30:
        score += 2
    elif days_old < 90:
        score += 1
    
    return score

def analyze_issue(repo, issue):
    return {
        "title": issue.title or '',
        "body": issue.body or '',
        "labels": [l.name for l in issue.labels],
        "comments": [comment.body or '' for comment in issue.get_comments()],
        "mentioned_files": find_mentioned_files(issue.body or ''),
    }

def find_mentioned_files(text):
    if not text:
        return []
    words = text.split()
    return [word for word in words if '.' in word and '/' in word]

def suggest_contribution(repo, issue):
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