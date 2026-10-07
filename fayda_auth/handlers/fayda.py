import requests
from typing import Dict, Any
from ..utils.responses import SuccessResponse, ErrorResponse
from ..utils.utils import fayda_unique_code_verifier_generator, fayda_unique_code_challenge_generator
from ..utils.random import generate_random_string, random_csrf_token_generator
from ..utils.validators import validate
from ..services.token_exchange import fayda_oauth_get_token
from ..services.user_info import fetch_user_info_from_fayda
from ..exceptions import FaydaAuthError
from ..config.hosts import HostConfigManager

class FaydaOAuthHandler:
    def __init__(self, redis_client, client_id: str, authorize_url: str, token_url: str, user_info_url: str, private_key: str, client_assertion_type: str):
        self.redis = redis_client
        self.client_id = client_id
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.user_info_url = user_info_url
        self.private_key = private_key
        self.client_assertion_type = client_assertion_type
        self.http_client = requests.Session()

    def authorize(self, host_manager: HostConfigManager, request_origin: str, request_referer: str = "") -> Dict[str, str]:
        redirect_uri = host_manager.get_redirect_uri(request_origin)
        if not redirect_uri:
            raise FaydaAuthError(f"Invalid origin: {request_origin}", 400)

        state_csrf_token = random_csrf_token_generator()
        code_verifier = fayda_unique_code_verifier_generator()
        challenge = fayda_unique_code_challenge_generator(code_verifier)

        session_id = generate_random_string(32)
        session_data = {
            "csrf_token": state_csrf_token,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri
        }
        self.redis.hmset(session_id, session_data)
        self.redis.expire(session_id, 15 * 60)

        auth_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "openid profile email",
            "state": state_csrf_token
        }
        auth_url = f"{self.authorize_url}?{'&'.join(f'{k}={v}' for k, v in auth_params.items())}"

        return SuccessResponse("Redirecting to Fayda Esignet", {
            "auth_url": auth_url,
            "session_id": session_id,
            "utm_referer": request_referer,
            "utm_source": request_origin
        }, 200).__dict__()

    def authenticate(self, session_id: str, auth_code: str, csrf_token: str) -> Dict[str, Any]:
        request_body = {"session_id": session_id, "auth_code": auth_code, "csrf_token": csrf_token}
        errors = validate(request_body, AuthRequest)
        if errors:
            raise FaydaAuthError(", ".join(errors), 400)

        session_data = self.redis.hgetall(session_id)
        if not session_data:
            raise FaydaAuthError("Invalid or expired session", 401)

        stored_csrf = session_data[b'csrf_token'].decode('utf-8')
        if stored_csrf != csrf_token:
            raise FaydaAuthError("Invalid CSRF token", 401)

        token_data = fayda_oauth_get_token(
            auth_code,
            session_data[b'redirect_uri'].decode('utf-8'),
            session_data[b'code_verifier'].decode('utf-8'),
            self.token_url,
            self.client_id,
            self.client_assertion_type,
            self.private_key,
            session=self.http_client
        )
        user_info = fetch_user_info_from_fayda(
            token_data['access_token'], 
            self.user_info_url,
            session=self.http_client
        )

        return SuccessResponse("User authenticated successfully", user_info, 200).__dict__()

class AuthRequest:
    def __init__(self, session_id, auth_code, csrf_token):
        self.session_id = session_id
        self.auth_code = auth_code
        self.csrf_token = csrf_token