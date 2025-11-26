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
    Para la integración con Google Sheets, es necesario configurar las credenciales de una cuenta de servicio de Google Cloud. Consulta la sección detallada "Manual de Configuración de Credenciales de Google Sheets" más abajo para obtener instrucciones completas.

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

---

## Manual de Configuración de Credenciales de Google Sheets

Este manual te guiará a través de los pasos para configurar las credenciales de Google Sheets en tu proyecto Django de forma segura, utilizando un archivo de cuenta de servicio local.

#### 1. Requisitos Previos en Google Cloud Platform (GCP)

Antes de empezar, asegúrate de tener lo siguiente en tu proyecto de GCP:

*   **Proyecto de GCP:** Un proyecto activo en Google Cloud Platform.
*   **API de Google Sheets habilitada:** La API de Google Sheets debe estar habilitada para tu proyecto.
    *   Ve a la [Biblioteca de API de Google Cloud](https://console.cloud.google.com/apis/library).
    *   Busca "Google Sheets API" y asegúrate de que esté habilitada.
*   **Cuenta de Servicio:** Una cuenta de servicio creada con los roles necesarios para acceder a Google Sheets (mínimo "Editor de Hojas de Cálculo" o un rol personalizado con permisos de lectura/escritura).
    *   Ve a `IAM y administración` > `Cuentas de servicio`.
    *   Crea una nueva cuenta de servicio o selecciona una existente.
    *   Asegúrate de que tenga los permisos adecuados.
*   **Descargar la clave JSON:** Una vez creada la cuenta de servicio, genera una nueva clave JSON y descárgala. Este archivo contiene tus credenciales sensibles.

#### 2. Configuración en tu Proyecto Django

1.  **Copia el archivo JSON de la cuenta de servicio:**
    *   El archivo JSON que descargaste de GCP (por ejemplo, `your-project-name-xxxxxx.json`) cópialo y pégalo en la **raíz de tu proyecto Django** (al mismo nivel que `manage.py`).
    *   **Renómbralo** a `service_account_local.json`.

2.  **Ignorar el archivo en Git:**
    *   Abre tu archivo `.gitignore` (en la raíz de tu proyecto).
    *   Asegúrate de que las siguientes líneas estén presentes para evitar que tus credenciales se suban accidentalmente a tu repositorio:
        ```
        /service_account_local.json
        google_sheets_credentials.json # Si aún conservas el nombre original
        ```

3.  **Configuración en `settings.py`:**
    *   Abre `control_maestros/settings.py`.
    *   El código ya está configurado para cargar las credenciales desde `service_account_local.json`. Busca el bloque `Google Sheets API Configuration`. Debería verse así:

        ```python
        # Google Sheets API Configuration
        # ADVERTENCIA DE SEGURIDAD: Las credenciales de la API de Google Sheets son un secreto
        # y NO deben ser versionadas en un repositorio público.
        # Se recomienda cargarlas desde un archivo local que esté en .gitignore.

        # Ruta al archivo de credenciales local (debe estar en .gitignore)
        LOCAL_SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account_local.json')

        GOOGLE_SHEETS_CREDENTIALS = {}
        if os.path.exists(LOCAL_SERVICE_ACCOUNT_FILE):
            try:
                with open(LOCAL_SERVICE_ACCOUNT_FILE, 'r') as f:
                    GOOGLE_SHEETS_CREDENTIALS = json.load(f)
            except Exception as e:
                # Considera usar un logger en lugar de print en consola
                print(f"ERROR: No se pudieron cargar las credenciales de Google Sheets desde {LOCAL_SERVICE_ACCOUNT_FILE}: {e}")
        else:
            # Considera usar un logger en lugar de print en consola
            print(f"ADVERTENCIA: Archivo de credenciales de Google Sheets no encontrado en {LOCAL_SERVICE_ACCOUNT_FILE}. La integración con Google Sheets no funcionará.")

        # Cargar IDs desde variables de entorno (o directamente si no son sensibles)
        # Si GOOGLE_SHEET_ID y GOOGLE_SHEET_WORKSHEET_NAME no son secretos, pueden estar aquí directamente.
        # Si son sensibles, se recomienda cargarlos también desde variables de entorno.
        GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1Svs7eClLiHezipj9RnV_Q8yNuxJbxew--OqKemOeoSs') # Usar valor por defecto si no está en .env
        GOOGLE_SHEET_WORKSHEET_NAME = os.getenv('GOOGLE_SHEET_WORKSHEET_NAME', 'DatosVacancias') # Usar valor por defecto si no está en .env
        ```
    *   **`GOOGLE_SHEET_ID` y `GOOGLE_SHEET_WORKSHEET_NAME`**: Estos valores se cargan desde variables de entorno (`.env`) o usan un valor por defecto si no se encuentran.
        *   Abre tu archivo `.env` (en la raíz de tu proyecto).
        *   Añade o actualiza las siguientes líneas con el ID de tu hoja de cálculo de Google y el nombre de la pestaña (worksheet) donde quieres escribir:
            ```
            GOOGLE_SHEET_ID="TU_ID_DE_HOJA_DE_CALCULO"
            GOOGLE_SHEET_WORKSHEET_NAME="TU_NOMBRE_DE_PESTAÑA"
            ```
        *   **Importante:** El `GOOGLE_SHEET_ID` es la parte alfanumérica de la URL de tu hoja de cálculo (por ejemplo, `https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA_DE_CALCULO/edit`).

#### 3. Compartir la Hoja de Cálculo con la Cuenta de Servicio

Este es un paso **CRÍTICO** y a menudo olvidado:

1.  Abre tu hoja de cálculo de Google en tu navegador.
2.  Haz clic en el botón "Compartir" (normalmente en la esquina superior derecha).
3.  En el campo "Añadir personas y grupos", pega la **dirección de correo electrónico de tu cuenta de servicio**. Esta dirección se encuentra en tu archivo `service_account_local.json` bajo la clave `client_email`.
    *   Ejemplo: `escritor-datos-sheets@integracionappvacanciasdjango.iam.gserviceaccount.com`
4.  Asegúrate de darle a la cuenta de servicio los permisos adecuados (por ejemplo, "Editor") para que pueda escribir en la hoja.
5.  Haz clic en "Enviar".

#### 4. Probar la Integración

1.  Reinicia tu servidor de desarrollo de Django.
2.  Realiza la acción en tu aplicación que debería interactuar con Google Sheets.
3.  Verifica la consola de tu servidor Django para asegurarte de que no haya errores y que la operación se haya completado con éxito.