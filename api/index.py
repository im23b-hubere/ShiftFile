from flask import Flask, request
from backend.app import app as flask_app

def handler(request):
    """Handle incoming requests."""
    with flask_app.request_context(request):
        return flask_app.full_dispatch_request() 