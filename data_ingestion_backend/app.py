from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger

from api import api_bp

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://127.0.0.1:5500", "http://localhost:5500", "https://data-ingestion-processing-api.vercel.app"]
        }
    },
    allow_headers=["Content-Type", "X-API-Key"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["Content-Type"]
)

# ============================================================
# Swagger Configuration
# ============================================================

swagger_template = {
    "swagger": "2.0",

    "info": {
        "title": "Data Ingestion & Processing REST API",
        "description": (
            "REST API for data ingestion, validation, CSV upload, "
            "batch ingestion and ETL processing."
        ),
        "version": "1.0.0",
        "termsOfService": "/tos"
    },

    "basePath": "/",

    "schemes": [
        "http",
        "https"
    ],

    # ========================================================
    # API KEY SECURITY
    # ========================================================

    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "X-API-Key",
            "in": "header",
            "description": "Enter your API key here."
        }
    },

    "tags": [
        {
            "name": "General",
            "description": "General API information and health check"
        },
        {
            "name": "Data Ingestion",
            "description": "Single, batch and CSV data ingestion"
        },
        {
            "name": "API Logs",
            "description": "API request logs"
        },
        {
            "name": "ETL Processing",
            "description": "Data processing and transformation"
        }
    ]
}

# Create Swagger
swagger = Swagger(
    app,
    template=swagger_template
)

# Register API Blueprint
app.register_blueprint(api_bp)


# ============================================================
# ROOT
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API",
        "api_base_url": "/api"
    })


# ============================================================
# TERMS OF SERVICE
# ============================================================

@app.route("/tos")
def terms_of_service():
    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API Terms of Service"
    })


# ============================================================
# 404 ERROR
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error_code": 404,
        "message": "API endpoint not found",
        "path": request.path,
        "method": request.method
    }), 404


# ============================================================
# 405 ERROR
# ============================================================

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "success": False,
        "error_code": 405,
        "message": "HTTP method not allowed for this endpoint",
        "path": request.path,
        "method": request.method
    }), 405


# ============================================================
# 500 ERROR
# ============================================================

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error_code": 500,
        "message": "Internal server error",
        "path": request.path,
        "method": request.method
    }), 500


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("DATA INGESTION & PROCESSING REST API")
    print("Local URL : http://127.0.0.1:5000")
    print("Swagger   : http://127.0.0.1:5000/apidocs/")
    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
