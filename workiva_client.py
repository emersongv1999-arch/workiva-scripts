import os
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning
from dotenv import load_dotenv

load_dotenv()

# La red corporativa usa inspección SSL — se desactiva verificación de certificados
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
VERIFY_SSL = False

TOKEN_URL  = "https://api.app.wdesk.com/iam/v1/oauth2/token"
BASE_URL   = "https://h.app.wdesk.com/s/wdata/prep"
WDESK_BASE = "https://api.app.wdesk.com"

CLIENT_ID     = os.getenv("WORKIVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("WORKIVA_CLIENT_SECRET")
WORKSPACE_ID  = os.getenv("WORKIVA_WORKSPACE_ID")


def get_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/json"},
        timeout=30,
        verify=VERIFY_SSL,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_session() -> requests.Session:
    token = get_token()
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "X-Version":     "2022-01-01",
    })
    session.verify = VERIFY_SSL
    return session


if __name__ == "__main__":
    print("Conectando a Workiva...")
    session = get_session()

    r = session.get(f"{BASE_URL}/api/v1/table?includeShared=true&limit=100", timeout=30)
    if r.status_code == 200:
        items = r.json().get("body", [])
        print(f"Conexion exitosa! Tablas disponibles: {len(items)}")
        for t in items[:5]:
            print(f"  - {t.get('name','?')} ({t.get('id','?')})")
    else:
        print(f"Error {r.status_code}: {r.text}")
