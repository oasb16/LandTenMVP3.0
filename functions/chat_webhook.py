def handler(event, context=None):
    message = event.get('message', '')
    print(f'Webhook received message: {message}')
    return {'status': 'ok'}
