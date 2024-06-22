import re
import json
import base64
import ast
from collections import Counter
from datetime import datetime, timedelta
from utils import extract_section

class RepoAnalyzer:
    def __init__(self, repo):
        self.repo = repo
        self.analysis = {}

    def analyze(self):
        self.analysis = {
            "name": self.repo.name,
            "description": self.repo.description,
            "language": self.repo.language,
            "contributors": [c.login for c in self.repo.get_contributors()[:5]],
            "setup_instructions": self.get_setup_instructions(),
            "project_structure": self.identify_project_structure(),
            "file_analysis": self.analyze_repository_files(),
            "issue_pr_trends": self.analyze_issue_pr_trends(),
            "commit_history": self.analyze_commit_history(),
            "dependency_analysis": self.analyze_dependencies(),
            "code_complexity": self.estimate_code_complexity(),
            "issue_templates": self.analyze_issue_templates()
        }
        return self.analysis

    def get_setup_instructions(self):
        files_to_check = ["README.md", "CONTRIBUTING.md", "SETUP.md", "CONTRIBUTE.md"]
        setup_info = {
            "setup_instructions": "",
            "contribution_guidelines": "",
        }
        
        for file_name in files_to_check:
            try:
                content = self.repo.get_contents(file_name).decoded_content.decode('utf-8')
                setup_info["setup_instructions"] = extract_section(content, "installation|setup|getting started")
                setup_info["contribution_guidelines"] = extract_section(content, "contributing|how to contribute")
                
                if setup_info["setup_instructions"] and setup_info["contribution_guidelines"]:
                    break
            except:
                continue
        
        return setup_info

    def identify_project_structure(self):
        structure = {
            "directories": [],
            "important_files": [],
            "inferred_language": self.repo.language,
            "potential_standards": []
        }
        
        contents = self.repo.get_contents("")
        for content in contents:
            if content.type == "dir":
                structure["directories"].append(content.name)
            elif content.type == "file":
                if content.name in [".editorconfig", ".pylintrc", "tox.ini", "setup.cfg"]:
                    structure["important_files"].append(content.name)
                    structure["potential_standards"].append(f"Possible use of {content.name} for code style")
        
        if "tests" in structure["directories"]:
            structure["potential_standards"].append("Presence of a 'tests' directory suggests unit testing is used")
        if "docs" in structure["directories"]:
            structure["potential_standards"].append("Presence of a 'docs' directory suggests documentation is maintained")
        
        return structure

    def analyze_repository_files(self):
        analysis = {
            "community_health": [],
            "ci_cd": [],
            "important_files": [],
            "language_specific": {}
        }
        
        community_files = ["CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md"]
        ci_cd_files = [".travis.yml", ".github/workflows", "azure-pipelines.yml", "Jenkinsfile", ".gitlab-ci.yml"]
        important_files = [".gitignore", "README.md", "LICENSE"]
        
        contents = self.repo.get_contents("")
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
        
        if self.repo.language:
            analysis["language_specific"]["primary_language"] = self.repo.language
            if self.repo.language.lower() == "python":
                python_files = ["requirements.txt", "setup.py", "Pipfile"]
                for file in python_files:
                    try:
                        self.repo.get_contents(file)
                        analysis["language_specific"]["python_files"] = analysis["language_specific"].get("python_files", []) + [file]
                    except:
                        pass
            elif self.repo.language.lower() == "javascript":
                try:
                    package_json = self.repo.get_contents("package.json")
                    package_content = base64.b64decode(package_json.content).decode('utf-8')
                    analysis["language_specific"]["package_json"] = package_content
                except:
                    pass
        
        return analysis

    def analyze_issue_pr_trends(self):
        analysis = {
            "issues": {"open": 0, "closed": 0, "recent_activity": 0},
            "pull_requests": {"open": 0, "closed": 0, "merged": 0, "recent_activity": 0},
            "top_issue_labels": [],
            "avg_time_to_close_issues": None,
            "avg_time_to_merge_prs": None
        }
        
        issues = self.repo.get_issues(state='all')
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
        
        pulls = self.repo.get_pulls(state='all')
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
        
        if issue_close_times:
            analysis["avg_time_to_close_issues"] = sum(issue_close_times) / len(issue_close_times) / 86400  # Convert to days
        if pr_merge_times:
            analysis["avg_time_to_merge_prs"] = sum(pr_merge_times) / len(pr_merge_times) / 86400  # Convert to days
        
        analysis["top_issue_labels"] = [label for label, _ in label_counter.most_common(5)]
        
        return analysis

    def analyze_commit_history(self):
        analysis = {
            "total_commits": 0,
            "recent_commits": 0,
            "top_contributors": [],
            "commit_frequency": None
        }
        
        commits = self.repo.get_commits()
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

    def analyze_dependencies(self):
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
                    content = self.repo.get_contents(file)
                    analysis["dependency_files"].append(file)
                    if file == "requirements.txt":
                        deps = content.decoded_content.decode().split("\n")
                        analysis["dependencies"].extend([dep.strip() for dep in deps if dep.strip()])
                    elif file == "package.json":
                        package_data = json.loads(content.decoded_content.decode())
                        analysis["dependencies"].extend(package_data.get("dependencies", {}).keys())
                        analysis["dependencies"].extend(package_data.get("devDependencies", {}).keys())
                except:
                    pass
        
        return analysis

    def estimate_code_complexity(self):
        complexity = {
            "total_lines": 0,
            "total_functions": 0,
            "avg_function_complexity": 0,
            "files_analyzed": 0
        }

        for content_file in self.repo.get_contents(""):
            if content_file.type == "file" and content_file.name.endswith(".py"):
                try:
                    file_content = self.repo.get_contents(content_file.path).decoded_content.decode('utf-8')
                    complexity["total_lines"] += len(file_content.splitlines())
                    
                    tree = ast.parse(file_content)
                    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    complexity["total_functions"] += len(functions)
                    
                    file_complexity = sum(self.calculate_cyclomatic_complexity(func) for func in functions)
                    if functions:
                        complexity["avg_function_complexity"] += file_complexity / len(functions)
                    
                    complexity["files_analyzed"] += 1
                except Exception as e:
                    print(f"Error analyzing file {content_file.name}: {str(e)}")

        if complexity["files_analyzed"] > 0:
            complexity["avg_function_complexity"] /= complexity["files_analyzed"]

        return complexity

    def calculate_cyclomatic_complexity(self, func):
        complexity = 1
        for node in ast.walk(func):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
                complexity += 1
        return complexity

    def analyze_issue_templates(self):
        templates = {}
        template_dir = '.github/ISSUE_TEMPLATE'
        
        try:
            contents = self.repo.get_contents(template_dir)
            for content_file in contents:
                if content_file.name.endswith(('.md', '.yml', '.yaml')):
                    template_content = content_file.decoded_content.decode('utf-8')
                    template_name = content_file.name.rsplit('.', 1)[0]
                    templates[template_name] = self.parse_issue_template(template_content)
        except:
            # If .github/ISSUE_TEMPLATE doesn't exist, check for individual files
            for template_name in ['bug_report', 'feature_request']:
                try:
                    content = self.repo.get_contents(f'{template_dir}/{template_name}.md')
                    template_content = content.decoded_content.decode('utf-8')
                    templates[template_name] = self.parse_issue_template(template_content)
                except:
                    pass

        return templates

    def parse_issue_template(self, content):
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)[1:]
        parsed_template = {}
        for section in sections:
            lines = section.strip().split('\n')
            section_name = lines[0].strip()
            section_content = '\n'.join(lines[1:]).strip()
            parsed_template[section_name] = section_content
        return parsed_template

    def generate_markdown(self):
        md = f"# Contribution Guide for {self.analysis['name']}\n\n"
        md += f"## Repository Analysis\n"
        md += f"- Name: {self.analysis['name']}\n"
        md += f"- Description: {self.analysis['description']}\n"
        md += f"- Primary Language: {self.analysis['language']}\n"
        md += f"- Top Contributors: {', '.join(self.analysis['contributors'])}\n\n"
        
        md += f"## Setup Instructions\n"
        md += self.analysis['setup_instructions']['setup_instructions'] or "No specific setup instructions found.\n"
        md += "\n"
        
        md += f"## Contribution Guidelines\n"
        md += self.analysis['setup_instructions']['contribution_guidelines'] or "No specific contribution guidelines found.\n"
        md += "\n"
        
        md += f"## Project Structure\n"
        md += f"- Directories: {', '.join(self.analysis['project_structure']['directories'])}\n"
        md += f"- Important Files: {', '.join(self.analysis['project_structure']['important_files'])}\n"
        md += f"- Inferred Language: {self.analysis['project_structure']['inferred_language']}\n"
        md += "- Potential Coding Standards:\n"
        for standard in self.analysis['project_structure']['potential_standards']:
            md += f"  - {standard}\n"
        md += "\n"

        md += f"## Repository File Analysis\n"
        md += f"### Community Health Files\n"
        if self.analysis['file_analysis']['community_health']:
            md += f"The following community health files are present:\n"
            for file in self.analysis['file_analysis']['community_health']:
                md += f"- {file}\n"
        else:
            md += f"No community health files found.\n"
        
        md += f"\n### CI/CD Configuration\n"
        if self.analysis['file_analysis']['ci_cd']:
            md += f"The following CI/CD configurations were detected:\n"
            for ci_cd in self.analysis['file_analysis']['ci_cd']:
                md += f"- {ci_cd}\n"
        else:
            md += f"No CI/CD configuration detected.\n"
        
        md += f"\n### Important Files\n"
        if self.analysis['file_analysis']['important_files']:
            md += f"The following important files are present:\n"
            for file in self.analysis['file_analysis']['important_files']:
                md += f"- {file}\n"
        if 'gitignore_content' in self.analysis['file_analysis']:
            md += f"\n.gitignore file content:\n```\n{self.analysis['file_analysis']['gitignore_content']}\n```\n"
        
        md += f"\n### Language-Specific Analysis\n"
        if self.analysis['file_analysis']['language_specific']:
            md += f"Primary language: {self.analysis['file_analysis']['language_specific']['primary_language']}\n"
            if 'python_files' in self.analysis['file_analysis']['language_specific']:
                md += f"Python-specific files found: {', '.join(self.analysis['file_analysis']['language_specific']['python_files'])}\n"
            if 'package_json' in self.analysis['file_analysis']['language_specific']:
                md += f"package.json found for JavaScript project.\n"
        else:
            md += f"No language-specific information found.\n"
        
        md += "\n"
        
        md += f"## Issue and Pull Request Trends\n"
        md += f"- Open Issues: {self.analysis['issue_pr_trends']['issues']['open']}\n"
        md += f"- Closed Issues: {self.analysis['issue_pr_trends']['issues']['closed']}\n"
        md += f"- Open Pull Requests: {self.analysis['issue_pr_trends']['pull_requests']['open']}\n"
        md += f"- Merged Pull Requests: {self.analysis['issue_pr_trends']['pull_requests']['merged']}\n"
        md += f"- Recent Issue Activity (last 30 days): {self.analysis['issue_pr_trends']['issues']['recent_activity']}\n"
        md += f"- Recent PR Activity (last 30 days): {self.analysis['issue_pr_trends']['pull_requests']['recent_activity']}\n"
        if self.analysis['issue_pr_trends']['avg_time_to_close_issues']:
            md += f"- Average Time to Close Issues: {self.analysis['issue_pr_trends']['avg_time_to_close_issues']:.2f} days\n"
        if self.analysis['issue_pr_trends']['avg_time_to_merge_prs']:
            md += f"- Average Time to Merge PRs: {self.analysis['issue_pr_trends']['avg_time_to_merge_prs']:.2f} days\n"
        md += f"- Top Issue Labels: {', '.join(self.analysis['issue_pr_trends']['top_issue_labels'])}\n\n"
        
        md += f"## Commit History Analysis\n"
        md += f"- Total Commits: {self.analysis['commit_history']['total_commits']}\n"
        md += f"- Recent Commits (last 30 days): {self.analysis['commit_history']['recent_commits']}\n"
        md += f"- Top Contributors: {', '.join(self.analysis['commit_history']['top_contributors'])}\n"
        if self.analysis['commit_history']['commit_frequency']:
            md += f"- Commit Frequency: {self.analysis['commit_history']['commit_frequency']:.2f} commits per day\n\n"
        
        md += f"## Dependency Analysis\n"
        md += f"- Dependency Files Found: {', '.join(self.analysis['dependency_analysis']['dependency_files'])}\n"
        if self.analysis['dependency_analysis']['dependencies']:
            md += f"- Dependencies:\n"
            for dep in self.analysis['dependency_analysis']['dependencies'][:10]:  # Limit to first 10 for brevity
                md += f"  - {dep}\n"
            if len(self.analysis['dependency_analysis']['dependencies']) > 10:
                md += f"  - ... and {len(self.analysis['dependency_analysis']['dependencies']) - 10} more\n"
        else:
            md += f"- No dependencies found or unable to parse dependency files.\n"
        
        md += "\n"
        
        md += f"## Code Complexity Analysis\n"
        md += f"- Total Lines of Code: {self.analysis['code_complexity']['total_lines']}\n"
        md += f"- Total Functions: {self.analysis['code_complexity']['total_functions']}\n"
        md += f"- Average Function Complexity: {self.analysis['code_complexity']['avg_function_complexity']:.2f}\n"
        md += f"- Files Analyzed: {self.analysis['code_complexity']['files_analyzed']}\n\n"

        md += f"## Issue Templates Analysis\n"
        if self.analysis['issue_templates']:
            md += "The following issue templates were found:\n"
            for template_name, template_content in self.analysis['issue_templates'].items():
                md += f"- {template_name}\n"
                md += "  Sections:\n"
                for section_name in template_content.keys():
                    md += f"  - {section_name}\n"
        else:
            md += "No issue templates were found in this repository.\n"
        md += "\n"

        return md