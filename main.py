import os
from github import Github
from repo_analyzer import RepoAnalyzer
from issue_analyzer import get_open_issues, analyze_issue

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
    issues = get_open_issues(repo, labels=labels, keywords=keywords, issue_templates=repo_analysis['issue_templates'])

    with open("contribution_guide.md", "w") as f:
        f.write(analyzer.generate_markdown())

        f.write(f"## Open Issues (Sorted by Approachability)\n")
        for issue, score in issues:
            issue_analysis = analyze_issue(repo, issue, repo_analysis['issue_templates'])
            f.write(f"### Issue #{issue.number}: {issue.title} (Score: {score})\n")
            f.write(f"Category: {issue_analysis['category']}\n")
            f.write(f"Labels: {', '.join([label.name for label in issue.labels])}\n")
            f.write(f"Description: {(issue.body or '')[:100]}...\n")
            if issue_analysis['follows_template']:
                f.write(f"Follows template: {issue_analysis['template_name']}\n")
                f.write(f"Filled sections: {', '.join(issue_analysis['filled_sections'])}\n")
            if issue_analysis['related_files']:
                f.write(f"Related files: {', '.join(issue_analysis['related_files'])}\n")
            if issue_analysis['code_snippets']:
                f.write(f"Code snippets found: {len(issue_analysis['code_snippets'])}\n")
            if issue_analysis['dependency_context']:
                f.write("Dependency context:\n")
                for file, deps in issue_analysis['dependency_context'].items():
                    f.write(f"  {file}: {', '.join(deps)}\n")
            if issue_analysis['test_files']:
                f.write("Related test files:\n")
                for test_file in issue_analysis['test_files']:
                    f.write(f"  {test_file}\n")
                    if test_file in issue_analysis['test_cases']:
                        f.write("    Test cases:\n")
                        for test_case in issue_analysis['test_cases'][test_file]:
                            f.write(f"      - {test_case}\n")
            if issue_analysis['similar_resolved_issues']:
                f.write("Similar resolved issues:\n")
                for similar_issue, similarity in issue_analysis['similar_resolved_issues']:
                    f.write(f"  - #{similar_issue.number}: {similar_issue.title} (Similarity: {similarity:.2f})\n")
            if issue_analysis['code_area_complexity']:
                f.write("Code area complexity:\n")
                for file, complexity in issue_analysis['code_area_complexity'].items():
                    f.write(f"  - {file}: Complexity score {complexity}\n")
            f.write("Automated Fix Suggestions:\n")
            for suggestion in issue_analysis['automated_fix_suggestions']:
                f.write(f"- {suggestion}\n")
            f.write("\nContext-Aware Contribution Guide:\n")
            f.write(issue_analysis['context_aware_guide'])
            f.write("\n\n")

    print("Analysis complete. Results written to contribution_guide.md")

if __name__ == "__main__":
    main()