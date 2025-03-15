#!/usr/bin/env python3
import sys
import importlib.util

def check_package(package_name):
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            return False, None
        else:
            module = importlib.import_module(package_name)
            version = getattr(module, "__version__", "unknown")
            return True, version
    except ImportError:
        return False, None

# Check if agents package is available
agents_available, agents_version = check_package("agents")
print(f"OpenAI Agents SDK available: {agents_available}")
if agents_available:
    print(f"  Version: {agents_version}")
else:
    print("  NOT INSTALLED")

# Check if openai package is available
openai_available, openai_version = check_package("openai")
print(f"OpenAI API package available: {openai_available}")
if openai_available:
    print(f"  Version: {openai_version}")
else:
    print("  NOT INSTALLED")

print(f"Python version: {sys.version}")
