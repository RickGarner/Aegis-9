#!/usr/bin/env python3
"""Verify role-mappings.json configuration."""

import json
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path("backend").resolve()))

config_path = Path("config/role-mappings.json")
data = json.loads(config_path.read_text(encoding="utf-8"))

print(f"Loaded {len(data['assignments'])} role assignments")
print()

for assignment in data['assignments']:
    subject = assignment['subject']
    roles = assignment['roles']
    print(f"  {assignment['type']}: {subject} -> {roles}")

print()
print("Role coverage:")
all_roles = set()
for assignment in data['assignments']:
    all_roles.update(assignment['roles'])

from app.authorization import ROLES
for role in sorted(ROLES):
    status = "✓" if role in all_roles else "✗"
    print(f"  {status} {role}")
