#!/usr/bin/env python3
"""
Main entry point for the calculator CLI.
"""

import sys
import os

# Add the current directory to the path so we can import calculator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main

if __name__ == "__main__":
    main()