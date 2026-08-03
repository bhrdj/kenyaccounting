"""Google OAuth credential locations and the shared gspread client.

Payroll authenticates as a *user*, not a service account: the tool acts on
the Sheets and Drive files a person can already see, so access is granted
by ordinary Drive sharing rather than by IAM roles on the Cloud project.
The Cloud project only supplies the OAuth client identity and the enabled
APIs.

Two files are involved, and they are easy to confuse:

    CREDS   the OAuth *client* (app identity), downloaded from the Cloud
            console. Shared by everyone who runs the tool. This is a
            desktop-app client, where Google does not treat the secret as
            confidential, so handing a colleague a copy is expected.

    TOKEN   the *user* token, written by gspread after the browser consent
            flow. Personal, per-machine, and a live bearer credential --
            never copy this between people.

Both live outside the repo so no credential can be committed.
"""

from pathlib import Path

CONFIG_DIR = Path.home() / ".config/google"
GSPREAD_CREDS = CONFIG_DIR / "elaccounting_creds.json"
GSPREAD_TOKEN = CONFIG_DIR / "elaccounting_token.json"

_SETUP_HELP = f"""OAuth client not found at {GSPREAD_CREDS}

Download it from the Google Cloud console for the project hosting the
payroll OAuth client:
    APIs & Services -> Credentials -> the Desktop app client -> Download JSON
then save it to that path and re-run. See README.md."""


def client():
    """Authorized gspread client, prompting for browser consent if needed."""
    import gspread

    if not GSPREAD_CREDS.is_file():
        raise FileNotFoundError(_SETUP_HELP)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return gspread.oauth(
        credentials_filename=str(GSPREAD_CREDS),
        authorized_user_filename=str(GSPREAD_TOKEN),
    )
