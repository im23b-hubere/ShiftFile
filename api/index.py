from backend.app import app

# Vercel Handler
def handler(request, context):
    return app(request) 