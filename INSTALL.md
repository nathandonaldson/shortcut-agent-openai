# Installation Guide

## Requirements

- Python 3.9 or higher
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)

## Steps to install the OpenAI Agents SDK

1. Install the OpenAI Agents SDK:

```bash
pip install openai-agents
```

2. Verify the installation:

```bash
python check_sdk.py
```

If the OpenAI Agents SDK is not installed, you'll see a message that it's not available. The output should show both the OpenAI API package and the OpenAI Agents SDK as available if everything is installed correctly.

## Troubleshooting

If you encounter errors related to missing modules or classes:

- Make sure you have the latest version of the OpenAI Agents SDK:
  ```bash
  pip install openai-agents --upgrade
  ```

- If you're using a virtual environment, make sure it's activated:
  ```bash
  source .venv/bin/activate  # On macOS/Linux
  ```

- Check that your Python environment matches the one used by your scripts:
  ```bash
  which python
  python --version
  ```

- Try installing with pip3 instead:
  ```bash
  pip3 install openai-agents
  ```

## Environment Variables

Make sure to set the following environment variables:

```bash
export OPENAI_API_KEY=sk-your-openai-api-key
```

For development, you may also want to set:

```bash
export USE_BACKGROUND_PROCESSING=false  # Process webhooks inline for easier debugging
```
