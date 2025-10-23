from django.core.management.base import BaseCommand
from gestion_escolar.models import Historial, Vacancia, Maestro, LoteReporteVacancia
import json

def get_full_name(maestro):
    if not maestro: return ""
    return f"{maestro.nombres or ''} {maestro.a_paterno or ''} {maestro.a_materno or ''}".strip()

class Command(BaseCommand):
    help = 'Populates datos_tramite for existing Historial entries of type "Asignación de Vacancia".'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data migration for Historial entries...'))

        # Find existing Historial entries that are "Reporte de Vacancia"
        reporte_vacancia_historial_items = Historial.objects.filter(
            tipo_documento="Reporte de Vacancia",
            lote_reporte__isnull=False # Ensure it's linked to a LoteReporteVacancia
        )

        self.stdout.write(f'Found {reporte_vacancia_historial_items.count()} "Reporte de Vacancia" Historial items to process.')

        for reporte_item in reporte_vacancia_historial_items:
            try:
                lote = reporte_item.lote_reporte
                if not lote:
                    self.stdout.write(self.style.WARNING(f'Historial item {reporte_item.id} ("Reporte de Vacancia") has no associated lote_reporte. Skipping.'))
                    continue

                vacancias_in_lote = Vacancia.objects.filter(lote=lote)
                if not vacancias_in_lote.exists():
                    self.stdout.write(self.style.WARNING(f'Lote {lote.id} (from Historial item {reporte_item.id}) has no associated Vacancia objects. Skipping.'))
                    continue

                for vacancia in vacancias_in_lote:
                    # Check if a Historial entry for this specific Vacancia already exists
                    # This prevents duplicate entries if the command is run multiple times
                    existing_historial_for_vacancia = Historial.objects.filter(
                        tipo_documento="Asignación de Vacancia",
                        maestro=vacancia.maestro_titular,
                        lote_reporte=lote,
                        datos_tramite__id_vacancia=vacancia.id # Assuming id_vacancia is stored in datos_tramite
                    ).first()

                    if existing_historial_for_vacancia:
                        self.stdout.write(self.style.WARNING(f'Historial entry for Vacancia {vacancia.id} (Lote {lote.id}) already exists. Skipping creation.'))
                        continue

                    maestro_titular_obj = vacancia.maestro_titular
                    maestro_interino_obj = vacancia.maestro_interino

                    datos_tramite_vacancia = {
                        "tipo_movimiento": "Detalle de Asignación de Vacancia",
                        "id_vacancia": vacancia.id,
                        "clave_presupuestal_posicion": vacancia.clave_presupuestal,
                        "maestro_titular_info": {
                            "id_maestro": maestro_titular_obj.id_maestro,
                            "nombre_completo": get_full_name(maestro_titular_obj),
                            "clave_presupuestal": maestro_titular_obj.generar_clave_presupuestal()
                        }
                    }

                    if maestro_interino_obj:
                        datos_tramite_vacancia["maestro_interino_info"] = {
                            "id_maestro": maestro_interino_obj.id_maestro,
                            "nombre_completo": get_full_name(maestro_interino_obj),
                            "clave_presupuestal": maestro_interino_obj.generar_clave_presupuestal()
                        }
                    
                    # Create a new Historial entry for the individual Vacancia
                    Historial.objects.create(
                        usuario=reporte_item.usuario, # Use the user who created the report
                        tipo_documento="Asignación de Vacancia",
                        maestro=maestro_titular_obj,
                        maestro_secundario_nombre=get_full_name(maestro_interino_obj) if maestro_interino_obj else '',
                        ruta_archivo="",
                        motivo="Asignación de Vacancia",
                        lote_reporte=lote,
                        datos_tramite=datos_tramite_vacancia,
                        fecha_creacion=reporte_item.fecha_creacion # Use the creation date of the report item
                    )
                    self.stdout.write(self.style.SUCCESS(f'Successfully created new Historial item for Vacancia {vacancia.id} (Lote {lote.id}).'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing "Reporte de Vacancia" Historial item {reporte_item.id}: {e}'))

        self.stdout.write(self.style.SUCCESS('Data migration for Historial entries completed.'))
