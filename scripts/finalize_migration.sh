#!/bin/bash
# Finalize agent refactoring migration by replacing original files with refactored versions

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Finalizing Agent Refactoring Migration${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo

# Ask for confirmation since this is irreversible
echo -e "${YELLOW}WARNING:${NC} This script will replace the original agent files with refactored versions."
echo "This action cannot be undone and should only be performed after thorough testing in production."
echo
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${RED}Migration aborted.${NC}"
    exit 1
fi

echo
echo -e "${BLUE}Step 1: Backing up original files...${NC}"
# Create backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR/agents/{triage,analysis,update}

# Backup original files
cp -v agents/triage/triage_agent.py $BACKUP_DIR/agents/triage/
cp -v agents/analysis/analysis_agent.py $BACKUP_DIR/agents/analysis/
cp -v agents/update/update_agent.py $BACKUP_DIR/agents/update/

echo 
echo -e "${BLUE}Step 2: Replacing original files with refactored versions...${NC}"
mv -v agents/triage/triage_agent_refactored.py agents/triage/triage_agent.py
mv -v agents/analysis/analysis_agent_refactored.py agents/analysis/analysis_agent.py
mv -v agents/update/update_agent_refactored.py agents/update/update_agent.py

echo
echo -e "${BLUE}Step 3: Updating import statements in __init__.py files...${NC}"
sed -i.bak 's/triage_agent_refactored/triage_agent/g' agents/triage/__init__.py
sed -i.bak 's/analysis_agent_refactored/analysis_agent/g' agents/analysis/__init__.py
sed -i.bak 's/update_agent_refactored/update_agent/g' agents/update/__init__.py

echo
echo -e "${BLUE}Step 4: Running validation tests on replaced files...${NC}"
# Run simplified validation to make sure everything still works
python3 -m pytest tests/unit/agents/test_base_agent.py -v || /Users/nathandonaldson/Library/Python/3.9/bin/pytest tests/unit/agents/test_base_agent.py -v
python3 -m pytest tests/integration/test_agent_workflow.py -v || /Users/nathandonaldson/Library/Python/3.9/bin/pytest tests/integration/test_agent_workflow.py -v

# Capture the exit code
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo
    echo -e "${RED}=======================================================${NC}"
    echo -e "${RED}❌ Validation tests failed after file replacement!${NC}"
    echo -e "${RED}=======================================================${NC}"
    echo
    echo -e "${YELLOW}Restoring from backup...${NC}"
    
    # Restore original files
    cp -v $BACKUP_DIR/agents/triage/triage_agent.py agents/triage/
    cp -v $BACKUP_DIR/agents/analysis/analysis_agent.py agents/analysis/
    cp -v $BACKUP_DIR/agents/update/update_agent.py agents/update/
    
    # Restore import statements
    mv agents/triage/__init__.py.bak agents/triage/__init__.py
    mv agents/analysis/__init__.py.bak agents/analysis/__init__.py
    mv agents/update/__init__.py.bak agents/update/__init__.py
    
    echo -e "${RED}Migration failed. Original files have been restored.${NC}"
    exit $TEST_EXIT_CODE
else
    echo
    echo -e "${GREEN}=======================================================${NC}"
    echo -e "${GREEN}✅ Migration completed successfully!${NC}"
    echo -e "${GREEN}=======================================================${NC}"
    echo
    echo -e "Original files have been backed up to: ${YELLOW}$BACKUP_DIR${NC}"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Run your application to verify everything works"
    echo "2. Commit the changes to version control:"
    echo "   git add agents/"
    echo "   git commit -m \"Complete agent refactoring migration\""
    echo "3. Push the changes to remote"
    
    # Clean up backup .bak files
    rm -f agents/triage/__init__.py.bak
    rm -f agents/analysis/__init__.py.bak
    rm -f agents/update/__init__.py.bak
fi

echo
exit 0