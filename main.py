import os
from github import Github
from repo_analyzer import RepoAnalyzer
from issue_analyzer import get_open_issues, analyze_issue, suggest_contribution

def main():
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo_url = input("Please enter the GitHub repository URL: ")
    repo = g.get_repo(repo_url.split('github.com/')[-1])

    analyzer = RepoAnalyzer(repo)
    print("Analyzing repository...")
    repo_analysis = analyzer.analyze()

    labels = input("Enter labels to filter by (comma-separated, or press enter to skip): ").split(',')
    labels = [label.strip() for label in labels if label.strip()]
    
    keywords = input("Enter keywords to filter by (comma-separated, or press enter to skip): ").split(',')
    keywords = [keyword.strip() for keyword in keywords if keyword.strip()]

    print("Fetching and analyzing open issues...")
    issues = get_open_issues(repo, labels=labels, keywords=keywords)

    with open("contribution_guide.md", "w") as f:
        f.write(analyzer.generate_markdown())

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