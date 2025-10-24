import os
from pusher import Pusher

_pusher_client = None


def get_pusher_client() -> Pusher:
    global _pusher_client
    if _pusher_client is None:
        app_id = os.getenv("PUSHER_APP_ID", "2062969")
        key = os.getenv("PUSHER_KEY", "2178d446fd16f6575323")
        secret = os.getenv("PUSHER_SECRET", "0672cb1dd96b90d4ba0b")
        cluster = os.getenv("PUSHER_CLUSTER", "us2")
        _pusher_client = Pusher(
            app_id=app_id,
            key=key,
            secret=secret,
            cluster=cluster,
            ssl=True,
        )
    return _pusher_client
