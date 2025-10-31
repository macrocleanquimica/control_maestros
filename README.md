# Control de Maestros

Sistema de gestión escolar para el control de maestros, vacancias y trámites relacionados.

## Creador

- **krascode L.I. Jose Joel Carrasco Alvarez**

## Requisitos Previos

- Python 3.x
- pip (manejador de paquetes de Python)

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/macrocleanquimica/control_maestros
    cd control_maestros
    ```

2.  **Crear y activar un entorno virtual:**
    ```bash
    python -m venv venv
    # En Windows
    venv\Scripts\activate
    # En macOS/Linux
    source venv/bin/activate
    ```

3.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuración de variables de entorno:**
    Crea un archivo `.env` en la raíz del proyecto (al mismo nivel que `manage.py`). Este archivo contendrá variables de entorno para configuraciones sensibles.

    Ejemplo de `.env`:
    ```
    SECRET_KEY='tu_clave_secreta_aqui'
    DEBUG=True
    # Otras variables de entorno necesarias
    ```

5.  **Configurar las credenciales de Google Sheets:**
    Para la integración con Google Sheets, es necesario configurar las credenciales de una cuenta de servicio de Google Cloud.

    -   Crea un proyecto en la [Consola de Google Cloud](https://console.cloud.google.com/).
    -   Activa la API de Google Drive y la API de Google Sheets.
    -   Crea una cuenta de servicio y descarga el archivo de credenciales en formato JSON.
    -   **Guarda este archivo JSON en una ubicación segura (por ejemplo, en la raíz del proyecto o en un subdirectorio `config/`) y define su ruta en el archivo `.env`** (por ejemplo, `GOOGLE_SHEETS_CREDENTIALS_PATH='./credentials.json'`).
    -   Asegúrate de compartir tus hojas de cálculo de Google con el correo electrónico de la cuenta de servicio.
    -   En `control_maestros/settings.py`, deberás cargar esta variable de entorno para que la aplicación pueda acceder a la ruta del archivo de credenciales.

6.  **Configurar la base de datos y ejecutar migraciones:**
    ```bash
    python manage.py migrate
    ```

## Uso

Para iniciar el servidor de desarrollo, ejecuta el siguiente comando:

```bash
python manage.py runserver
```

El sistema estará disponible en `http://127.0.0.1:8000/`.
