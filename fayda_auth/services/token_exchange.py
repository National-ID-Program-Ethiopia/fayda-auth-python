import requests
import logging
from ..utils.utils import fayda_client_assertion_secret_generator

def fayda_oauth_get_token(auth_code: str, redirect_uri: str, code_verifier: str, token_url: str, client_id: str, client_assertion_type: str, private_key: str, session: requests.Session = None) -> dict:
    client_assertion = fayda_client_assertion_secret_generator(client_id, token_url, private_key)
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_assertion_type": client_assertion_type,
        "client_assertion": client_assertion,
        "code_verifier": code_verifier
    }
    
    http = session or requests
    response = http.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if response.status_code != 200:
        logging.error(f"Token request failed: {response.text}")
        raise Exception(f"Unexpected status code: {response.status_code}")
    
    return response.json()