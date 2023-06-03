from fastapi import FastAPI, HTTPException, BackgroundTasks
import requests
from pydantic import BaseModel
from hubspot import HubSpot
from utils import get_secret, get_external_urls_hubspot, get_external_urls_clickup


app = FastAPI()
hubspot_key = get_secret("HUBSPOT_ACCESS_TOKEN")
clickup_key = get_secret("CLICKUP_ACCESS_TOKEN")

class ContactCreateRequest(BaseModel):
    company: str
    email: str
    firstname: str
    lastname: str
    phone: str
    website: str

class TaskCreateRequest(BaseModel):
    name: str
    description: str
    priority: str


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
    url = get_external_urls_hubspot('CREATE_CONTACT_HUBSPOT')
    headers = {"Authorization": f"Bearer {hubspot_key}"}
    body = contact.dict()

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
@app.get("/contacts/")
def get_contacts():
    """
        API que obtiene los contacto en hubspot
        :param contact:
        :return:
    """
    url = get_external_urls_hubspot('CREATE_CONTACT_HUBSPOT')
    headers = {"Authorization": f"Bearer {hubspot_key}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
@app.post("/sync_contacts/")
async def sync_contacts(background_tasks: BackgroundTasks):
    async def sync_contacts_task():
        contacts = get_contacts()
        if contacts:
            for contact in contacts.get('results', None):
                print(contact)


    background_tasks.add_task(sync_contacts_task)

    return {"message": "Sincronización de contactos iniciada"}

@app.post("/clickup/tasks/")
def create_task(task: TaskCreateRequest):
    """
        API que crea un tasks en clickup
        :param
        :return: 201: created
    """
    url = get_external_urls_clickup('CREATE_TASK_CLICKUP')

    headers = {"Authorization": f"{clickup_key}"}
    body = task.dict()

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())