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
        "triage": "gpt-3.5-turbo",
        "analysis": "gpt-3.5-turbo",
        "generation": "gpt-3.5-turbo",
        "update": "gpt-3.5-turbo",
        "comment": "gpt-3.5-turbo",
        "notification": "gpt-3.5-turbo",
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