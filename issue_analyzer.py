# issue_analyzer.py
import re
from github import GithubException
from difflib import SequenceMatcher
import ast
from datetime import datetime, timedelta

def get_open_issues(repo, labels=None, keywords=None, limit=10, issue_templates=None):
    issues = repo.get_issues(state='open', labels=labels)
    filtered_issues = []
    
    for issue in issues:
        if len(filtered_issues) >= limit:
            break
        
        if keywords and not any(keyword.lower() in issue.title.lower() or keyword.lower() in (issue.body or '').lower() for keyword in keywords):
            continue
        
        score = score_issue(issue, issue_templates)
        filtered_issues.append((issue, score))
    
    return sorted(filtered_issues, key=lambda x: x[1], reverse=True)

def score_issue(issue, issue_templates):
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
    
    # Check if the issue follows a template
    if issue_templates:
        for template_name, template_content in issue_templates.items():
            if all(section in (issue.body or '') for section in template_content.keys()):
                score += 3
                break

    return score

def find_mentioned_files(text):
    if not text:
        return []
    # Look for file paths (e.g., src/main.py or docs/README.md)
    file_pattern = r'\b(?:[\w-]+/)*[\w-]+\.[a-zA-Z]+\b'
    return list(set(re.findall(file_pattern, text)))

def identify_related_files(repo, issue):
    related_files = set()
    
    # Check issue body
    mentioned_files = find_mentioned_files(issue.body or '')
    related_files.update(mentioned_files)
    
    # Check issue comments
    for comment in issue.get_comments():
        mentioned_files = find_mentioned_files(comment.body or '')
        related_files.update(mentioned_files)
    
    # Verify that the mentioned files actually exist in the repository
    existing_files = set()
    for file_path in related_files:
        try:
            repo.get_contents(file_path)
            existing_files.add(file_path)
        except GithubException:
            pass  # File doesn't exist, skip it
    
    return list(existing_files)

def classify_issue(issue):
    title = issue.title.lower()
    body = (issue.body or '').lower()
    labels = [label.name.lower() for label in issue.labels]

    # Define classification rules
    categories = {
        'bug': ['bug', 'error', 'problem', 'fail', 'defect', 'broken'],
        'feature request': ['feature request', 'enhancement', 'new feature', 'add', 'request'],
        'documentation': ['documentation', 'docs', 'typo', 'readme', 'wiki'],
        'question': ['question', 'help', 'how to', 'how do i', '?'],
        'enhancement': ['enhancement', 'improve', 'optimization', 'performance'],
    }

    # Check labels first
    for category, keywords in categories.items():
        if any(keyword in labels for keyword in keywords):
            return category

    # Check title and body
    for category, keywords in categories.items():
        if any(keyword in title or keyword in body for keyword in keywords):
            return category

    # If no category is found, return 'other'
    return 'other'

def extract_code_snippets(text):
    # Extract code blocks (```code```)
    code_blocks = re.findall(r'```[\s\S]*?```', text)
    
    # Extract inline code (`code`)
    inline_code = re.findall(r'`[^`\n]+`', text)
    
    return code_blocks + inline_code

def get_file_content(repo, file_path):
    try:
        content = repo.get_contents(file_path)
        return content.decoded_content.decode('utf-8')
    except GithubException:
        return None

def analyze_dependencies(repo, related_files):
    dependency_info = {}
    for file in related_files:
        content = get_file_content(repo, file)
        if content:
            if file.endswith('.py'):
                imports = re.findall(r'^import\s+(\w+)|^from\s+(\w+)\s+import', content, re.MULTILINE)
                dependency_info[file] = list(set([imp[0] or imp[1] for imp in imports]))
            elif file.endswith('.js'):
                imports = re.findall(r'(const|let|var)\s+{\s*([^}]+)\s*}\s*=\s*require$$[\'"]([^\'"]+)[\'"]$$|import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]', content)
                dependency_info[file] = list(set([imp[2] or imp[3] for imp in imports]))
    return dependency_info

def identify_test_files(repo, related_files):
    test_files = []
    for file in related_files:
        if 'test' in file.lower() or file.startswith('test_') or file.endswith('_test.py'):
            test_files.append(file)
    
    # If no test files found in related files, search the repo
    if not test_files:
        contents = repo.get_contents("")
        for content in contents:
            if content.type == "dir" and "test" in content.path.lower():
                test_files.extend(find_test_files_in_dir(repo, content.path))
    
    return test_files

def find_test_files_in_dir(repo, dir_path):
    test_files = []
    contents = repo.get_contents(dir_path)
    for content in contents:
        if content.type == "file" and (content.name.startswith('test_') or content.name.endswith('_test.py')):
            test_files.append(content.path)
        elif content.type == "dir":
            test_files.extend(find_test_files_in_dir(repo, content.path))
    return test_files

def extract_test_cases(repo, test_files):
    test_cases = {}
    for file in test_files:
        content = get_file_content(repo, file)
        if content:
            # Extract test function names
            test_functions = re.findall(r'def\s+(test_\w+)', content)
            if test_functions:
                test_cases[file] = test_functions
    return test_cases

def find_similar_resolved_issues(repo, issue, limit=5):
    similar_issues = []
    closed_issues = repo.get_issues(state='closed')
    
    for closed_issue in closed_issues:
        if closed_issue.number == issue.number:
            continue
        
        similarity = SequenceMatcher(None, issue.title, closed_issue.title).ratio()
        if similarity > 0.5:  # Adjust this threshold as needed
            similar_issues.append((closed_issue, similarity))
    
    similar_issues.sort(key=lambda x: x[1], reverse=True)
    return similar_issues[:limit]

def calculate_code_complexity(content):
    try:
        tree = ast.parse(content)
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity
    except SyntaxError:
        return None

class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.complexity = 0

    def visit_FunctionDef(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

def analyze_code_area_complexity(repo, related_files):
    complexity_analysis = {}
    for file in related_files:
        content = get_file_content(repo, file)
        if content:
            complexity = calculate_code_complexity(content)
            if complexity is not None:
                complexity_analysis[file] = complexity
    return complexity_analysis

def suggest_automated_fix(issue_analysis):
    suggestions = []

    # Suggest fixes based on issue category
    if issue_analysis['category'] == 'bug':
        suggestions.append("Consider adding error handling or input validation.")
    elif issue_analysis['category'] == 'feature request':
        suggestions.append("Start by creating a new function or class to implement the requested feature.")
    elif issue_analysis['category'] == 'documentation':
        suggestions.append("Update the relevant documentation files or add inline comments to clarify the code.")

    # Suggest fixes based on code complexity
    high_complexity_files = [file for file, complexity in issue_analysis['code_area_complexity'].items() if complexity > 10]
    if high_complexity_files:
        suggestions.append(f"Consider refactoring the following high-complexity files: {', '.join(high_complexity_files)}")

    # Suggest adding or updating tests
    if not issue_analysis['test_cases']:
        suggestions.append("Add new test cases to cover the changes you're making.")
    else:
        suggestions.append("Update existing test cases to reflect your changes.")

    return suggestions

def generate_context_aware_guide(repo, issue_analysis, automated_fix_suggestions):
    guide = f"# Context-Aware Contribution Guide for Issue #{issue_analysis['issue_number']}\n\n"

    guide += f"## Issue Overview\n"
    guide += f"Title: {issue_analysis['title']}\n"
    guide += f"Category: {issue_analysis['category']}\n"
    guide += f"Labels: {', '.join(issue_analysis['labels'])}\n\n"

    guide += f"## Related Files\n"
    for file in issue_analysis['related_files']:
        guide += f"- {file}\n"
    guide += "\n"

    if issue_analysis['dependency_context']:
        guide += f"## Dependency Context\n"
        for file, deps in issue_analysis['dependency_context'].items():
            guide += f"- {file}: {', '.join(deps)}\n"
        guide += "\n"

    if issue_analysis['test_files']:
        guide += f"## Related Test Files\n"
        for test_file in issue_analysis['test_files']:
            guide += f"- {test_file}\n"
        guide += "\n"

    if issue_analysis['similar_resolved_issues']:
        guide += f"## Similar Resolved Issues\n"
        for similar_issue, similarity in issue_analysis['similar_resolved_issues']:
            guide += f"- #{similar_issue.number}: {similar_issue.title} (Similarity: {similarity:.2f})\n"
        guide += "\n"

    guide += f"## Automated Fix Suggestions\n"
    for suggestion in automated_fix_suggestions:
        guide += f"- {suggestion}\n"
    guide += "\n"

    guide += f"## Steps to Contribute\n"
    guide += "1. Fork the repository\n"
    guide += "2. Clone your fork locally\n"
    guide += "3. Create a new branch for your changes\n"
    guide += "4. Make the necessary changes, following the automated fix suggestions\n"
    guide += "5. Add or update tests as needed\n"
    guide += "6. Commit your changes with a descriptive commit message\n"
    guide += "7. Push your changes to your fork\n"
    guide += "8. Create a pull request, referencing this issue\n"

    return guide

def analyze_issue(repo, issue, issue_templates):
    analysis = {
        "issue_number": issue.number,
        "title": issue.title or '',
        "body": issue.body or '',
        "labels": [l.name for l in issue.labels],
        "comments": [comment.body or '' for comment in issue.get_comments()],
        "follows_template": False,
        "template_name": None,
        "filled_sections": [],
        "related_files": identify_related_files(repo, issue),
        "category": classify_issue(issue),
        "code_snippets": extract_code_snippets(issue.body or ''),
        "dependency_context": {},
        "test_files": [],
        "test_cases": {},
        "similar_resolved_issues": [],
        "code_area_complexity": {}
    }

    if issue_templates:
        for template_name, template_content in issue_templates.items():
            if all(section in analysis["body"] for section in template_content.keys()):
                analysis["follows_template"] = True
                analysis["template_name"] = template_name
                analysis["filled_sections"] = list(template_content.keys())
                break

    # Extract code snippets from comments
    for comment in analysis["comments"]:
        analysis["code_snippets"].extend(extract_code_snippets(comment))

    # Analyze dependencies for related files
    analysis["dependency_context"] = analyze_dependencies(repo, analysis["related_files"])

    # Identify test files and cases
    analysis["test_files"] = identify_test_files(repo, analysis["related_files"])
    analysis["test_cases"] = extract_test_cases(repo, analysis["test_files"])

    # Find similar resolved issues
    analysis["similar_resolved_issues"] = find_similar_resolved_issues(repo, issue)

    # Analyze code area complexity
    analysis["code_area_complexity"] = analyze_code_area_complexity(repo, analysis["related_files"])

    # Generate automated fix suggestions
    analysis["automated_fix_suggestions"] = suggest_automated_fix(analysis)

    # Generate context-aware contribution guide
    analysis["context_aware_guide"] = generate_context_aware_guide(repo, analysis, analysis["automated_fix_suggestions"])

    return analysis