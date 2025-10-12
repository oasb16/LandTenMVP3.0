def handler(event, context=None):
    message = event.get('message', '')
    return {'response': f'AI agent received: {message}'}
