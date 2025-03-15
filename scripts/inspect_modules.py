#!/usr/bin/env python3
"""
Script to inspect module structure in detail
"""

import sys
import inspect
import importlib

def explore_module(module_name):
    """Explore a module's structure in detail"""
    print(f"\n--- Exploring module: {module_name} ---")
    try:
        module = importlib.import_module(module_name)
        print(f"Module exists: {module.__name__}")
        
        # List all non-private attributes
        attrs = [attr for attr in dir(module) if not attr.startswith('_')]
        print(f"Attributes: {', '.join(attrs)}")
        
        # Look for class definitions
        for attr in attrs:
            obj = getattr(module, attr)
            if inspect.isclass(obj):
                print(f"Class: {attr}")
                # Show class methods
                methods = [m for m in dir(obj) if not m.startswith('_')]
                print(f"  Methods: {', '.join(methods)}")
        
        # Check for any interface or processor classes
        for attr in attrs:
            obj = getattr(module, attr)
            if inspect.isclass(obj) and ('process' in dir(obj) or 'interface' in str(obj).lower()):
                print(f"Potential match: {attr}")
                print(f"  Methods: {[m for m in dir(obj) if not m.startswith('_')]}")
    
    except ImportError as e:
        print(f"Cannot import module: {e}")
    except Exception as e:
        print(f"Error exploring module: {e}")

def main():
    """Main function"""
    # Modules to explore
    modules = [
        'agents',
        'agents.tracing',
        'agents.tracing.processor_interface',
        'agents.tracing.interface',
        'agents.tracing.processors',
        'agents.tracing.setup',
    ]
    
    for module_name in modules:
        explore_module(module_name)
    
    # Try to explicitly look for trace processor
    print("\n--- Searching for trace processor class ---")
    try:
        import agents.tracing
        
        # Print file content if small enough
        import os
        interface_file = getattr(agents.tracing.processor_interface, '__file__', None)
        if interface_file and os.path.exists(interface_file):
            print(f"\nContents of {interface_file}:")
            with open(interface_file, 'r') as f:
                content = f.read()
                print(content[:1000] + "..." if len(content) > 1000 else content)
    except Exception as e:
        print(f"Error examining tracing module: {e}")

if __name__ == "__main__":
    main()
