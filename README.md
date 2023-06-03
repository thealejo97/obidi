Aplicación que permite la creación de contactos en el portal hubspot y sincronización con tareas de clickup

- Se debe de crear un ambiente Python
- Ingresar a la carpeta del proyecto e instalar los requerimientos que están en el archivo requirements.txt
•	pip install -r requirements.txt
- Crear el archivo secrets.json con la información sensible del proyecto debe tener la siguiente estructura:

    {
        "FILENAME": "secrets.json",
        "CLICKUP_ACCESS_TOKEN": "ACCES_TOKEN",
        "CLICKUP_LIST_ID": "LIST_ID",
        "HUBSPOT_ACCESS_TOKEN": "ACCES_TOKEN",
        "DATABASE_DEFAULT": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "DATA_BASENAME",
            "USER": "USERNAME",
            "PASSWORD": "PASSWORD",
            "HOST": "HOST",
            "PORT": "5432"
        }
    }

- Dentro de la carpeta app del proyecto ejecutar el proyecto utilizando uvicorn main:app –reload
- Ya se pueden consumir las apis del proyecto

/contacts [GET] trae una lista de todos los contactos creados en hubspot sin paginar
/contacts/contact_id [GET] trae un contacto en específico y sus propiedades incluyendo la propiedad estado_clickup
/contacts [POST] crea un nuevo contacto en hubspot
/clickup/tasks/ [POST] crea una nueva tarea en clic up con la información del contacto
/sync_contacts/[POST] sincroniza los contactos de hubspot con clic up y valida que los contactos no se creen duplicados utilizando la propiedad estado_clickup
/create_history_log_request/[POST] crea el registro en la base de datos con las peticiones, tipo, y fecha
/create_history_log_request/[GET] devuelve todos los registros en la base de datos con las peticiones, tipo, y fecha
