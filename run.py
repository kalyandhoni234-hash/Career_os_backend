from flask_migrate import upgrade
from app import create_app

app = create_app()

with app.app_context():
    try:
        upgrade()
    except Exception as e:
        print(f"Migration on startup failed (may already be up to date): {e}")

if __name__ == "__main__":
    import os

    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug, port=5001)
