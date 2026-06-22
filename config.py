import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("WORKIVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("WORKIVA_CLIENT_SECRET")
WORKSPACE_ID  = os.getenv("WORKIVA_WORKSPACE_ID")

TOKEN_URL  = "https://api.app.wdesk.com/iam/v1/oauth2/token"
BASE_URL   = "https://h.app.wdesk.com/s/wdata/prep"
WDESK_BASE = "https://api.app.wdesk.com"

# ID del workspace sin prefijo "w_"
WORKSPACE_BARE = WORKSPACE_ID.replace("w_", "") if WORKSPACE_ID else ""
