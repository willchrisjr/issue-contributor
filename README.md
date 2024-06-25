# Issue Contributor

Issue Contributor is a Python-based tool designed to analyze GitHub repositories and provide tailored guidance for potential contributors. The tool aims to lower the barrier to entry for open-source contributions by offering detailed insights into repositories and their open issues.

## Project Overview

This tool performs the following key functions:

1. Repository Analysis:
   - Examines the repository structure
   - Identifies important files (README, CONTRIBUTING, etc.)
   - Analyzes community health files
   - Detects CI/CD configurations
   - Provides language-specific analysis

2. Issue Analysis:
   - Retrieves and analyzes open issues
   - Classifies issues by type (bug, feature request, etc.)
   - Scores issues based on approachability for new contributors
   - Identifies related files mentioned in issues
   - Extracts code snippets from issue descriptions and comments

3. Code Analysis:
   - Performs basic code complexity analysis
   - Identifies dependencies in related files
   - Locates relevant test files and test cases

4. Contribution Guidance:
   - Generates automated fix suggestions based on issue type and code analysis
   - Creates a context-aware contribution guide for each issue
   - Identifies similar resolved issues for reference

5. User Interaction:
   - Allows users to input repository URL
   - Provides options to filter issues by labels and keywords

## Current Implementation

The project currently consists of several Python scripts:

- `main.py`: The entry point of the application, orchestrating the overall analysis process.
- `repo_analyzer.py`: Handles repository-level analysis.
- `issue_analyzer.py`: Manages issue retrieval, analysis, and scoring.
- `utils.py`: Contains utility functions used across the project.

The tool generates a comprehensive Markdown file (`contribution_guide.md`) containing the analysis results and contribution guidance for the specified repository.

## Potential Future Features

While the core functionality is in place, there are several exciting features planned for future development:

1. Advanced README and CONTRIBUTING file parsing: Implement more sophisticated text analysis to extract detailed information from these files.

2. Enhanced issue context analysis: Utilize advanced NLP techniques for better understanding of issue descriptions and comments.

3. Integration with professional code analysis tools: Incorporate tools like CodeQL for deeper code quality and security analysis.

4. Improved user interaction and customization: Develop a more interactive interface with additional customization options.

5. Personalized recommendations: Allow users to specify their skill level and interests for tailored issue suggestions.

6. Visual progress indicators: Add progress bars for long-running operations to enhance user experience.

7. Preference management: Implement functionality to save and load user filter preferences.

8. Multi-language support: Extend code analysis capabilities to cover a wider range of programming languages.

These planned features aim to make the tool more powerful, user-friendly, and adaptable to different projects and contributor needs.