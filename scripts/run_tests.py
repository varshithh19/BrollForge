#!/usr/bin/env python3
"""
Test runner script for BrollForge.
Executes the full test suite without requiring external API keys.
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    args = [
        "-v",
        "--tb=short",
        "-s",
        "backend/tests",
    ]
    if len(sys.argv) > 1:
        args = sys.argv[1:]

    print(f"Running BrollForge test suite with arguments: {args}")
    exit_code = pytest.main(args)
    sys.exit(exit_code)
