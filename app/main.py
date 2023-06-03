from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
import requests
from pydantic import BaseModel
import asyncpg
from utils import get_secret, get_external_urls_hubspot, get_external_urls_clickup
from sqlalchemy import create_engine, Column, Integer, String, DateTime, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()
hubspot_key = get_secret("HUBSPOT_ACCESS_TOKEN")
clickup_key = get_secret("CLICKUP_ACCESS_TOKEN")
db_info = get_secret("DATABASE_DEFAULT")
POSTGRES_USER = db_info.get('USER')
POSTGRES_PASSWORD = db_info.get('PASSWORD')
POSTGRES_HOST = db_info.get('HOST')
POSTGRES_PORT = db_info.get('PORT')
POSTGRES_DB = db_info.get('NAME')


dsn = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"

engine = create_engine(dsn)

Session = sessionmaker(bind=engine)
session = Session()
class ContactCreateRequest(BaseModel):
    company: str
    email: str
    firstname: str
    lastname: str
    phone: str
    website: str
    estado_clickup: str

class TaskCreateRequest(BaseModel):
    name: str
    description: str
    priority: str

Base = declarative_base()

class HistoryLogRequest(Base):
    __tablename__ = 'history_log_requests'
    id = Column(Integer, primary_key=True)
    request_method = Column(String)
    request_url = Column(String)
    request_timestamp = Column(DateTime)

class HistoryLogRequestModel(BaseModel):
    request_method: str
    request_url: str
    request_timestamp: datetime
#Creamos la tabla history_log_requests que almacenara los registros
Base.metadata.create_all(engine)
@app.post("/contacts/")
async def contacts(contact: ContactCreateRequest):
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
    contact_dict = contact.dict()
    body = {
        "properties": {
            "email": contact_dict.get("email"),
            "firstname": contact_dict.get("firstname"),
            "lastname": contact_dict.get("lastname"),
            "phone": contact_dict.get("phone"),
            "website": contact_dict.get("website"),
            "estado_clickup": contact_dict.get("estado_clickup")
        }
    }

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 201:
        # Guardar el log de la petición
        log = HistoryLogRequestModel(
            request_method="[POST]",
            request_url=url,
            request_timestamp=datetime.now()
        )
        await create_history_log_request(history=log)

        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
@app.get("/contacts/")
async def get_all_contacts():
    """
    API que obtiene todos los contactos en HubSpot SIN PAGINAR
    :return: Datos de los contactos en formato JSON
    """
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {"Authorization": f"Bearer {hubspot_key}"}

    all_contacts = []

    has_more = True
    after = None

    while has_more:
        params = {"limit": 100}
        if after:
            params["after"] = after

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            # Guardar el log de la petición
            log = HistoryLogRequestModel(
                request_method="[GET]",
                request_url=url,
                request_timestamp=datetime.now()
            )
            await create_history_log_request(history=log)
            contacts_data = response.json()
            contacts = contacts_data.get('results', [])
            all_contacts.extend(contacts)

            pagination = contacts_data.get('paging', {})
            next_page = pagination.get('next')
            if next_page:
                after = next_page.get('after')
            else:
                has_more = False
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())

    return all_contacts
@app.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    """
        API que obtiene los contacto en hubspot
        :param contact:
        :return:
    """
    url = f"https://api.hubapi.com/contacts/v1/contact/vid/{contact_id}/profile"

    headers = {"Authorization": f"Bearer {hubspot_key}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        properties = response.json().get("properties", {})
        # Guardar el log de la petición
        log = HistoryLogRequestModel(
            request_method="[GET]",
            request_url=url,
            request_timestamp=datetime.now()
        )
        await create_history_log_request(history=log)


        return properties
    else:
        if response.status_code == 404:
            raise HTTPException(status_code=response.status_code, detail="NOT found")
        raise HTTPException(status_code=response.status_code, detail=response.json())
@app.post("/clickup/tasks/")
async def create_task(task: TaskCreateRequest):
    """
        API que crea un tasks en clickup
        :param
        :return: 201: created
    """
    url = get_external_urls_clickup('CREATE_TASK_CLICKUP')

    headers = {"Authorization": f"{clickup_key}"}
    body = task.dict()

    response = requests.post(url, json=body, headers=headers)

    if response.status_code == 200:
        # Guardar el log de la petición
        log = HistoryLogRequestModel(
            request_method="[POST]",
            request_url=url,
            request_timestamp=datetime.now()
        )
        await create_history_log_request(history=log)


        return {'status_code': response.status_code , 'data' : response.json()}
    else:
        return {'status_code': response.status_code , 'data' : response.json()}
@app.post("/sync_contacts/")
async def sync_contacts(background_tasks: BackgroundTasks):
    """
    Api que sincroniza los contactos de hubapi que se han creado con las tareas en clickup, revisa si ya existe usando la propiedad estado_clickup,
    si no ha sido creado crea la tarea en clickup
    :param background_tasks:
    :return:
    """
    async def sync_contacts_task():
        contacts = await  get_all_contacts()
        cant_contactos = len(contacts)  # Obtener la cantidad de contactos
        print(f"----------- iniciando sincronizacion de {cant_contactos} contactos -----------")
        if contacts:
            for contact in contacts:
                try:
                    if contact.get('id', None):
                        obtener_estado_clickup = await get_contact(contact.get('id'))

                        if obtener_estado_clickup.get('estado_clickup'):
                            estado_clickup = obtener_estado_clickup.get('estado_clickup').get('value')

                            if estado_clickup == "pending":
                                task_request = TaskCreateRequest(
                                    name=contact.get('firstname', '') + ' ' + contact.get('lastname', ''),
                                    description=contact.get('company', '') + ' ' + contact.get('email', ''),
                                    priority='3'
                                )
                                response = create_task(task_request)
                                if response['status_code'] == 200:
                                    print(response['status_code'], " ", contact.get("email"), "  sincronizado!")
                                else:
                                    print(contact.get('id'),contact.get('email'), "No se debe sincronizar ya ha sido sincronizado (estado_clickup)")
                            else:
                                print(contact.get('id'),contact.get('email'), "No se debe sincronizar ya ha sido sincronizado (estado_clickup)")

                        else:
                            print(contact.get('id'),contact.get('email'), "No se debe sincronizar ya ha sido sincronizado (estado_clickup)")
                except Exception as e:
                    print(f"Error al crear tarea para contacto: {contact.get('firstname', '')} {contact.get('lastname', '')}")
                    print(f"Mensaje de error: {str(e)}")

    background_tasks.add_task(sync_contacts_task)
    return {"message": "Sincronización de contactos iniciada, ESTO PUEDE TARDAR un tiempo"}
@app.post("/history-log-requests/")
async def create_history_log_request(history: HistoryLogRequestModel):
    """
    API que crea una instancia del modelo HistoryLogRequest con los datos proporcionados y la guarda en la base de datos.
    :param history: Datos del registro de log a crear
    :return: Respuesta de éxito en caso de éxito
    """
    log_request = HistoryLogRequest(
        request_method=history.request_method,
        request_url=history.request_url,
        request_timestamp=history.request_timestamp
    )

    session = Session()

    try:
        session.add(log_request)
        session.commit()
        return {"message": "Registro creado exitosamente"}
    except Exception as e:
        # Manejar el error según corresponda
        return {"error": str(e)}
    finally:
        session.close()
@app.get("/history-log-requests/")
async def get_history_log_requests():
    """
    Api que devuelve todos los registros de logs almacenados en el log de peticiones
    :return: Lista de registros de logs
    """
    session = Session()

    try:
        history_logs = session.query(HistoryLogRequest).all()
        results = []
        for log in history_logs:
            result = {
                "id": log.id,
                "request_method": log.request_method,
                "request_url": log.request_url,
                "request_timestamp": log.request_timestamp
            }
            results.append(result)

        return results
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()
