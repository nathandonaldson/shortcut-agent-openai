#!/usr/bin/env python3
"""
Script to find the correct location of TraceProcessor in the OpenAI Agents SDK
"""

import sys
import inspect
import pkgutil
import importlib
from pprint import pprint

def search_for_class(module_name, class_name, visited=None):
    """
    Recursively search a module and its submodules for a class by name.
    """
    if visited is None:
        visited = set()
        
    if module_name in visited:
        return None
        
    visited.add(module_name)
    print(f"Searching in {module_name} for {class_name}...")
    
    try:
        # Try to import the module
        module = importlib.import_module(module_name)
        
        # Check if the class is directly available
        if hasattr(module, class_name):
            print(f"FOUND {class_name} in {module_name}!")
            return f"{module_name}.{class_name}"
            
        # Check all attributes for possible matches
        for attr_name in dir(module):
            if attr_name.startswith('_'):
                continue
                
            attr = getattr(module, attr_name)
            
            # Check if the attribute is a class that has a similar name
            if inspect.isclass(attr) and (
                attr_name == class_name or
                attr_name.lower() == class_name.lower() or
                (attr_name.lower().endswith(class_name.lower()) and len(attr_name) <= len(class_name) + 5)
            ):
                print(f"POSSIBLE MATCH: {module_name}.{attr_name}")
                print(f"  Methods: {[m for m in dir(attr) if not m.startswith('_')]}")
            
            # If it's a module, recursively search it
            if inspect.ismodule(attr):
                submodule_name = attr.__name__
                if submodule_name not in visited:
                    result = search_for_class(submodule_name, class_name, visited)
                    if result:
                        return result
                        
        # Search submodules that aren't directly imported
        if hasattr(module, '__path__'):
            for _, submodule_name, is_pkg in pkgutil.iter_modules(module.__path__, module.__name__ + '.'):
                if submodule_name not in visited:
                    result = search_for_class(submodule_name, class_name, visited)
                    if result:
                        return result
                        
    except ImportError as e:
        print(f"  Cannot import {module_name}: {e}")
    except Exception as e:
        print(f"  Error inspecting {module_name}: {e}")
        
    return None

def check_installed_package():
    """Check the installed package for the TraceProcessor class."""
    try:
        import agents
        print(f"Using OpenAI Agents SDK version: {getattr(agents, '__version__', 'Unknown')}")
        
        # Search for TraceProcessor in all submodules of agents
        search_for_class('agents', 'TraceProcessor')
        
        # Also check for interfaces
        search_for_class('agents', 'TraceProcessorInterface')
        search_for_class('agents', 'ProcessorInterface')
        
        # Check processor interfaces
        import agents.tracing.processor_interface
        print("\nProcessor Interface Module:")
        pprint(dir(agents.tracing.processor_interface))
    
    except ImportError as e:
        print(f"Failed to import OpenAI Agents SDK: {e}")

if __name__ == "__main__":
    check_installed_package()
