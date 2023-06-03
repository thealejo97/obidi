from fastapi import FastAPI, HTTPException
import requests
from pydantic import BaseModel
from utils import get_secret, get_external_urls


app = FastAPI()
hubspot_key = get_secret("HUBSPOT_ACCESS_TOKEN")


class ContactCreateRequest(BaseModel):
    company: str
    email: str
    firstname: str
    lastname: str
    phone: str
    website: str


@app.post("/contacts/")
def contacts(contact: ContactCreateRequest):
    """
        API que crea un contacto en hubspot
        :param contact:
        :return:
        {
            "id": "5601",
            "properties": {...},
            "createdAt": ...,
            "updatedAt": ...,
            "archived": false
        }
    """
    url = get_external_urls('CREATE_CONTACT_HUBSPOT')
    headers = {"Authorization": f"Bearer {hubspot_key}"}
    body = contact.dict()

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
