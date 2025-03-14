"""
Production-specific configuration.
"""

config = {
    "redis": {
        "url": None,  # Will use Vercel KV REST API
        "token": None,  # Will use Vercel KV REST API
    },
    "models": {
        "triage": "gpt-4o-mini",
        "analysis": "gpt-4o",
        "generation": "gpt-4o",
        "update": "gpt-4o-mini",
        "comment": "gpt-4o-mini",
        "notification": "gpt-4o-mini",
    },
    "log_level": "INFO",
    "timeout": 10,  # Shorter timeouts for production
    "webhook_base_url": "https://your-app.vercel.app/api/webhook",
    
    # Feature flags for production
    "feature_flags": {
        "use_notification": True,
        "enable_analytics": True,
        "use_claude": False
    }
}