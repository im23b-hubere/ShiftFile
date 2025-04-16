from backend.app import app
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

# WSGI-Middleware hinzufügen
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Vercel Handler
def handler(request):
    """Handle Vercel serverless function requests."""
    return app 