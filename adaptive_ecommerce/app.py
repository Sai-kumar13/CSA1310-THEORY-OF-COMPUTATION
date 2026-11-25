"""
Adaptive E-Commerce Search and Personalized Product Recommendation System
==========================================================================
Main Flask application entry point.

Theory of Computation Capstone Project
Demonstrates: DFA, NFA, Regular Expressions, Pattern Matching, State Transitions

Run: python app.py
URL: http://127.0.0.1:5000/
"""

from flask import Flask
from config import Config
from backend.routes import api, init_engines


def create_app():
    app = Flask(
        __name__,
        template_folder='frontend/templates',
        static_folder='frontend/static'
    )
    app.config.from_object(Config)

    # Initialize backend engines with database config
    init_engines(Config)

    # Register the API blueprint
    app.register_blueprint(api)

    return app


if __name__ == '__main__':
    app = create_app()
    print("=" * 60)
    print("  AdaptiveShop - E-Commerce Search & Recommendation System")
    print("  Theory of Computation Capstone Project")
    print("=" * 60)
    print(f"  Database: {Config.MYSQL_DATABASE}")
    print(f"  Server:   http://127.0.0.1:5000/")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=5000)
