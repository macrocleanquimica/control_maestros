import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'control_maestros.settings')
django.setup()

from gestion_escolar.models import Historial, PlantillaTramite, MotivoTramite
try:
    h = Historial.objects.get(id=387)
    d = h.datos_tramite
    pl_id = d.get('plantilla')
    mo_id = d.get('motivo_tramite')
    
    pl = PlantillaTramite.objects.get(id=pl_id) if pl_id else None
    mo = MotivoTramite.objects.get(id=mo_id) if mo_id else None
    
    print(f"Historial 387:")
    print(f"Tipo Documento: {h.tipo_documento}")
    print(f"Plantilla en JSON: {pl.nombre if pl else 'None'} (ID: {pl_id})")
    print(f"Motivo en JSON: {mo.motivo_tramite if mo else 'None'} (ID: {mo_id})")
except Exception as e:
    print(f"Error: {e}")
