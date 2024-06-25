# utils.py
import re

def extract_section(content, section_name):
    pattern = re.compile(rf"#+\s*{section_name}.*?\n(.*?)(?:\n#+\s|\Z)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(1).strip()
    return ""