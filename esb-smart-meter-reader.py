#!/usr/bin/env python3
"""Download smart electricity meter readings from the ESB Networks customer portal.

Configuration is read from a ".env" file (see ".env.example"). Output goes to
stdout — redirect with the shell to save to a file:

    uv run esb-smart-meter-reader.py > readings.json
    uv run esb-smart-meter-reader.py --format csv > readings.csv

Set LOG_LEVEL=DEBUG in ".env" for a verbose per-request trace.
"""

import argparse
import csv
import io
import json
import logging
import os
import re
from dataclasses import dataclass
from random import randint
from time import sleep

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logger = logging.getLogger("esb_meter_reader")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) "
    "Gecko/20100101 Firefox/142.0"
)
ALLOWED_OUTPUT_FORMATS = ("json", "csv")

# B2C tenant / policy identifiers used throughout the login flow.
B2C_TENANT = "esbntwkscustportalprdb2c01.onmicrosoft.com"
B2C_POLICY = "B2C_1A_signup_signin"
LOGIN_BASE_URL = f"https://login.esbnetworks.ie/{B2C_TENANT}/{B2C_POLICY}"
PORTAL_BASE_URL = "https://myaccount.esbnetworks.ie"


class LoginError(RuntimeError):
    """Raised when the portal blocks or rejects the login attempt."""


@dataclass
class EsbConfig:
    """Settings loaded from the environment / .env file."""

    username: str
    password: str
    mprn: str
    search_type: str
    user_agent: str
    log_level: str


def load_config() -> EsbConfig:
    """Load and validate configuration from environment variables."""
    load_dotenv()

    username = os.environ.get("ESB_USERNAME", "").strip()
    password = os.environ.get("ESB_PASSWORD", "").strip()
    mprn = os.environ.get("ESB_MPRN", "").strip()
    search_type = os.environ.get("ESB_SEARCH_TYPE", "intervalkwh").strip()
    user_agent = os.environ.get("ESB_USER_AGENT", "").strip() or DEFAULT_USER_AGENT
    log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()

    missing = [
        name
        for name, value in (
            ("ESB_USERNAME", username),
            ("ESB_PASSWORD", password),
            ("ESB_MPRN", mprn),
            ("ESB_SEARCH_TYPE", search_type),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "Missing required config: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in your values."
        )

    return EsbConfig(
        username=username,
        password=password,
        mprn=mprn,
        search_type=search_type,
        user_agent=user_agent,
        log_level=log_level,
    )


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download ESB smart meter readings.")
    parser.add_argument(
        "--format", choices=ALLOWED_OUTPUT_FORMATS, default="json",
        help="Output format: json (default) or csv",
    )
    return parser.parse_args()


def random_delay(min_seconds: int, max_seconds: int) -> None:
    """Sleep a random number of seconds to look less robotic to the server."""
    delay = randint(min_seconds, max_seconds)
    logger.debug("Random sleep for %s seconds...", delay)
    sleep(delay)


def build_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    return session


def fetch_login_settings(session: requests.Session) -> tuple[str, str]:
    """Request #1 -- GET the portal landing page and extract the B2C SETTINGS blob.

    Returns (csrf_token, transaction_id).
    """
    logger.debug("##### REQUEST 1 -- GET [%s/] ######", PORTAL_BASE_URL)
    try:
        # timeout -- 10s to connect, 5s to first byte
        response = session.get(
            f"{PORTAL_BASE_URL}/", allow_redirects=True, timeout=(10, 5)
        )
    except requests.exceptions.Timeout:
        raise LoginError(
            "The request timed out, server is not responding. Try again later."
        )
    except requests.exceptions.RequestException as exc:
        raise LoginError(f"An error occurred: {exc}")

    settings_match = re.findall(r"(?<=var SETTINGS = )\S*;", str(response.content))
    settings = json.loads(settings_match[0][:-1])
    csrf_token = settings["csrf"]
    transaction_id = settings["transId"]

    soup = BeautifulSoup(response.content, "html.parser")
    logger.debug("[!] Request #1 Page Title :: %s", soup.find("title").text)
    logger.debug("[!] Request #1 Status Code :: %s", response.status_code)
    logger.debug("[!] Request #1 Cookies :: %s", session.cookies.get_dict())
    logger.debug("csrf_token :: %s", csrf_token)
    logger.debug("transaction_id :: %s", transaction_id)

    return csrf_token, transaction_id


def submit_credentials(
    session: requests.Session,
    config: EsbConfig,
    csrf_token: str,
    transaction_id: str,
) -> None:
    """Request #2 -- POST credentials to the SelfAsserted endpoint."""
    logger.debug("##### REQUEST 2 -- POST [SelfAsserted] ######")
    cookies = session.cookies.get_dict()
    response = session.post(
        f"{LOGIN_BASE_URL}/SelfAsserted?tx={transaction_id}&p={B2C_POLICY}",
        data={
            "signInName": config.username,
            "password": config.password,
            "request_type": "RESPONSE",
        },
        headers={
            "x-csrf-token": csrf_token,
            "User-Agent": config.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://login.esbnetworks.ie",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Te": "trailers",
        },
        cookies={
            "x-ms-cpim-csrf": cookies.get("x-ms-cpim-csrf"),
            "x-ms-cpim-trans": cookies.get("x-ms-cpim-trans"),
        },
        allow_redirects=False,
    )
    logger.debug("[!] Request #2 Status Code :: %s", response.status_code)
    logger.debug("[!] Request #2 text :: %s", response.text)


@dataclass
class SigninForm:
    """Hidden form fields needed to complete the OIDC sign-in (request #4)."""

    login_url: str
    state: str
    client_info: str
    code: str


def confirm_signin(
    session: requests.Session, csrf_token: str, transaction_id: str
) -> SigninForm:
    """Request #3 -- confirm sign-in and extract the auto-post form fields.

    Also detects the portal's "too many retries" / human-verification responses.
    """
    logger.debug("##### REQUEST 3 -- GET [API CombinedSigninAndSignup] ######")
    cookies = session.cookies.get_dict()
    response = session.get(
        f"{LOGIN_BASE_URL}/api/CombinedSigninAndSignup/confirmed",
        params={
            "rememberMe": False,
            "csrf_token": csrf_token,
            "tx": transaction_id,
            "p": B2C_POLICY,
        },
        headers={
            "User-Agent": session.headers["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0, i",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Te": "trailers",
        },
        cookies={
            "x-ms-cpim-csrf": cookies.get("x-ms-cpim-csrf"),
            "x-ms-cpim-trans": cookies.get("x-ms-cpim-trans"),
        },
    )

    soup = BeautifulSoup(response.content, "html.parser")
    logger.debug("[!] Request #3 Status Code :: %s", response.status_code)
    logger.debug("[!] Request #3 Page Title :: %s", soup.find("title").text)

    # A genuine success page starts with a full HTML doctype; anything else is a
    # verification / blocked response.
    if not response.text.startswith("<!DOCTYPE html PUBLIC"):
        for selector in (("h1", {}), ("div", {"id": "no_js"}), ("div", {"id": "no_cookie"})):
            element = soup.find(selector[0], selector[1])
            if element:
                logger.error("[FAILED] Page response :: %s", element.text)
        raise LoginError(
            "Unable to reach login page -- too many retries (max=2 in 24h) or a prior "
            "session was not closed properly. Please try again after midnight."
        )

    logger.debug("[PASS] SUCCESS -- ALL OK")

    logger.debug("##### Extracting state & client_info & code ######")
    form = soup.find("form", {"id": "auto"})
    try:
        signin_form = SigninForm(
            login_url=form["action"],
            state=form.find("input", {"name": "state"})["value"],
            client_info=form.find("input", {"name": "client_info"})["value"],
            code=form.find("input", {"name": "code"})["value"],
        )
    except (TypeError, KeyError):
        raise LoginError(
            "Unable to get the required form fields -- too many retries (captcha?) or a "
            "prior session was not closed properly. Please wait 6 hours for the server "
            "to time out and try again."
        )

    logger.debug("login_url :: %s", signin_form.login_url)
    logger.debug("state :: %s", signin_form.state)
    logger.debug("client_info :: %s", signin_form.client_info)
    logger.debug("code :: %s", signin_form.code)
    return signin_form


def complete_oidc(
    session: requests.Session, user_agent: str, signin_form: SigninForm
) -> None:
    """Request #4 -- POST the form back to the signin-oidc endpoint."""
    logger.debug("##### REQUEST 4 -- POST [signin-oidc] ######")
    random_delay(2, 5)
    response = session.post(
        signin_form.login_url,
        allow_redirects=False,
        data={
            "state": signin_form.state,
            "client_info": signin_form.client_info,
            "code": signin_form.code,
        },
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://login.esbnetworks.ie",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Referer": "https://login.esbnetworks.ie/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Priority": "u=0, i",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Te": "trailers",
        },
    )
    logger.debug("[!] Request #4 Status Code :: %s", response.status_code)  # expect 302


def load_account_home(session: requests.Session, user_agent: str) -> None:
    """Request #5 -- GET the portal home page to confirm we are logged in."""
    logger.debug("##### REQUEST 5 -- GET [%s] ######", PORTAL_BASE_URL)
    cookies = session.cookies.get_dict()
    response = session.get(
        PORTAL_BASE_URL,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://login.esbnetworks.ie/",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Priority": "u=0, i",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Te": "trailers",
        },
        cookies={
            "ARRAffinity": cookies.get("ARRAffinity"),
            "ARRAffinitySameSite": cookies.get("ARRAffinitySameSite"),
        },
    )
    logger.debug("[!] Request #5 Status Code :: %s", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")
    logger.debug("[!] Page Title :: %s", soup.find("title").text)  # "Customer Portal"
    welcome = soup.find("h1", class_="esb-title-h1")
    if welcome:
        logger.debug("[!] Confirmed User Login :: %s", welcome.text)  # "Welcome, ..."


def open_consumption_page(session: requests.Session, user_agent: str) -> None:
    """Request #6 -- GET the Historic Consumption page (sets up the download)."""
    logger.debug("##### REQUEST 6 -- GET [Api/HistoricConsumption] ######")
    random_delay(3, 8)
    cookies = session.cookies.get_dict()
    response = session.get(
        f"{PORTAL_BASE_URL}/Api/HistoricConsumption",
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Referer": f"{PORTAL_BASE_URL}/",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Priority": "u=0, i",
            "Te": "trailers",
        },
        cookies={
            "ARRAffinity": cookies.get("ARRAffinity"),
            "ARRAffinitySameSite": cookies.get("ARRAffinitySameSite"),
            ".AspNetCore.Cookies": cookies.get(".AspNetCore.Cookies"),
        },
    )
    logger.debug("[!] Request #6 Status Code :: %s", response.status_code)
    soup = BeautifulSoup(response.text, "html.parser")
    logger.debug("[!] Page Title :: %s", soup.find("title").text)


def fetch_download_token(session: requests.Session, user_agent: str) -> str:
    """Request #7 -- GET the anti-forgery token required for the file download."""
    logger.debug("##### REQUEST 7 -- GET [file download token] ######")
    random_delay(2, 5)
    cookies = session.cookies.get_dict()
    response = session.get(
        f"{PORTAL_BASE_URL}/af/t",
        headers={
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Returnurl": f"{PORTAL_BASE_URL}/Api/HistoricConsumption",
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Referer": f"{PORTAL_BASE_URL}/Api/HistoricConsumption",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Te": "trailers",
        },
        cookies={
            "ARRAffinity": cookies.get("ARRAffinity"),
            "ARRAffinitySameSite": cookies.get("ARRAffinitySameSite"),
        },
    )
    download_token = json.loads(response.text)["token"]
    logger.debug("[!] Request #7 Status Code :: %s", response.status_code)
    logger.debug("Download token :: %s", download_token)
    return download_token


def download_readings(
    session: requests.Session,
    user_agent: str,
    mprn: str,
    search_type: str,
    download_token: str,
) -> requests.Response:
    """Request #8 -- POST to download the historic data file for the meter."""
    logger.debug("##### REQUEST 8 -- POST [/DataHub/DownloadHdfPeriodic] ######")
    response = session.post(
        f"{PORTAL_BASE_URL}/DataHub/DownloadHdfPeriodic",
        headers={
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{PORTAL_BASE_URL}/Api/HistoricConsumption",
            "Content-Type": "application/json",
            "X-Returnurl": f"{PORTAL_BASE_URL}/Api/HistoricConsumption",
            "X-Xsrf-Token": download_token,
            "Origin": PORTAL_BASE_URL,
            "Dnt": "1",
            "Sec-Gpc": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=4",
            "Cache-Control": "max-age=0",
            "Te": "trailers",
        },
        json={
            "mprn": mprn,
            "searchType": search_type,
        },
    )
    logger.debug("[!] Request #8 Status Code :: %s", response.status_code)
    return response


def parse_filename(response: requests.Response) -> str | None:
    """Extract the filename from the Content-Disposition header, if present."""
    disposition = response.headers.get("Content-Disposition")
    if not disposition:
        return None
    # e.g. "attachment; filename=HDF_kW_mprn_date.csv; filename*=UTF-8''..."
    parts = disposition.split(";")
    if len(parts) < 2 or "=" not in parts[1]:
        return None
    return parts[1].split("=")[1].strip()


def decode_payload(response: requests.Response) -> str:
    """Return the downloaded CSV payload as text."""
    content = response.content
    if isinstance(content, bytes):
        logger.debug("[!] Payload is bytes, decoding to utf-8...")
        return content.decode("utf-8")
    if isinstance(content, str):
        return content
    raise SystemExit(
        "[FAIL] Downloaded object is neither bytes nor str; "
        "please check the response from request #8."
    )


def csv_to_json(csv_text: str) -> str:
    """Convert the ESB CSV payload to a pretty-printed JSON string."""
    if not csv_text.startswith("MPRN"):
        raise SystemExit(
            "[FAIL] Unexpected CSV header; cannot convert to JSON "
            "(expected the file to start with 'MPRN')."
        )
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    return json.dumps(rows, indent=2)


def main() -> None:
    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)

    session = build_session(config.user_agent)
    try:
        csrf_token, transaction_id = fetch_login_settings(session)
        random_delay(10, 20)
        submit_credentials(session, config, csrf_token, transaction_id)
        signin_form = confirm_signin(session, csrf_token, transaction_id)
        complete_oidc(session, config.user_agent, signin_form)
        load_account_home(session, config.user_agent)
        open_consumption_page(session, config.user_agent)
        download_token = fetch_download_token(session, config.user_agent)
        response = download_readings(
            session,
            config.user_agent,
            config.mprn,
            config.search_type,
            download_token,
        )
    except LoginError as exc:
        logger.error("[FAILED] %s", exc)
        raise SystemExit(1)
    finally:
        logger.debug("[END] Closing session.")
        session.close()

    filename = parse_filename(response)
    logger.info("Downloaded file :: %s (%s bytes)", filename, response.headers.get("Content-Length"))

    readings_csv = decode_payload(response)
    if args.format == "csv":
        print(readings_csv)
    else:
        print(csv_to_json(readings_csv))


if __name__ == "__main__":
    main()
