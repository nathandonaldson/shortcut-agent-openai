#!/bin/bash
# Script to finalize the refactoring by replacing original files with refactored versions
set -e

echo "🚀 Finalizing agent refactoring..."

# Create backup directory
BACKUP_DIR="pre_finalization_backup"
mkdir -p $BACKUP_DIR

# Back up original files
echo "Creating backups of original files..."
for file in $(find shortcut_agents -name "*_agent.py"); do
  cp "$file" "$BACKUP_DIR/$(basename $file)"
  echo "Backed up $file"
done

# List of agent modules to finalize
AGENT_MODULES=(
  "shortcut_agents/triage"
  "shortcut_agents/analysis" 
  "shortcut_agents/update"
)

# Process each module
for module in "${AGENT_MODULES[@]}"; do
  echo "Processing $module..."
  
  # Check if refactored file exists
  if [ -f "$module/$(basename $module)_agent_refactored.py" ]; then
    # If original file exists, remove it
    if [ -f "$module/$(basename $module)_agent.py" ]; then
      echo "Removing original file: $module/$(basename $module)_agent.py"
      rm "$module/$(basename $module)_agent.py"
    fi
    
    # Rename refactored file to replace original
    echo "Renaming: $module/$(basename $module)_agent_refactored.py -> $module/$(basename $module)_agent.py"
    mv "$module/$(basename $module)_agent_refactored.py" "$module/$(basename $module)_agent.py"
  else
    echo "No refactored file found for $module, skipping"
  fi
done

# Update imports in other files
echo "Updating imports in other files..."
find . -name "*.py" -not -path "./$BACKUP_DIR/*" -type f -exec sed -i '' 's/from shortcut_agents\([^_]*\)_agent_refactored/from shortcut_agents\1_agent/g' {} \;
find . -name "*.py" -not -path "./$BACKUP_DIR/*" -type f -exec sed -i '' 's/import shortcut_agents\([^_]*\)_agent_refactored/import shortcut_agents\1_agent/g' {} \;

# Stage changes
echo "Staging changes..."
git add shortcut_agents/

echo "✅ Refactoring finalization complete"
echo ""
echo "Please verify the changes with 'git status' before committing."
echo "To commit these changes, run:"
echo "  git commit -m \"Finalize agent refactoring by replacing original files with refactored versions\""
echo "  git push"