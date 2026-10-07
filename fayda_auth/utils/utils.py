import base64
import hashlib
import secrets
from jwcrypto import jwk, jwt
import time

def fayda_unique_code_verifier_generator() -> str:
    """Generate a URL-safe base64-encoded code verifier."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

def fayda_unique_code_challenge_generator(verifier: str) -> str:
    """Generate a code challenge from a verifier using SHA-256."""
    hash_obj = hashlib.sha256(verifier.encode('utf-8'))
    return base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8').rstrip('=')

def fayda_client_assertion_secret_generator(client_id: str, token_url: str, private_key: str) -> str:
    """
    Generate a client assertion JWT using a JWK private key.

    Args:
        client_id: The OAuth client ID.
        token_url: The token endpoint URL.
        private_key: Base64-encoded JWK private key.

    Returns:
        A signed JWT string.
    """
    # Decode base64-encoded JWK
    try:
        jwk_data = base64.b64decode(private_key)
        key = jwk.JWK.from_json(jwk_data.decode('utf-8'))
        if key.key_type != 'RSA':  # Ensure RSA for RS256
            raise ValueError("Only RSA keys are supported")
    except Exception as e:
        raise ValueError(f"Failed to parse JWK private key: {str(e)}")

    # Generate JWT claims
    claims = {
        "iss": client_id,
        "aud": token_url,
        "sub": client_id,
        "exp": int(time.time()) + 5 * 60,  # 5 minutes
        "iat": int(time.time())
    }

    # Create and sign JWT
    token = jwt.JWT(header={"alg": "RS256"}, claims=claims)
    token.make_signed_token(key)
    return token.serialize()