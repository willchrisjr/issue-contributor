import os
import re
import json
import base64
from github import Github
from tqdm import tqdm
from datetime import datetime, timedelta
from collections import Counter

def get_setup_instructions(repo):
    """
    Extract setup instructions and contribution guidelines from README and CONTRIBUTING files.
    """
    files_to_check = ["README.md", "CONTRIBUTING.md", "SETUP.md", "CONTRIBUTE.md"]
    setup_info = {
        "setup_instructions": "",
        "contribution_guidelines": "",
    }
    
    for file_name in files_to_check:
        try:
            content = repo.get_contents(file_name).decoded_content.decode('utf-8')
            
            # Look for setup instructions
            setup_match = re.search(r'(?i)## (installation|setup|getting started).*?(?=##|\Z)', content, re.DOTALL)
            if setup_match and not setup_info["setup_instructions"]:
                setup_info["setup_instructions"] = setup_match.group(0).strip()
            
            # Look for contribution guidelines
            contrib_match = re.search(r'(?i)## (contributing|how to contribute).*?(?=##|\Z)', content, re.DOTALL)
            if contrib_match and not setup_info["contribution_guidelines"]:
                setup_info["contribution_guidelines"] = contrib_match.group(0).strip()
            
            if setup_info["setup_instructions"] and setup_info["contribution_guidelines"]:
                break
        except:
            continue
    
    return setup_info

def identify_project_structure(repo):
    """
    Identify project structure and attempt to infer coding standards.
    """
    structure = {
        "directories": [],
        "important_files": [],
        "inferred_language": repo.language,
        "potential_standards": []
    }
    
    contents = repo.get_contents("")
    for content in contents:
        if content.type == "dir":
            structure["directories"].append(content.name)
        elif content.type == "file":
            if content.name in [".editorconfig", ".pylintrc", "tox.ini", "setup.cfg"]:
                structure["important_files"].append(content.name)
                structure["potential_standards"].append(f"Possible use of {content.name} for code style")
    
    # Infer potential standards based on project structure
    if "tests" in structure["directories"]:
        structure["potential_standards"].append("Presence of a 'tests' directory suggests unit testing is used")
    if "docs" in structure["directories"]:
        structure["potential_standards"].append("Presence of a 'docs' directory suggests documentation is maintained")
    
    return structure

def analyze_repository_files(repo):
    """Analyze repository files for community health, CI/CD, and language-specific information."""
    analysis = {
        "community_health": [],
        "ci_cd": [],
        "important_files": [],
        "language_specific": {}
    }
    
    community_files = ["CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md"]
    ci_cd_files = [".travis.yml", ".github/workflows", "azure-pipelines.yml", "Jenkinsfile", ".gitlab-ci.yml"]
    important_files = [".gitignore", "README.md", "LICENSE"]
    
    contents = repo.get_contents("")
    for content in contents:
        if content.type == "file":
            if content.name in community_files:
                analysis["community_health"].append(content.name)
            elif content.name in ci_cd_files or (content.name == "workflows" and content.path == ".github/workflows"):
                analysis["ci_cd"].append(content.name)
            elif content.name in important_files:
                analysis["important_files"].append(content.name)
                if content.name == ".gitignore":
                    analysis["gitignore_content"] = base64.b64decode(content.content).decode('utf-8')
        elif content.type == "dir" and content.path == ".github/workflows":
            analysis["ci_cd"].append("GitHub Actions")
    
    # Language-specific analysis
    if repo.language:
        analysis["language_specific"]["primary_language"] = repo.language
        if repo.language.lower() == "python":
            python_files = ["requirements.txt", "setup.py", "Pipfile"]
            for file in python_files:
                try:
                    repo.get_contents(file)
                    analysis["language_specific"]["python_files"] = analysis["language_specific"].get("python_files", []) + [file]
                except:
                    pass
        elif repo.language.lower() == "javascript":
            try:
                package_json = repo.get_contents("package.json")
                package_content = base64.b64decode(package_json.content).decode('utf-8')
                analysis["language_specific"]["package_json"] = package_content
            except:
                pass
    
    return analysis

def analyze_issue_pr_trends(repo):
    """Analyze trends in issues and pull requests."""
    analysis = {
        "issues": {"open": 0, "closed": 0, "recent_activity": 0},
        "pull_requests": {"open": 0, "closed": 0, "merged": 0, "recent_activity": 0},
        "top_issue_labels": [],
        "avg_time_to_close_issues": None,
        "avg_time_to_merge_prs": None
    }
    
    # Analyze issues
    issues = repo.get_issues(state='all')
    issue_close_times = []
    label_counter = Counter()
    for issue in issues:
        if issue.pull_request is None:  # Exclude PRs from issue count
            if issue.state == 'open':
                analysis["issues"]["open"] += 1
            else:
                analysis["issues"]["closed"] += 1
                if issue.closed_at:
                    issue_close_times.append((issue.closed_at - issue.created_at).total_seconds())
            if datetime.now(issue.updated_at.tzinfo) - issue.updated_at < timedelta(days=30):
                analysis["issues"]["recent_activity"] += 1
            for label in issue.labels:
                label_counter[label.name] += 1
    
    # Analyze pull requests
    pulls = repo.get_pulls(state='all')
    pr_merge_times = []
    for pr in pulls:
        if pr.state == 'open':
            analysis["pull_requests"]["open"] += 1
        elif pr.merged:
            analysis["pull_requests"]["merged"] += 1
            if pr.merged_at:
                pr_merge_times.append((pr.merged_at - pr.created_at).total_seconds())
        else:
            analysis["pull_requests"]["closed"] += 1
        if datetime.now(pr.updated_at.tzinfo) - pr.updated_at < timedelta(days=30):
            analysis["pull_requests"]["recent_activity"] += 1
    
    # Calculate averages
    if issue_close_times:
        analysis["avg_time_to_close_issues"] = sum(issue_close_times) / len(issue_close_times) / 86400  # Convert to days
    if pr_merge_times:
        analysis["avg_time_to_merge_prs"] = sum(pr_merge_times) / len(pr_merge_times) / 86400  # Convert to days
    
    # Get top 5 issue labels
    analysis["top_issue_labels"] = [label for label, _ in label_counter.most_common(5)]
    
    return analysis

def analyze_commit_history(repo):
    """Analyze the commit history of the repository."""
    analysis = {
        "total_commits": 0,
        "recent_commits": 0,
        "top_contributors": [],
        "commit_frequency": None
    }
    
    commits = repo.get_commits()
    contributor_counter = Counter()
    
    for commit in commits:
        analysis["total_commits"] += 1
        if datetime.now(commit.commit.author.date.tzinfo) - commit.commit.author.date < timedelta(days=30):
            analysis["recent_commits"] += 1
        if commit.author:
            contributor_counter[commit.author.login] += 1
    
    analysis["top_contributors"] = [contributor for contributor, _ in contributor_counter.most_common(5)]
    
    if analysis["total_commits"] > 0:
        days_since_first_commit = (datetime.now(commits[analysis["total_commits"]-1].commit.author.date.tzinfo) - commits[analysis["total_commits"]-1].commit.author.date).days
        analysis["commit_frequency"] = analysis["total_commits"] / max(days_since_first_commit, 1)
    
    return analysis

def analyze_dependencies(repo):
    """Analyze the dependencies of the repository."""
    analysis = {
        "dependencies": [],
        "dependency_files": []
    }
    
    dependency_files = {
        "Python": ["requirements.txt", "Pipfile", "setup.py"],
        "JavaScript": ["package.json"],
        "Ruby": ["Gemfile"],
        "Java": ["pom.xml", "build.gradle"],
        "PHP": ["composer.json"],
        "Go": ["go.mod"]
    }
    
    for lang, files in dependency_files.items():
        for file in files:
            try:
                content = repo.get_contents(file)
                analysis["dependency_files"].append(file)
                if file == "requirements.txt":
                    deps = content.decoded_content.decode().split("\n")
                    analysis["dependencies"].extend([dep.strip() for dep in deps if dep.strip()])
                elif file == "package.json":
                    package_data = json.loads(content.decoded_content.decode())
                    analysis["dependencies"].extend(package_data.get("dependencies", {}).keys())
                    analysis["dependencies"].extend(package_data.get("devDependencies", {}).keys())
                # Add more parsing logic for other dependency files as needed
            except:
                pass
    
    return analysis

def analyze_repo(repo):
    """Analyze the repository for contribution-related information."""
    setup_info = get_setup_instructions(repo)
    project_structure = identify_project_structure(repo)
    file_analysis = analyze_repository_files(repo)
    issue_pr_trends = analyze_issue_pr_trends(repo)
    commit_history = analyze_commit_history(repo)
    dependency_analysis = analyze_dependencies(repo)
    
    analysis = {
        "name": repo.name,
        "description": repo.description,
        "language": repo.language,
        "contributors": [c.login for c in repo.get_contributors()[:5]],
        "setup_instructions": setup_info["setup_instructions"],
        "contribution_guidelines": setup_info["contribution_guidelines"],
        "project_structure": project_structure,
        "file_analysis": file_analysis,
        "issue_pr_trends": issue_pr_trends,
        "commit_history": commit_history,
        "dependency_analysis": dependency_analysis
    }
    return analysis

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
    days_old = (datetime.now(issue.created_at.tzinfo) - issue.created_at).days
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
        f.write(f"# Contribution Guide for {repo_analysis['name']}\n\n")
        f.write(f"## Repository Analysis\n")
        f.write(f"- Name: {repo_analysis['name']}\n")
        f.write(f"- Description: {repo_analysis['description']}\n")
        f.write(f"- Primary Language: {repo_analysis['language']}\n")
        f.write(f"- Top Contributors: {', '.join(repo_analysis['contributors'])}\n\n")
        
        f.write(f"## Setup Instructions\n")
        f.write(repo_analysis['setup_instructions'] or "No specific setup instructions found.\n")
        f.write("\n")
        
        f.write(f"## Contribution Guidelines\n")
        f.write(repo_analysis['contribution_guidelines'] or "No specific contribution guidelines found.\n")
        f.write("\n")
        
        f.write(f"## Project Structure\n")
        f.write(f"- Directories: {', '.join(repo_analysis['project_structure']['directories'])}\n")
        f.write(f"- Important Files: {', '.join(repo_analysis['project_structure']['important_files'])}\n")
        f.write(f"- Inferred Language: {repo_analysis['project_structure']['inferred_language']}\n")
        f.write("- Potential Coding Standards:\n")
        for standard in repo_analysis['project_structure']['potential_standards']:
            f.write(f"  - {standard}\n")
        f.write("\n")

        f.write(f"## Repository File Analysis\n")
        f.write(f"### Community Health Files\n")
        if repo_analysis['file_analysis']['community_health']:
            f.write(f"The following community health files are present:\n")
            for file in repo_analysis['file_analysis']['community_health']:
                f.write(f"- {file}\n")
        else:
            f.write(f"No community health files found.\n")
        
        f.write(f"\n### CI/CD Configuration\n")
        if repo_analysis['file_analysis']['ci_cd']:
            f.write(f"The following CI/CD configurations were detected:\n")
            for ci_cd in repo_analysis['file_analysis']['ci_cd']:
                f.write(f"- {ci_cd}\n")
        else:
            f.write(f"No CI/CD configuration detected.\n")
        
        f.write(f"\n### Important Files\n")
        if repo_analysis['file_analysis']['important_files']:
            f.write(f"The following important files are present:\n")
            for file in repo_analysis['file_analysis']['important_files']:
                f.write(f"- {file}\n")
        if 'gitignore_content' in repo_analysis['file_analysis']:
            f.write(f"\n.gitignore file content:\n```\n{repo_analysis['file_analysis']['gitignore_content']}\n```\n")
        
        f.write(f"\n### Language-Specific Analysis\n")
        if repo_analysis['file_analysis']['language_specific']:
            f.write(f"Primary language: {repo_analysis['file_analysis']['language_specific']['primary_language']}\n")
            if 'python_files' in repo_analysis['file_analysis']['language_specific']:
                f.write(f"Python-specific files found: {', '.join(repo_analysis['file_analysis']['language_specific']['python_files'])}\n")
            if 'package_json' in repo_analysis['file_analysis']['language_specific']:
                f.write(f"package.json found for JavaScript project.\n")
        else:
            f.write(f"No language-specific information found.\n")
        
        f.write("\n")
        
        f.write(f"## Issue and Pull Request Trends\n")
        f.write(f"- Open Issues: {repo_analysis['issue_pr_trends']['issues']['open']}\n")
        f.write(f"- Closed Issues: {repo_analysis['issue_pr_trends']['issues']['closed']}\n")
        f.write(f"- Open Pull Requests: {repo_analysis['issue_pr_trends']['pull_requests']['open']}\n")
        f.write(f"- Merged Pull Requests: {repo_analysis['issue_pr_trends']['pull_requests']['merged']}\n")
        f.write(f"- Recent Issue Activity (last 30 days): {repo_analysis['issue_pr_trends']['issues']['recent_activity']}\n")
        f.write(f"- Recent PR Activity (last 30 days): {repo_analysis['issue_pr_trends']['pull_requests']['recent_activity']}\n")
        if repo_analysis['issue_pr_trends']['avg_time_to_close_issues']:
            f.write(f"- Average Time to Close Issues: {repo_analysis['issue_pr_trends']['avg_time_to_close_issues']:.2f} days\n")
        if repo_analysis['issue_pr_trends']['avg_time_to_merge_prs']:
            f.write(f"- Average Time to Merge PRs: {repo_analysis['issue_pr_trends']['avg_time_to_merge_prs']:.2f} days\n")
        f.write(f"- Top Issue Labels: {', '.join(repo_analysis['issue_pr_trends']['top_issue_labels'])}\n\n")
        
        f.write(f"## Commit History Analysis\n")
        f.write(f"- Total Commits: {repo_analysis['commit_history']['total_commits']}\n")
        f.write(f"- Recent Commits (last 30 days): {repo_analysis['commit_history']['recent_commits']}\n")
        f.write(f"- Top Contributors: {', '.join(repo_analysis['commit_history']['top_contributors'])}\n")
        if repo_analysis['commit_history']['commit_frequency']:
            f.write(f"- Commit Frequency: {repo_analysis['commit_history']['commit_frequency']:.2f} commits per day\n\n")
        
        f.write(f"## Dependency Analysis\n")
        f.write(f"- Dependency Files Found: {', '.join(repo_analysis['dependency_analysis']['dependency_files'])}\n")
        if repo_analysis['dependency_analysis']['dependencies']:
            f.write(f"- Dependencies:\n")
            for dep in repo_analysis['dependency_analysis']['dependencies'][:10]:  # Limit to first 10 for brevity
                f.write(f"  - {dep}\n")
            if len(repo_analysis['dependency_analysis']['dependencies']) > 10:
                f.write(f"  - ... and {len(repo_analysis['dependency_analysis']['dependencies']) - 10} more\n")
        else:
            f.write(f"- No dependencies found or unable to parse dependency files.\n")
        
        f.write("\n")

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