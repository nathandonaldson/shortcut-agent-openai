#!/bin/bash
# Setup script for testing refactored agents with OpenAI Agent SDK

# Define colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================================${NC}"
echo -e "${BLUE}Setting up environment for refactored agent validation${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo

# Check if Python 3.9+ is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
    python_version=$(python --version 2>&1 | awk '{print $2}')
else
    echo -e "${RED}Python not found. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Using Python $python_version via $PYTHON_CMD${NC}"

# Create virtual environment
echo -e "\n${BLUE}Creating virtual environment...${NC}"
$PYTHON_CMD -m venv agent_venv
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create virtual environment.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment created: agent_venv${NC}"

# Activate virtual environment
echo -e "\n${BLUE}Activating virtual environment...${NC}"
source agent_venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment activated${NC}"

# Upgrade pip
echo -e "\n${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to upgrade pip.${NC}"
    exit 1
fi

# Install dependencies
echo -e "\n${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt
pip install pytest
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create .env file
echo -e "\n${BLUE}Creating .env file...${NC}"
if [ ! -f .env ]; then
    touch .env
    echo "# OpenAI API Configuration" >> .env
    echo "OPENAI_API_KEY=" >> .env
    echo "" >> .env
    echo "# Shortcut API Configuration" >> .env
    echo "SHORTCUT_API_KEY_WORKSPACE1=" >> .env
    echo "" >> .env
    echo "# Environment" >> .env
    echo "VERCEL_ENV=development" >> .env
    
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}Please edit .env file to set your API keys${NC}"
else
    echo -e "${YELLOW}⚠️ .env file already exists. Skipping creation.${NC}"
fi

# Set PYTHONPATH
echo -e "\n${BLUE}Setting PYTHONPATH...${NC}"
project_path=$(pwd)
export PYTHONPATH=$project_path

echo -e "${GREEN}✅ PYTHONPATH set to $project_path${NC}"
echo -e "${YELLOW}⚠️ Note: You'll need to set PYTHONPATH each time you open a new terminal:${NC}"
echo -e "${YELLOW}   export PYTHONPATH=$project_path${NC}"

# Verify imports
echo -e "\n${BLUE}Verifying imports...${NC}"
$PYTHON_CMD verify_imports.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to verify imports.${NC}"
    echo -e "${YELLOW}Please check the error messages and fix any issues.${NC}"
else
    echo -e "${GREEN}✅ All imports verified successfully${NC}"
fi

echo
echo -e "${BLUE}=======================================================${NC}"
echo -e "${GREEN}Environment setup complete!${NC}"
echo -e "${BLUE}=======================================================${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit the .env file to set your API keys"
echo "2. Run validation tests:"
echo "   $PYTHON_CMD verify_imports.py"
echo "3. If you have access to OpenAI Agent SDK, run full validation:"
echo "   ./scripts/validate_refactored.sh workspace1 your-story-id enhance"
echo
echo -e "${YELLOW}To activate this environment in the future:${NC}"
echo "source agent_venv/bin/activate"
echo "export PYTHONPATH=$project_path"
echo 
echo -e "${BLUE}Happy testing!${NC}"