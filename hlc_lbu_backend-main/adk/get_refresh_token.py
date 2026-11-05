"""Run this script ONCE to generate a Google Ads OAuth2 refresh token.

The refresh token is then stored in Secret Manager and never needs to be
regenerated unless explicitly revoked.

Usage:
    # Set credentials via environment (never hardcode them):
    export GOOGLE_ADS_CLIENT_ID="<your-client-id>"
    export GOOGLE_ADS_CLIENT_SECRET="<your-client-secret>"

    # Or create a local adk/.env file (gitignored):
    #   GOOGLE_ADS_CLIENT_ID=...
    #   GOOGLE_ADS_CLIENT_SECRET=...

    cd adk/
    source ../.venv/bin/activate
    python3 get_refresh_token.py

    # Store the resulting token in Secret Manager:
    echo -n "<token>" | gcloud secrets versions add adk-google-ads-refresh-token --data-file=-

Credentials source:
    CLIENT_ID / CLIENT_SECRET come from the Google Cloud Console OAuth 2.0 client
    created for the Google Ads MCC account (266-443-8976).
    Never commit these values — retrieve them from the GCP Console or Secret Manager.
"""

import os
import sys

# Load adk/.env if present (local dev convenience — file must be gitignored)
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

CLIENT_ID     = os.environ.get("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET must be set.")
    print("  export GOOGLE_ADS_CLIENT_ID='...'")
    print("  export GOOGLE_ADS_CLIENT_SECRET='...'")
    print("  Or create adk/.env with those keys (file must be gitignored).")
    sys.exit(1)

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/adwords"],
)

print("Opening browser for Google authorization...")
print("Sign in with the account that has access to your MCC (266-443-8976)")
print()

creds = flow.run_local_server(port=8080)

print()
print("=" * 50)
print("YOUR NEW REFRESH TOKEN:")
print(creds.refresh_token)
print("=" * 50)
print()
print("Store it in Secret Manager:")
print(f'  echo -n "{creds.refresh_token}" | gcloud secrets versions add adk-google-ads-refresh-token --data-file=-')
