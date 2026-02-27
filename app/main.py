"""Flask main application entry point."""

import time
from functools import wraps

from flask import Flask, jsonify, request
from flask_cors import CORS

from app.api.routes import api_bp
from app.core.config import settings

app = Flask(__name__)

# Production startup guard: fail fast without explicit SECRET_KEY
if not settings.DEBUG and not settings.SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY must be set explicitly in production. "
        "Set it in your .env file or environment variables."
    )

app.config["SECRET_KEY"] = settings.SECRET_KEY or "dev-secret-key"
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

# Configure CORS with explicit origin allowlist
allowed_origins = (
    settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else "*"
)
CORS(app, origins=allowed_origins)

# Simple in-memory rate limiter storage
_rate_limit_store = {}


def rate_limit(max_requests=10, window_seconds=60):
    """Rate limiting decorator for expensive API endpoints."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Skip rate limiting in DEBUG mode or if no auth key configured
            if settings.DEBUG or not settings.API_AUTH_KEY:
                return f(*args, **kwargs)

            # Get client identifier (API key or IP address)
            client_id = request.headers.get("X-API-Key", request.remote_addr)
            now = time.time()
            key = f"{client_id}:{f.__name__}"

            # Clean old entries and check current count
            if key in _rate_limit_store:
                _rate_limit_store[key] = [
                    ts for ts in _rate_limit_store[key] if now - ts < window_seconds
                ]
                if len(_rate_limit_store[key]) >= max_requests:
                    return jsonify(
                        {"error": "Rate limit exceeded. Try again later."}
                    ), 429
            else:
                _rate_limit_store[key] = []

            _rate_limit_store[key].append(now)
            return f(*args, **kwargs)

        return wrapped

    return decorator


def require_api_key():
    """Check API key for protected routes."""
    # Skip auth in DEBUG mode if no key configured
    if settings.DEBUG and not settings.API_AUTH_KEY:
        return None

    # If API_AUTH_KEY is configured, require it
    if settings.API_AUTH_KEY:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"error": "API key required. Set X-API-Key header."}), 401
        if api_key != settings.API_AUTH_KEY:
            return jsonify({"error": "Invalid API key."}), 401

    return None


@app.before_request
def check_auth():
    """Apply API key check to protected routes."""
    # Skip auth for public endpoints
    if request.endpoint in ["health_check", "root"]:
        return None

    # Only check auth for API routes
    if request.path.startswith(settings.API_V1_PREFIX):
        return require_api_key()

    return None


# Register blueprints
app.register_blueprint(api_bp, url_prefix=settings.API_V1_PREFIX)


@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "version": settings.VERSION})


@app.route("/")
def root():
    """Root endpoint."""
    return jsonify(
        {"message": "Welcome to ArchAI BOM API", "version": settings.VERSION}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=settings.DEBUG)
