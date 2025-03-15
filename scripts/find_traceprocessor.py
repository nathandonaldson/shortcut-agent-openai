#!/usr/bin/env python3
"""
Script to locate the TraceProcessor class in the OpenAI Agents SDK
"""

import os
import sys
import importlib
import inspect
import pkgutil

def check_module_for_class(module_name, class_name):
    """Check if a module contains a specific class."""
    try:
        module = importlib.import_module(module_name)
        print(f"Checking module: {module_name}")
        
        # Check for direct attribute
        if hasattr(module, class_name):
            print(f"✅ Class {class_name} found in {module_name}")
            return True
            
        # Get all submodules
        for _, submodule_name, ispkg in pkgutil.iter_modules(module.__path__, module.__name__ + '.'):
            if ispkg:
                # If it's a package, recursively check it
                if check_module_for_class(submodule_name, class_name):
                    return True
            else:
                # If it's a module, check it directly
                try:
                    submodule = importlib.import_module(submodule_name)
                    if hasattr(submodule, class_name):
                        print(f"✅ Class {class_name} found in {submodule_name}")
                        return True
                except ImportError as e:
                    print(f"Error importing {submodule_name}: {e}")
                    
        return False
    except ImportError as e:
        print(f"Error importing {module_name}: {e}")
        return False
    except Exception as e:
        print(f"Error checking {module_name}: {e}")
        return False

def find_class_in_package(package_name, class_name):
    """Find a class within a package."""
    print(f"Searching for {class_name} in {package_name}")
    
    try:
        # First, check the package itself
        if check_module_for_class(package_name, class_name):
            return
            
        # Check related packages
        related_packages = [
            f"{package_name}.tracing",
            f"{package_name}.processors",
            f"{package_name}.tracing.processors"
        ]
        
        for related_package in related_packages:
            if check_module_for_class(related_package, class_name):
                return
                
        print(f"❌ Class {class_name} not found in {package_name} or its submodules")
    except Exception as e:
        print(f"Error searching for {class_name} in {package_name}: {e}")

def list_dir_contents(path):
    """List the contents of a directory."""
    try:
        print(f"\nContents of {path}:")
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                print(f"  📁 {item}/")
            else:
                print(f"  📄 {item}")
    except Exception as e:
        print(f"Error listing directory {path}: {e}")

def check_site_packages():
    """Check the site-packages directory for installed packages."""
    try:
        import site
        site_packages = site.getsitepackages()
        for site_package in site_packages:
            if os.path.exists(site_package):
                list_dir_contents(site_package)
                
                # Check for agents directory
                agents_dir = os.path.join(site_package, "agents")
                if os.path.isdir(agents_dir):
                    print("\nFound agents directory:")
                    list_dir_contents(agents_dir)
                    
                    tracing_dir = os.path.join(agents_dir, "tracing")
                    if os.path.isdir(tracing_dir):
                        print("\nFound tracing directory:")
                        list_dir_contents(tracing_dir)
    except Exception as e:
        print(f"Error checking site-packages: {e}")

def main():
    """Main function."""
    print("Searching for TraceProcessor in agents package...")
    
    try:
        import agents
        print(f"OpenAI Agents SDK version: {getattr(agents, '__version__', 'Unknown')}")
        
        # Check if tracing module exists
        try:
            import agents.tracing
            print("✅ agents.tracing module exists")
            
            # List the contents of the tracing module
            print(f"Contents of agents.tracing: {dir(agents.tracing)}")
            
            # Check for processors module
            try:
                import agents.tracing.processors
                print("✅ agents.tracing.processors module exists")
                
                # List the contents of the processors module
                print(f"Contents of agents.tracing.processors: {dir(agents.tracing.processors)}")
            except ImportError:
                print("❌ agents.tracing.processors module not found")
        except ImportError:
            print("❌ agents.tracing module not found")
            
        # Systematically search for TraceProcessor
        find_class_in_package("agents", "TraceProcessor")
        
        # Check for interface module
        print("\nChecking for TraceProcessor in interface module...")
        for module_name in ["agents.tracing.interface", "agents.interface"]:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "TraceProcessor"):
                    print(f"✅ Found TraceProcessor in {module_name}")
                else:
                    print(f"❌ module {module_name} exists but doesn't have TraceProcessor")
            except ImportError:
                print(f"❌ module {module_name} not found")
                
        # Check site-packages
        check_site_packages()
        
    except ImportError:
        print("❌ agents package not installed")
        
if __name__ == "__main__":
    main()
