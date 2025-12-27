#!/usr/bin/env python3
"""Check for potential dataclass access issues."""
import re
import sys

# Patterns to check
patterns = {
    'corner': r'corner\s*\[',
    'corners': r'corners\d*\s*\[',
    'decomp': r'decomp\s*\[',
    'decomposition': r'decomposition\s*\[',
    'zone': r'zone\s*\[',
    'stint': r'stint\s*\[',
}

files_to_check = [
    'app/streamlit_app.py',
    'app/components/insight_summary.py',
    'app/components/kpi_cards.py',
    'app/pages/race_pace.py',
    'app/pages/style_profile.py',
    'app/pages/exports.py',
]

issues_found = False
for filepath in files_to_check:
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                for name, pattern in patterns.items():
                    if re.search(pattern, line):
                        # Skip if it's in a comment or string
                        if '#' not in line or line.index('#') > line.index('['):
                            print(f"{filepath}:{line_num}: Potential {name} dict access: {line.strip()}")
                            issues_found = True
    except FileNotFoundError:
        pass

if not issues_found:
    print("✓ No dataclass dictionary access issues found!")
    sys.exit(0)
else:
    print("\n✗ Found potential issues (may be false positives)")
    sys.exit(1)
