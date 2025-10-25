import hmac
import hashlib


def verify_stream_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verify Stream webhook signature.

    Parameters
    ----------
    body : bytes
        Raw HTTP body from request.
    signature : str
        Hex-encoded signature from Stream header `X-Signature`.
    secret : str
        Stream Chat API secret used to compute HMAC.
    """
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
