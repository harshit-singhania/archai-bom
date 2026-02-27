"""Flask main application entry point."""

from flask import Flask, jsonify
from flask_cors import CORS

from app.api.routes import api_bp
from app.core.config import settings

app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY or "dev-secret-key"

# Enable CORS
CORS(app)

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
