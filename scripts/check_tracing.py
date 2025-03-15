#!/usr/bin/env python
"""
Script to check the structure of agents.tracing module.
"""

import sys
import importlib
import inspect

def main():
    try:
        import agents
        print(f"Agents module exists, version: {getattr(agents, '__version__', 'Unknown')}")
    except ImportError:
        print("Agents module not found")
        return

    try:
        import agents.tracing
        print("\nAgents.tracing exists")
        print("Contents:", dir(agents.tracing))
    except ImportError:
        print("\nAgents.tracing module not found")
        return

    # Check for various potential locations of TraceProcessor
    potential_paths = [
        "agents.tracing.processors",
        "agents.tracing.processor",
        "agents.tracing",
        "agents.processors",
        "agents.tracing.setup"
    ]

    for path in potential_paths:
        try:
            module = importlib.import_module(path)
            if hasattr(module, "TraceProcessor"):
                print(f"\nFound TraceProcessor in {path}")
                print(f"TraceProcessor: {module.TraceProcessor}")
                if inspect.isclass(module.TraceProcessor):
                    print(f"Methods: {[m for m in dir(module.TraceProcessor) if not m.startswith('__')]}")
            else:
                print(f"\n{path} exists but does not contain TraceProcessor")
                print(f"Contents: {[item for item in dir(module) if not item.startswith('__')]}")
        except ImportError as e:
            print(f"\n{path} cannot be imported: {str(e)}")

if __name__ == "__main__":
    main()
