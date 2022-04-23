import hashlib
import hmac

def hmac_sha512(message_k):
    return hmac.new(key=b'bip-entropy-from-k', msg=message_k, digestmod=hashlib.sha512).digest()


