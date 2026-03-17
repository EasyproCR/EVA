#!/usr/bin/env python3
"""Test script to identify import issues"""

import sys
import traceback

def test_import(module_name):
    try:
        print(f"Trying to import {module_name}...", end=" ")
        __import__(module_name)
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

# Start with basic imports
print("=" * 60)
print("TESTING IMPORTS")
print("=" * 60)

imports_to_test = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
    "app.core.config",
    "app.services.llamaOrchestor",
    "app.main",
]

for module in imports_to_test:
    if not test_import(module):
        print(f"\n❌ Failed at module: {module}")
        break
    print()

print("Done!")
