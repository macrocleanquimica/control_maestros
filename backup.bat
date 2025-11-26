@echo off
echo Iniciando el proceso de backup de la base de datos...

:: Cambia al directorio del proyecto donde está manage.py
cd /d "C:\Users\Usuario\Desktop\control_maestros"

:: Crea un nombre de archivo con la fecha y hora actual (formato YYYY-MM-DD_HH-mm-ss)
:: Asume un formato de fecha regional DD/MM/YYYY.
set DATE_STAMP=%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%
set CLEAN_TIME=%TIME::=-%
set CLEAN_TIME=%CLEAN_TIME: =0%
set CLEAN_TIME=%CLEAN_TIME:,=.%
set BACKUP_FILENAME=backup_%DATE_STAMP%_%CLEAN_TIME%.json

:: Crea el directorio de backups si no existe
if not exist backups mkdir backups

:: Ejecuta el comando de backup de Django
echo Creando backup en "backups\%BACKUP_FILENAME%"...
python manage.py dumpdata > "backups\%BACKUP_FILENAME%"

echo Backup completado.
echo Proceso finalizado.
timeout /t 5
