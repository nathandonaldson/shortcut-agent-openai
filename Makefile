.PHONY: deploy test-analysis test-webhook start-webhook deploy-prod

# Deploy to development environment
deploy:
	vercel deploy

# Deploy to production environment
deploy-prod:
	vercel deploy --prod

# Test Analysis Agent with test story
test-analysis:
	python agents/analysis/cli.py --workspace test --test tests/mocks/test_story.json

# Test specific story analysis
analyze-story:
	python agents/analysis/cli.py --workspace $(WORKSPACE) analyze $(STORY_ID)

# Start webhook test server
start-webhook:
	./scripts/start_webhook_server.sh

# Test webhook processing
test-webhook:
	python scripts/simulate_webhook.py --workspace test --action update --label enhance

# Install dependencies
install:
	pip install -r requirements.txt