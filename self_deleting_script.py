#!/usr/bin/env python3
"""
Self-deleting script that prints "Hello, World!" and then deletes itself.
"""

import os

def main():
    # Print "Hello, World!" to stdout
    print("Hello, World!")
    
    # Get the absolute path of the current script
    script_path = os.path.abspath(__file__)
    
    # Attempt to remove the file
    try:
        os.remove(script_path)
        print(f"Successfully deleted: {script_path}")
    except FileNotFoundError:
        # File might have been already deleted or moved
        print(f"File not found: {script_path}")
    except PermissionError:
        # Permission denied to delete the file
        print(f"Permission denied: {script_path}")
    except OSError as e:
        # Other OS-related errors
        print(f"Error deleting file: {e}")

if __name__ == "__main__":
    main()
