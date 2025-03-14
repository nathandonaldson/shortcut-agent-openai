"""
Development-specific configuration.
"""

config = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "password": "",
    },
    "models": {
        "triage": "gpt-4o-mini",
        "analysis": "gpt-4o-mini",
        "generation": "gpt-4o-mini",
        "update": "gpt-4o-mini",
        "comment": "gpt-4o-mini",
        "notification": "gpt-4o-mini",
    },
    "log_level": "DEBUG",
    "timeout": 30,  # Longer timeouts for development
    "webhook_base_url": "http://localhost:3000/api/webhook",
    
    # Feature flags for development
    "feature_flags": {
        "use_notification": True,
        "enable_analytics": False,
        "use_claude": False
    }
}