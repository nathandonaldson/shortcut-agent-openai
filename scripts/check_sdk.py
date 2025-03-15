#!/usr/bin/env python3
"""
Script to check if the OpenAI Agent SDK is properly installed.
"""
import sys
import pkg_resources

def main():
    """Check if the OpenAI Agent SDK is installed."""
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    # Check if openai-agents is in installed packages
    try:
        agents_version = pkg_resources.get_distribution("openai-agents").version
        print(f"OpenAI Agents SDK installed: version {agents_version}")
    except pkg_resources.DistributionNotFound:
        print("OpenAI Agents SDK (openai-agents) is NOT installed")
    
    # Check if just openai is installed
    try:
        openai_version = pkg_resources.get_distribution("openai").version
        print(f"OpenAI SDK installed: version {openai_version}")
    except pkg_resources.DistributionNotFound:
        print("OpenAI SDK is NOT installed")
    
    # List all installed packages
    print("\nInstalled packages:")
    for pkg in pkg_resources.working_set:
        if 'openai' in pkg.key or 'agent' in pkg.key:
            print(f"  {pkg.key} {pkg.version}")
    
    # Try importing agents module
    try:
        import agents
        print(f"\nSuccessfully imported agents module from {agents.__file__}")
        print(f"Agents version: {getattr(agents, '__version__', 'Unknown')}")
        
        # Check for specific modules
        try:
            import agents.tracing
            print(f"Successfully imported agents.tracing from {agents.tracing.__file__}")
        except ImportError as e:
            print(f"Error importing agents.tracing: {e}")
        
        # Print out module structure
        print("\nAgents module structure:")
        for name in dir(agents):
            if not name.startswith('_'):
                print(f"  {name}")
                
    except ImportError as e:
        print(f"\nError importing agents module: {e}")

if __name__ == "__main__":
    main()
