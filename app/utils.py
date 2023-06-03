from fastapi import FastAPI, HTTPException
import json
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "..", "secrets.json")) as f:
    secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    """Get the secret variable or raise an exception."""
    try:
        return secrets[setting]
    except KeyError:
        error_msg = f"Definir la variable de ambiente {setting}"
        raise HTTPException(status_code=500, detail=error_msg)

def get_external_urls(id):
    url = None
    base_url = 'https://api.hubapi.com/crm/v3/objects/'
    if id == 'CREATE_CONTACT_HUBSPOT':
        url = f"{base_url}contacts/"
    return url