# Shortcut Enhancement System

An agent-based system that automatically improves Shortcut stories based on tags.

## Features

- **Full Enhancement**: Automatically enhances stories tagged with "enhance"
- **Analysis Only**: Analyzes stories tagged with "analyse" and adds results as comments
- **LLM-Driven**: Uses OpenAI Agent SDK for intelligent enhancement

## Local Development Setup

1. Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/shortcut-agent-openai.git
cd shortcut-agent-openai
pip install -r requirements.txt
```

2. Create a `.env.local` file with your API keys:

```bash
cp .env.example .env.local
# Edit .env.local to add your API keys
```

3. Run the local development server:

```bash
vercel dev
```

4. Testing the system:

```bash
# Test the enhancement pipeline
python main.py --test --workspace workspace1 --story 12345 --type enhance

# Simulate a webhook event
python main.py --simulate --workspace workspace1 --story 12345 --type enhance
```

## Webhook Integration

To use the system with Shortcut:

1. Deploy to Vercel:

```bash
vercel --prod
```

2. Configure a webhook in Shortcut pointing to:

```
https://your-app.vercel.app/api/webhook/{workspace_id}
```

3. Set the webhook to trigger on story updates (specifically label changes)

4. Tag stories with "enhance" or "analyse" to trigger the system

## Configuration

The system supports different configurations for development and production:

- Development mode uses local storage and faster/cheaper models
- Production mode uses Vercel KV for storage and more powerful models

Environment variables can be set in `.env.local` for development or in Vercel for production.

## Project Structure

```
/
├── api/                  # API endpoints
│   ├── webhook/          # Webhook handlers
│   └── test_pipeline.py  # Test endpoint
├── agents/               # Agent definitions
│   └── triage/           # Triage agent
├── context/              # Context objects
│   └── workspace/        # Workspace context
├── tools/                # Function tools
│   └── shortcut/         # Shortcut API tools
├── utils/                # Utilities
│   └── storage/          # Storage utilities
├── config/               # Configuration
│   ├── development.py    # Development config
│   └── production.py     # Production config
├── main.py               # Local development entry point
├── requirements.txt      # Python dependencies
└── vercel.json           # Vercel configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT