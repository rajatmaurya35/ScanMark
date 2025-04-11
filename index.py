from app import app

# This is for Vercel serverless deployment
def handler(request):
    """Handle incoming HTTP requests."""
    with app.test_client() as test_client:
        response = test_client.open(
            path=request.get('path', '/'),
            method=request.get('method', 'GET'),
            headers=request.get('headers', {}),
            data=request.get('body', '')
        )
        return {
            'statusCode': response.status_code,
            'headers': dict(response.headers),
            'body': response.get_data(as_text=True)
        }
