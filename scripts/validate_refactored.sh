#!/bin/bash
# Validate the refactored agent implementation

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check for workspace and story arguments
if [ "$#" -lt 2 ]; then
    echo -e "${RED}Error: Missing required arguments${NC}"
    echo "Usage: $0 <workspace_id> <story_id> [enhance|analyse]"
    echo "Example: $0 my-workspace 12345 enhance"
    exit 1
fi

# Set Python environment
export PYTHONPATH="${PYTHONPATH}:/Users/nathandonaldson/Documents/shortcut-agent-openai"

WORKSPACE_ID=$1
STORY_ID=$2
WORKFLOW=${3:-"enhance"}  # Default to enhance workflow

# Validate workflow type
if [ "$WORKFLOW" != "enhance" ] && [ "$WORKFLOW" != "analyse" ]; then
    echo -e "${RED}Error: Invalid workflow type '$WORKFLOW'${NC}"
    echo "Valid values: enhance, analyse"
    exit 1
fi

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Running Refactored Agent Validation Tests${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo

# Run unit tests first
echo -e "${BLUE}Running unit tests for BaseAgent...${NC}"
python3 -m pytest tests/unit/agents/test_base_agent.py -v || /Users/nathandonaldson/Library/Python/3.9/bin/pytest tests/unit/agents/test_base_agent.py -v
UNIT_EXIT_CODE=$?

if [ $UNIT_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ BaseAgent unit tests failed!${NC}"
    exit $UNIT_EXIT_CODE
else
    echo -e "${GREEN}✅ BaseAgent unit tests passed!${NC}"
fi

echo

echo -e "${BLUE}Running unit tests for TriageAgent...${NC}"
python3 -m pytest tests/unit/agents/triage/test_triage_agent.py -v || /Users/nathandonaldson/Library/Python/3.9/bin/pytest tests/unit/agents/triage/test_triage_agent.py -v
TRIAGE_EXIT_CODE=$?

if [ $TRIAGE_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ TriageAgent unit tests failed!${NC}"
    exit $TRIAGE_EXIT_CODE
else
    echo -e "${GREEN}✅ TriageAgent unit tests passed!${NC}"
fi

echo

echo -e "${BLUE}Running integration tests...${NC}"
python3 -m pytest tests/integration/test_agent_workflow.py -v || /Users/nathandonaldson/Library/Python/3.9/bin/pytest tests/integration/test_agent_workflow.py -v
INTEGRATION_EXIT_CODE=$?

if [ $INTEGRATION_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Integration tests failed!${NC}"
    exit $INTEGRATION_EXIT_CODE
else
    echo -e "${GREEN}✅ Integration tests passed!${NC}"
fi

echo

# If all tests passed, run the traced workflow
echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Running Traced Workflow Test${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo -e "Workspace: ${YELLOW}$WORKSPACE_ID${NC}"
echo -e "Story ID:  ${YELLOW}$STORY_ID${NC}"
echo -e "Workflow:  ${YELLOW}$WORKFLOW${NC}"
echo

# Run the test script
python3 scripts/test_traced_workflow.py --workspace $WORKSPACE_ID --story $STORY_ID --workflow $WORKFLOW

# Capture exit code
WORKFLOW_EXIT_CODE=$?

# If the script succeeded, show next steps
if [ $WORKFLOW_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=======================================================${NC}"
    echo -e "${GREEN}✅ All validation tests passed successfully!${NC}"
    echo -e "${GREEN}=======================================================${NC}"
    echo
    echo -e "${BLUE}Next steps to complete the migration:${NC}"
    echo "1. Deploy to production with refactored agents"
    echo "2. Monitor for issues in production"
    echo "3. After successful production validation:"
    echo "   a. Rename refactored files to replace originals"
    echo "   b. Remove original agent implementations"
    echo "   c. Update imports to use standard module paths"
else
    echo -e "${RED}=======================================================${NC}"
    echo -e "${RED}❌ Traced workflow test failed!${NC}"
    echo -e "${RED}=======================================================${NC}"
    echo
    echo -e "${BLUE}Troubleshooting steps:${NC}"
    echo "1. Check the logs directory for detailed error information"
    echo "2. Verify API keys and environment configuration"
    echo "3. Try with different stories or workflow types"
fi

exit $WORKFLOW_EXIT_CODE