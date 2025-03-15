#!/usr/bin/env python3
"""
Script to examine a specific module file.
"""

import os
import sys
import importlib.util

def view_file_content(module_path):
    """View the content of a module file."""
    try:
        # Try to get the file path from its module path
        spec = importlib.util.find_spec(module_path)
        if spec and spec.origin:
            file_path = spec.origin
            print(f"Module: {module_path}")
            print(f"File path: {file_path}")
            if os.path.exists(file_path):
                print("\nFile content:")
                with open(file_path, 'r') as f:
                    content = f.read()
                    print(content)
            else:
                print(f"File does not exist: {file_path}")
        else:
            print(f"Could not find module: {module_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Module to examine
    module_path = "agents.tracing.processor_interface"
    view_file_content(module_path)
