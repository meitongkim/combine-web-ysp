import os
import sys

# Add parent (root) directory to Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

startup_error = None
tb_str = ""

try:
    # Try importing the main app.py file from root
    from app import app
except Exception as e:
    import traceback
    startup_error = e
    tb_str = traceback.format_exc()
    print(f"Diagnostics: Failed to import app: {tb_str}")

if startup_error is not None:
    # If import failed, fallback to a diagnostics app
    try:
        from flask import Flask
        app = Flask(__name__)
    except Exception:
        # Fallback to raw WSGI application if Flask is not installed
        def app(environ, start_response):
            status = '500 Internal Server Error'
            headers = [('Content-type', 'text/html; charset=utf-8')]
            start_response(status, headers)
            return [f"""
            <html>
                <head><title>Startup / Dependency Error</title></head>
                <body style="font-family: monospace; padding: 40px; background: #fff5f5; color: #9b2c2c;">
                    <h1>Critical Startup Error</h1>
                    <p>The Flask application failed to import. Flask or other required packages might not be installed:</p>
                    <pre style="background: #fff; border: 1px solid #feb2b2; padding: 15px; border-radius: 5px; overflow-x: auto;">{tb_str}</pre>
                </body>
            </html>
            """.encode('utf-8')]
    else:
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def catch_all(path):
            return f"""
            <html>
                <head>
                    <title>Startup / Dependency Error</title>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; background: #fff5f5; color: #2d3748; line-height: 1.6; }}
                        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1); border-top: 4px solid #e53e3e; }}
                        h1 {{ color: #c53030; margin-top: 0; font-size: 24px; }}
                        p {{ color: #4a5568; margin-bottom: 20px; }}
                        pre {{ background: #f7fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 6px; overflow-x: auto; font-family: SFMono-Regular, Consolas, Monaco, monospace; font-size: 14px; color: #4a5568; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Application Crash during Import</h1>
                        <p>The Flask application encountered an error while importing packages or initializing the environment:</p>
                        <pre>{tb_str}</pre>
                    </div>
                </body>
            </html>
            """, 500
