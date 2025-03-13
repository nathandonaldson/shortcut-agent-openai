# Shortcut Enhancement System

An intelligent, agent-based system that automatically improves Shortcut stories based on tags. The system supports dual workflows for enhancement and analysis.

## Deployment URLs

- **Production**: [shortcut-agent-openai.vercel.app](https://shortcut-agent-openai.vercel.app)
- **Development**: [kangaroo-superb-cheaply.ngrok-free.app](https://kangaroo-superb-cheaply.ngrok-free.app)

## Features

- **Full Enhancement Workflow**: Automatically enhances stories tagged with "enhance", changing the tag to "enhanced" when complete
- **Analysis-Only Workflow**: Analyzes stories tagged with "analyse" and adds results as comments, changing the tag to "analysed"
- **LLM-Driven Orchestration**: Uses OpenAI Agent SDK for intelligent, dynamic agent handoffs based on contextual reasoning
- **Environment-Aware Configuration**: Automatically switches between development and production settings

## Architecture

The system uses a pure LLM-driven orchestration approach where:

- Each agent has access to all other agents through handoffs
- Agents independently decide when to hand off based on their reasoning
- The flow is completely dynamic, determined by the LLMs at runtime
- No hardcoded decision trees or explicit agent chaining in code

### Agent Composition

1. **Triage Agent**: Evaluates incoming webhooks and determines the appropriate workflow
2. **Analysis Agent**: Analyzes story quality and identifies improvement areas
3. **Generation Agent**: Creates enhanced content based on analysis results
4. **Update Agent**: Applies enhancements back to Shortcut
5. **Comment Agent**: Adds analysis results as comments without modifying content
6. **Notification Agent**: Informs stakeholders about enhancements or analysis

## Local Development Setup

1. Clone the repository and run the setup script:

```bash
git clone https://github.com/nathandonaldson/shortcut-agent-openai.git
cd shortcut-agent-openai
python scripts/setup.py
```

2. Create a `.env.local` file with your API keys:

```bash
cp .env.example .env.local
# Edit .env.local to add your API keys
```

3. Start Redis using Docker:

```bash
docker-compose up -d
```

4. Run the local development server:

```bash
vercel dev
```

## Testing Webhooks

### Option 1: Using ngrok (recommended)

```bash
# Start the webhook test server and ngrok in one command
./scripts/start_webhook_server.sh

# In another terminal, simulate a webhook event
python scripts/simulate_webhook.py --workspace workspace1 --action update --label enhance
```

### Option 2: Using localtunnel

```bash
# Start your server
python scripts/test_webhooks.py

# In another terminal, start localtunnel
lt --port 3000 --subdomain shortcut-enhancement

# Then simulate a webhook event
python scripts/simulate_webhook.py --workspace workspace1 --action update --label enhance --url https://shortcut-enhancement.loca.lt
```

## Setting Up Webhooks in Shortcut

```bash
# Configure webhooks automatically
python scripts/setup_webhooks.py

# Configure webhooks for a specific workspace
python scripts/setup_webhooks.py --workspace workspace1
```

## Model Configuration

Each agent can use a different model based on its requirements:

**Development Configuration (Default):**
- Triage Agent: `o3-mini` (fastest/cheapest for initial screening)
- Analysis Agent: `o3-mini` (for development speed)
- Generation Agent: `o3-mini` (for development speed)
- Update Agent: `o3-mini` (for simple task execution)
- Comment Agent: `o3-mini` (for formatting analysis as comments)
- Notification Agent: `o3-mini` (for simple message creation)

**Production Configuration:**
- Triage Agent: `gpt-3.5-turbo` (good balance of speed/capability)
- Analysis Agent: `gpt-4o` (sophisticated analysis needs)
- Generation Agent: `gpt-4o` (complex content creation)
- Update Agent: `gpt-3.5-turbo` (straightforward task execution)
- Comment Agent: `gpt-3.5-turbo` (formatting and comment creation)
- Notification Agent: `gpt-3.5-turbo` (message creation)

## Switching Environments

Toggle between development and production mode:

```bash
python scripts/toggle_mode.py development
# or
python scripts/toggle_mode.py production
```

## Project Structure

```
/
├── api/
│   ├── webhook/
│   │   └── [workspace].py        # Webhook receiver with workspace path param
│   ├── process_task.py           # Background processor for agent execution
│   └── test_pipeline.py          # End-to-end test endpoint
├── agents/
│   ├── triage/                   # Triage agent with workflow selection
│   └── ...                       # Other agent implementations
├── tools/
│   ├── shortcut/                 # Function tools for Shortcut API
│   └── ...                       # Other tool implementations
├── context/
│   └── workspace/                # Workspace context definitions
├── prompts/                      # Agent prompts
├── utils/
│   ├── storage/                  # Storage utilities
│   └── ...                       # Other utilities
├── config/
│   ├── development/              # Development environment config
│   ├── production/               # Production environment config
│   ├── development.py            # Development settings
│   └── production.py             # Production settings
├── guardrails/                   # Input/output validation
├── lifecycle/                    # Agent lifecycle hooks
├── tracing/                      # Tracing and monitoring
├── scripts/
│   ├── test_webhooks.py          # Webhook testing server
│   ├── simulate_webhook.py       # Webhook simulation tool
│   ├── start_webhook_server.sh   # Script to start server with ngrok
│   ├── setup_webhooks.py         # Configure Shortcut webhooks
│   ├── seed_test_data.py         # Seed test data in Shortcut
│   ├── setup.py                  # Project setup script
│   └── toggle_mode.py            # Toggle between dev and prod modes
├── tests/
│   ├── mocks/                    # Mock data for testing
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── main.py                       # Local development entry point
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker configuration
└── vercel.json                   # Vercel configuration
```

## Deployment to Production

1. Run the deployment checklist:

```bash
cat DEPLOYMENT_CHECKLIST.md
```

2. Deploy to Vercel:

```bash
vercel --prod
```

3. Configure Vercel KV and environment variables in the Vercel dashboard.

4. Set up production webhooks:

```
URL: https://shortcut-agent-openai.vercel.app/api/webhook/{workspace_id}
Events: Story updates (specifically label changes)
```

## Detailed Documentation

For more comprehensive documentation, see the `claude.md` file in the repository, which contains detailed implementation notes, architectural decisions, and best practices.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT