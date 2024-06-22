# utils.py
import re

def extract_section(content, section_name):
    pattern = rf'(?i)## {section_name}.*?(?=##|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(0).strip() if match else ""