#!/bin/bash
# Cleanup script to remove old agents module and migration scripts
set -e

echo "🧹 Starting cleanup of old files..."

# Remove old agents module
if [ -d "agents" ]; then
  echo "Removing old agents module directory..."
  rm -rf agents/
fi

# Remove migration scripts
echo "Removing migration scripts..."
rm -f rename_agents_module.py verify_imports.py verify_exports.py verify_sdk_import.py
rm -f fix_sdk_imports.py fix_tests.py test_renamed_module.py test_refactored_agents.py
rm -f test_sdk_integration.py test_imports.py

# Remove backup files
echo "Removing backup files..."
find . -name "*.bak" -type f -delete

# Remove temporary test files
echo "Removing temporary test files..."
rm -f test_refactored_webhook.sh run_with_mock.sh

# Commit changes
echo "Committing changes..."
git add -A
git status

echo "✅ Cleanup complete. Review the changes above before committing."
echo ""
echo "To commit these changes, run:"
echo "  git commit -m \"Remove old agents module and migration scripts\""
echo "  git push"