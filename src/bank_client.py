from config import settings, BANKS
from typing import Any

import logging
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
import ssl

import requests
import jwt as pyjwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_ORIGIN = "https://api.enablebanking.com"


# Error class for unhealthy API response
class SessionCreationError(Exception):
    """
    Raised when session setup fails.
    """

# Error class for invalid session details
class SessionLoadError(Exception):
    """
    Raised when the authorization session has expired.
    """

class SessionMissingError(Exception):
    """
    Raised when the session info JSON is missing.
    """

# Local listener
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        """Extract the OAuth authorization code from the redirect URL query string."""
        self.server.auth_code = parse_qs(
            urlparse(self.path).query
        )["code"][0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authentication successful, you can close this tab.")


def capture_auth_code() -> str:
    """
    Start a local HTTPS server on port 8000, handle a single OAuth redirect
    request, and return the extracted authorization code.
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(settings.ssl_cert_path, settings.ssl_key_path)

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

    server.auth_code = None
    server.handle_request()
    return server.auth_code


def jwt_gen() -> dict[str, str]:
    """
    Generate a signed RS256 JWT for the Enable Banking API and return it
    as an Authorization Bearer header dict ready to pass to requests calls.
    """
    iat = int(datetime.now().timestamp())
    jti = str(uuid.uuid4())
    jwt_body = {
        "iss": "settings.enable_banking_app_id",
        "aud": "api.enablebanking.com",
        "iat": iat,
        "exp": iat + 3600,
        "jti": jti
    }
    token = pyjwt.encode(
        jwt_body,
        open(settings.enable_banking_key_path, "rb").read(),
        algorithm="RS256",
        headers={"kid": settings.enable_banking_app_id},
    )

    base_headers = {"Authorization": f"Bearer {token}"}

    return base_headers


def request_details(base_headers: dict[str, str]) -> dict | None:
    """Return the Enable Banking application details, or None on failure."""
    r = requests.get(f"{API_ORIGIN}/application", headers=base_headers)
    if r.status_code == 200:
        app = r.json()
        logger.info("Application details captured successfully.")
        return app
    else:
        logger.error("Error in capturing application details. Status: %s", r.status_code)
        return None


def request_aspsps(base_headers: dict[str, str]) -> list | None:
    """Return the list of available ASPSPs from the API, or None on failure."""
    r = requests.get(f"{API_ORIGIN}/aspsps", headers=base_headers)
    if r.status_code == 200:
        logger.info("List of ASPSPs captured successfully.")
        return r.json()["aspsps"]
    else:
        logger.error("Error while capturing ASPSP list. Status: %s", r.status_code)
        return None


def authorization(base_headers: dict[str, str], name: str, country: str) -> str | None:
    """
    Initiate an OAuth authorization flow for a given bank and return the
    URL the user must visit to authenticate, or None on failure.
    """
    body = {
        "access": {
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=180)).isoformat(),
            "balances": True,
            "transactions": True,
        },
        "aspsp": {"name": name, "country": country},
        "state": str(uuid.uuid4()),
        "redirect_url": settings.redirect_url,
        "psu_type": "personal",
    }
    r = requests.post(f"{API_ORIGIN}/auth", json=body, headers=base_headers)
    if r.status_code == 200:
        auth_url = r.json()["url"]
        logger.info("Successful initialization. To authenticate, open URL: %s", auth_url)
        return auth_url
    else:
        logger.error("Failed authorization. Status: %s", r.status_code)
        return None


def create_session(base_headers: dict[str, str]) -> dict | None:
    """
    Exchange the OAuth authorization code captured from the local redirect
    listener for a new Enable Banking session. Returns the session dict on
    success, or None on failure.
    """
    auth_code = capture_auth_code()
    r = requests.post(f"{API_ORIGIN}/sessions", json={"code": auth_code}, headers=base_headers)
    if r.status_code == 200:
        session = r.json()
        logger.info("New session has been created.")
        return session
    else:
        logger.error("Error while creating new session. Status: %s", r.status_code)
        return None


def ensure(result: Any, step: str) -> Any:
    """
    Validate a step result.

    Raises SessionCreationError if result is None; otherwise returns result unchanged.
    """
    if result is None:
        raise SessionCreationError(f"{step} failed")
    return result


def save_session(session: dict, name: str) -> None:
    """Persist a session dict to the sessions JSON file under the given bank name."""
    sessions: dict = {}

    try:
        with open(settings.sessions_info_path, "r") as f:
            sessions = json.load(f)
    except FileNotFoundError:
        pass

    sessions[name] = session

    try:
        with open(settings.sessions_info_path, "w") as f:
            json.dump(sessions, f, indent=2)
        logger.info("Session saved successfully.")
    except OSError as e:
        logger.error("Failed to save session: %s", e)
        raise


def load_session(name: str) -> dict:
    """
    Load the saved session for the given bank from disk and verify it has
    not expired.

    Raises:
        SessionMissingError: if the sessions file is missing, malformed, or
                             does not contain an entry for the given bank.
        SessionLoadError: if the session's valid_until timestamp is in the past.
    """
    try:
        with open(settings.sessions_info_path, "r") as f:
            sessions_info = json.load(f)

        session_info = sessions_info[name]
        valid_until = session_info['access']['valid_until']

        if datetime.now(timezone.utc) < datetime.fromisoformat(valid_until):
            logger.info("Session has been successfully loaded.")
            return session_info
        else:
            raise SessionLoadError("Session load failed")

    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        raise SessionMissingError("session.json is missing, empty, or bank not found")


def initialize_session(name: str, country: str) -> dict | None:
    """
    Return a valid session for the given bank, creating one via the full
    OAuth flow if no unexpired session exists on disk.

    Returns the session dict on success, or None if session creation failed.
    """
    try:
        session_info = load_session(name)
        if session_info:
            return session_info

    except(SessionMissingError, SessionLoadError):
        try:
            headers = jwt_gen()

            ensure(headers, "Private key")
            ensure(request_details(headers), "Request details")
            ensure(request_aspsps(headers), "ASPSPs request")
            ensure(authorization(headers, name, country), "Authorization")

            session = ensure(
                create_session(headers),
                "Session creation"
            )

            logger.info("Session initialized successfully")

            save_session(session, name)

            return session

        except SessionCreationError as e:
            logger.error("Initialization failed: %s", e)
            return None

        except Exception:
            logger.exception("Unexpected error during initialization")
            raise


def main() -> int:
    """Initialize sessions for all configured banks and return 0 on success, 1 on failure."""
    for bank in BANKS.keys():
        session = initialize_session(name=bank, country="HU")
        if session is None:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
