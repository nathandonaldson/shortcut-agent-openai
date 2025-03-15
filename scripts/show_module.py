#!/usr/bin/env python3
"""
Show the contents of a specific module.
"""
import inspect
import importlib

def inspect_module(module_name):
    """Print all the contents of a module."""
    try:
        module = importlib.import_module(module_name)
        print(f"Module: {module_name}")
        print(f"File path: {getattr(module, '__file__', 'Unknown')}")
        print("\nModule contents:")
        
        # Get all attributes that don't start with underscore
        for name in dir(module):
            if name.startswith('_'):
                continue
                
            obj = getattr(module, name)
            obj_type = type(obj).__name__
            
            # Special handling for different types
            if inspect.isclass(obj):
                print(f"CLASS: {name}")
                # Show methods
                for method_name in dir(obj):
                    if method_name.startswith('_'):
                        continue
                    method = getattr(obj, method_name)
                    if callable(method):
                        print(f"  - {method_name}()")
            elif inspect.isfunction(obj):
                print(f"FUNCTION: {name}()")
            elif inspect.ismodule(obj):
                print(f"MODULE: {name}")
            else:
                print(f"OTHER: {name} ({obj_type})")
                
        # Check for processor-related items
        print("\nSearching for processor-related items:")
        for name in dir(module):
            if 'process' in name.lower():
                obj = getattr(module, name)
                print(f"Found: {name} (type: {type(obj).__name__})")
                
    except ImportError as e:
        print(f"Error importing module {module_name}: {e}")
    except Exception as e:
        print(f"Error inspecting module {module_name}: {e}")

if __name__ == "__main__":
    # Check the specific module
    inspect_module("agents.tracing.processor_interface")
    
    # Also check the general tracing module
    print("\n" + "="*50 + "\n")
    inspect_module("agents.tracing")
