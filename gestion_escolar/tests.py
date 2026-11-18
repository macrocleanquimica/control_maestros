import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .campos_plantilla import (
    PLANTILLAS_SISTEMA,
    config_para_js,
    config_sistema,
    config_vacia,
)
from .forms import MaestroForm, TramiteForm
from .models import (
    Categoria,
    Escuela,
    Historial,
    Interinato,
    KardexMovimiento,
    LoteReporteVacancia,
    Maestro,
    MotivoTramite,
    PlantillaTramite,
    TipoApreciacion,
    Vacancia,
    Zona,
)
from .views.personal import buscar_plaza_vacante, reclamar_plaza_vacante
from .motivos_plantilla import ids_permitidos
from .plantillas_utils import (
    es_administrador,
    extraer_variables_docx,
    guardar_docx_subido,
)
from .validators import (
    es_curp_valida,
    es_rfc_valido,
    fecha_nacimiento_desde_curp,
    normalizar_curp,
    normalizar_rfc,
    prefijo_rfc_desde_curp,
    validar_curp,
    validar_rfc,
)

CURP_VALIDA_1985 = 'GARC850101HDFRRR04'
CURP_VALIDA_2005 = 'LOPM050203MDFPRSA1'
CURP_CHECK_INVALIDO = 'GARC850101HDFRRR05'
CURP_FECHA_INVALIDA = 'GARC851301HDFRRR04'
CURP_ENTIDAD_INVALIDA = 'GARC850101HZZRRR04'
CURP_HOMOCLAVE_INVALIDA = 'GARC850101HDFRRRA4'
CURP_CONSONANTE_INVALIDA = 'GARC850101HDFRAR04'

RFC_VALIDO_1985 = 'GARC850101RR5'
RFC_CHECK_INVALIDO = 'GARC850101RR4'
RFC_FECHA_INVALIDA = 'GARC851301RR5'


class CurpRfcValidatorTests(TestCase):
    def test_normalizacion(self):
        self.assertEqual(normalizar_curp(' garc 850101 hdfrrr04 '), CURP_VALIDA_1985)
        self.assertEqual(normalizar_rfc(' garc850101 rr5 '), RFC_VALIDO_1985)
        self.assertEqual(normalizar_curp(None), '')
        self.assertEqual(normalizar_rfc(None), '')

    def test_curp_validas(self):
        validar_curp(CURP_VALIDA_1985)
        validar_curp(CURP_VALIDA_2005)
        self.assertTrue(es_curp_valida(CURP_VALIDA_1985))
        self.assertTrue(es_curp_valida(CURP_VALIDA_2005))

    def test_curp_vacia_es_opcional(self):
        validar_curp('')
        validar_curp(None)
        self.assertTrue(es_curp_valida(''))

    def test_curp_longitud_incorrecta(self):
        with self.assertRaisesMessage(Exception, '18 caracteres'):
            validar_curp('GARC850101HDFRRR0')

    def test_curp_check_invalido(self):
        with self.assertRaisesMessage(Exception, 'dígito verificador'):
            validar_curp(CURP_CHECK_INVALIDO)
        self.assertFalse(es_curp_valida(CURP_CHECK_INVALIDO))

    def test_curp_fecha_invalida(self):
        with self.assertRaisesMessage(Exception, 'fecha de nacimiento'):
            validar_curp(CURP_FECHA_INVALIDA)

    def test_curp_entidad_invalida(self):
        with self.assertRaisesMessage(Exception, 'entidad federativa'):
            validar_curp(CURP_ENTIDAD_INVALIDA)

    def test_curp_homoclave_invalida(self):
        with self.assertRaisesMessage(Exception, 'posición 17'):
            validar_curp(CURP_HOMOCLAVE_INVALIDA)

    def test_curp_consonante_invalida(self):
        with self.assertRaisesMessage(Exception, 'consonantes'):
            validar_curp(CURP_CONSONANTE_INVALIDA)

    def test_rfc_validos(self):
        validar_rfc(RFC_VALIDO_1985)
        validar_rfc('LOPM050203PRA')
        self.assertTrue(es_rfc_valido(RFC_VALIDO_1985))
        self.assertTrue(es_rfc_valido('LOPM050203PRA'))

    def test_rfc_vacio_es_opcional(self):
        validar_rfc('')
        validar_rfc(None)
        self.assertTrue(es_rfc_valido(''))

    def test_rfc_longitud_incorrecta(self):
        with self.assertRaisesMessage(Exception, '13 caracteres'):
            validar_rfc('GARC850101RR')

    def test_rfc_check_invalido(self):
        with self.assertRaisesMessage(Exception, 'dígito verificador'):
            validar_rfc(RFC_CHECK_INVALIDO)
        self.assertFalse(es_rfc_valido(RFC_CHECK_INVALIDO))

    def test_rfc_fecha_invalida(self):
        with self.assertRaisesMessage(Exception, 'fecha de nacimiento'):
            validar_rfc(RFC_FECHA_INVALIDA)

    def test_fecha_y_prefijo_desde_curp(self):
        self.assertEqual(fecha_nacimiento_desde_curp(CURP_VALIDA_1985), date(1985, 1, 1))
        self.assertEqual(fecha_nacimiento_desde_curp(CURP_VALIDA_2005), date(2005, 2, 3))
        self.assertIsNone(fecha_nacimiento_desde_curp(CURP_FECHA_INVALIDA))
        self.assertEqual(prefijo_rfc_desde_curp(CURP_VALIDA_1985), 'GARC850101')
        self.assertEqual(prefijo_rfc_desde_curp(''), '')


class MaestroFormCurpRfcTests(TestCase):
    def setUp(self):
        # Registro "legacy": ambos valores existen pero no pasan la validación.
        self.maestro = Maestro.objects.create(
            a_paterno='GARCIA',
            a_materno='RAMIREZ',
            nombres='JUAN',
            curp=CURP_CHECK_INVALIDO,
            rfc=RFC_CHECK_INVALIDO,
            fecha_nacimiento=date(1985, 1, 1),
        )

    def _datos_legacy(self):
        return {
            'a_paterno': self.maestro.a_paterno,
            'a_materno': self.maestro.a_materno,
            'nombres': self.maestro.nombres,
            'curp': self.maestro.curp,
            'rfc': self.maestro.rfc,
            'fecha_nacimiento': self.maestro.fecha_nacimiento.isoformat(),
        }

    def test_alta_nueva_valida_si_se_captura(self):
        form = MaestroForm(validar_curp_rfc=True, data={'curp': CURP_VALIDA_1985, 'rfc': RFC_VALIDO_1985})
        form.is_valid()
        self.assertFalse(form.has_error('curp'))
        self.assertFalse(form.has_error('rfc'))

    def test_alta_nueva_bloquea_invalidos(self):
        form = MaestroForm(validar_curp_rfc=True, data={'curp': CURP_CHECK_INVALIDO, 'rfc': RFC_CHECK_INVALIDO})
        form.is_valid()
        self.assertTrue(form.has_error('curp'))
        self.assertTrue(form.has_error('rfc'))
        self.assertIn('dígito verificador', form.errors['curp'][0])

    def test_sin_curp_ni_rfc_es_valido(self):
        form = MaestroForm(validar_curp_rfc=True, data={'curp': '', 'rfc': ''})
        form.is_valid()
        self.assertFalse(form.has_error('curp'))
        self.assertFalse(form.has_error('rfc'))

    def test_legacy_sin_cambios_se_permite_y_advierte(self):
        form = MaestroForm(validar_curp_rfc=True, data=self._datos_legacy(), instance=self.maestro)
        form.is_valid()
        self.assertFalse(form.has_error('curp'))
        self.assertFalse(form.has_error('rfc'))
        self.assertTrue(form.curp_aviso_legacy)
        self.assertTrue(form.rfc_aviso_legacy)

    def test_legacy_modificado_invalido_se_bloquea(self):
        datos = self._datos_legacy()
        datos['curp'] = 'GARC850101HDFRRR09'
        datos['rfc'] = 'GARC850101RR9'
        form = MaestroForm(validar_curp_rfc=True, data=datos, instance=self.maestro)
        form.is_valid()
        self.assertTrue(form.has_error('curp'))
        self.assertTrue(form.has_error('rfc'))

    def test_editar_sin_cambiar_curp_ignora_duplicado_previo(self):
        """Editar otros campos no debe bloquearse por una CURP repetida que ya existía."""
        Maestro.objects.create(
            a_paterno=self.maestro.a_paterno,
            a_materno=self.maestro.a_materno,
            nombres=self.maestro.nombres,
            curp=self.maestro.curp,
            rfc=self.maestro.rfc,
            fecha_nacimiento=date(1985, 1, 1),
        )
        datos = self._datos_legacy()
        datos['status'] = 'INACTIVO'
        form = MaestroForm(validar_curp_rfc=True, data=datos, instance=self.maestro)
        form.is_valid()
        self.assertFalse(form.has_error('curp'))

    def test_legacy_corregido_valido_pasa_sin_aviso(self):
        datos = self._datos_legacy()
        datos['curp'] = CURP_VALIDA_1985
        datos['rfc'] = RFC_VALIDO_1985
        form = MaestroForm(validar_curp_rfc=True, data=datos, instance=self.maestro)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertFalse(form.curp_aviso_legacy)
        self.assertFalse(form.rfc_aviso_legacy)

    def test_otra_plaza_hereda_legacy_sin_cambios(self):
        datos = {
            'a_paterno': self.maestro.a_paterno,
            'a_materno': self.maestro.a_materno,
            'nombres': self.maestro.nombres,
            'curp': self.maestro.curp,
            'rfc': self.maestro.rfc,
        }
        form = MaestroForm(
            data=datos,
            permitir_curp_duplicada=True,
            validar_curp_rfc=True,
            legacy_curp=self.maestro.curp,
            legacy_rfc=self.maestro.rfc,
        )
        form.is_valid()
        self.assertFalse(form.has_error('curp'))
        self.assertFalse(form.has_error('rfc'))
        self.assertTrue(form.curp_aviso_legacy)
        self.assertTrue(form.rfc_aviso_legacy)

    def test_otra_plaza_bloquea_cambio_invalido(self):
        form = MaestroForm(
            data={'curp': 'GARC850101HDFRRR09', 'rfc': 'GARC850101RR9'},
            permitir_curp_duplicada=True,
            validar_curp_rfc=True,
            legacy_curp=self.maestro.curp,
            legacy_rfc=self.maestro.rfc,
        )
        form.is_valid()
        self.assertTrue(form.has_error('curp'))
        self.assertTrue(form.has_error('rfc'))


class HistorialDetalleTramiteTests(TestCase):
    """La ficha de un movimiento debe abrir siempre, aunque no tenga datos_tramite."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='tester', email='tester@example.com', password='x'
        )
        self.maestro = Maestro.objects.create(
            id_maestro='99999',
            nombres='JUAN',
            a_paterno='PEREZ',
            a_materno='LOPEZ',
        )
        self.lote = LoteReporteVacancia.objects.create(usuario_generador=self.user)
        self.client.force_login(self.user)

    def _crear_eo(self):
        return Historial.objects.create(
            usuario=self.user,
            tipo_documento='Validación EO (Individual)',
            maestro=self.maestro,
            ruta_archivo='C:/ruta/falsa/EO_JUAN.xlsx',
            motivo='Generación de Formato EO',
            lote_reporte=self.lote,
        )

    def test_ficha_eo_sin_datos_tramite_no_redirige(self):
        item = self._crear_eo()

        r = self.client.get(f'/historial/detalle_tramite/{item.id}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Validación EO (Individual)')
        self.assertContains(r, 'Generación de Formato EO')
        self.assertContains(r, 'Descargar')
        self.assertNotContains(r, 'Corregir y regenerar')

    def test_ficha_eo_regresa_al_kardex(self):
        item = self._crear_eo()

        r = self.client.get(f'/historial/detalle_tramite/{item.id}/?from=kardex')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Volver al kardex')
        self.assertContains(r, f'/kardex/maestro/{self.maestro.pk}/')

    def test_ficha_con_datos_conserva_corregir_y_regenerar(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - ALTA INICIAL (09)',
            maestro=self.maestro,
            ruta_archivo='C:/ruta/falsa/ALTA.docx',
            datos_tramite={'clave_ct': '10DML0002K'},
            motivo='ALTA INICIAL',
        )

        r = self.client.get(f'/historial/detalle_tramite/{item.id}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Corregir y regenerar')
        self.assertContains(r, '10DML0002K')

    def test_kardex_enlaza_ficha_con_origen(self):
        item = self._crear_eo()

        r = self.client.get(f'/kardex/maestro/{self.maestro.pk}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'/historial/detalle_tramite/{item.id}/?from=kardex')

    def test_observaciones_se_pueden_editar_desde_la_ficha(self):
        item = self._crear_eo()

        r = self.client.get(f'/historial/detalle_tramite/{item.id}/')
        self.assertContains(r, 'id="btn-edit-obs"')

        r = self.client.post(
            f'/historial/guardar_observacion/{item.id}/',
            data='{"observaciones": "Revisado"}',
            content_type='application/json',
        )

        self.assertEqual(r.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.observaciones, 'Revisado')


class CorregirVacanciaHistorialTests(TestCase):
    """Corregir la vacancia de origen desde la ficha de un movimiento del kardex."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='tester', email='tester@example.com', password='x'
        )
        self.otro_user = User.objects.create_user(username='otro', password='x')
        self.maestro = Maestro.objects.create(
            id_maestro='99999',
            nombres='JUAN',
            a_paterno='PEREZ',
            a_materno='LOPEZ',
            status='LICENCIA',
        )
        self.apreciacion = TipoApreciacion.objects.create(descripcion='LICENCIA')
        self.lote = LoteReporteVacancia.objects.create(usuario_generador=self.user)
        self.vacancia = self._crear_vacancia()
        self.historial = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Reporte de Vacancia (Individual)',
            maestro=self.maestro,
            ruta_archivo='C:/ruta/falsa/VACANCIA.xlsx',
            motivo='Reporte de Vacancia Oficializado',
            lote_reporte=self.lote,
            datos_tramite={
                'tipo_vacante': 'Temporal',
                'tipo_movimiento': 'LICENCIA POR BECA',
                'fecha_inicio': '2026-11-01',
                'fecha_final': '2027-06-30',
                'clave_presupuestal': '071004E068700.0807031',
            },
        )
        self.client.force_login(self.user)

    def _crear_vacancia(self, **kwargs):
        datos = {
            'lote': self.lote,
            'maestro_titular': self.maestro,
            'apreciacion': self.apreciacion,
            'tipo_vacante': 'TEMPORAL',
            'plantilla_doc': 'NORMAL',
            'tipo_movimiento_original': 'LICENCIA POR BECA',
            'fecha_inicio': date(2026, 11, 1),
            'fecha_final': date(2027, 6, 30),
            'observaciones': 'ORIGINAL',
            'municipio': 'DURANGO',
            'direccion': 'ESCUELA DE PRUEBA',
            'zona_economica': 'Zona III',
            'destino': 'Admisión',
            'tipo_plaza': 'JORNADA',
            'sostenimiento': 'Federalizado',
            'categoria': 'E0687',
            'clave_presupuestal': '071004E068700.0807031',
            'techo_financiero': 'TECHO',
            'clave_ct': '10DML0002K',
            'turno': 'Matutino',
            'nombre_titular_reporte': 'PEREZ LOPEZ JUAN',
        }
        datos.update(kwargs)
        return Vacancia.objects.create(**datos)

    def _datos_post(self, **kwargs):
        datos = {
            'maestro_titular': str(self.maestro.pk),
            'maestro_interino': '',
            'apreciacion': str(self.apreciacion.pk),
            'tipo_vacante': 'TEMPORAL',
            'plantilla_doc': 'NORMAL',
            'tipo_movimiento_original': 'LICENCIA POR BECA',
            'fecha_inicio': '2026-11-17',
            'fecha_final': '2027-12-30',
            'observaciones': 'CORREGIDO',
            'pseudoplaza': '',
            'from': 'kardex',
        }
        datos.update(kwargs)
        return datos

    def test_formulario_de_correccion_muestra_boton_guardar(self):
        r = self.client.get(f'/historial/corregir_vacancia/{self.historial.id}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Guardar y regenerar')
        self.assertContains(r, 'PEREZ LOPEZ JUAN')
        self.assertNotContains(r, 'name="maestro_titular"')

    def test_post_actualiza_vacancia_y_regenera_documentos(self):
        with patch(
            'gestion_escolar.views.vacancias._regenerar_documentos_lote'
        ) as regenerar:
            r = self.client.post(
                f'/historial/corregir_vacancia/{self.historial.id}/',
                self._datos_post(),
            )

        self.assertRedirects(
            r,
            f'/historial/detalle_tramite/{self.historial.id}/?from=kardex',
            fetch_redirect_response=False,
        )
        self.vacancia.refresh_from_db()
        self.assertEqual(self.vacancia.fecha_inicio, date(2026, 11, 17))
        self.assertEqual(self.vacancia.fecha_final, date(2027, 12, 30))
        self.assertEqual(self.vacancia.observaciones, 'CORREGIDO')
        regenerar.assert_called_once_with(self.lote)

    def test_usuario_sin_permiso_no_puede_corregir(self):
        self.client.force_login(self.otro_user)

        with patch(
            'gestion_escolar.views.vacancias._regenerar_documentos_lote'
        ) as regenerar:
            r = self.client.post(
                f'/historial/corregir_vacancia/{self.historial.id}/',
                self._datos_post(),
            )

        self.assertEqual(r.status_code, 302)
        regenerar.assert_not_called()
        self.vacancia.refresh_from_db()
        self.assertEqual(self.vacancia.observaciones, 'ORIGINAL')

    def test_falla_de_regeneracion_no_guarda_correccion(self):
        with patch(
            'gestion_escolar.views.vacancias._regenerar_documentos_lote',
            side_effect=RuntimeError('sin plantilla'),
        ):
            r = self.client.post(
                f'/historial/corregir_vacancia/{self.historial.id}/',
                self._datos_post(),
            )

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No se pudieron regenerar los documentos')
        self.vacancia.refresh_from_db()
        self.assertEqual(self.vacancia.observaciones, 'ORIGINAL')
        self.assertEqual(self.vacancia.fecha_inicio, date(2026, 11, 1))

    def test_varias_vacancias_pide_elegir_cual_corregir(self):
        self._crear_vacancia(observaciones='SEGUNDA')
        self.historial.datos_tramite = None
        self.historial.save(update_fields=['datos_tramite'])

        r = self.client.get(f'/historial/corregir_vacancia/{self.historial.id}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Elige la vacancia a corregir')
        self.assertContains(r, f'?vacancia={self.vacancia.id}')

    def test_ficha_muestra_boton_corregir_datos(self):
        r = self.client.get(f'/historial/detalle_tramite/{self.historial.id}/')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Corregir datos')
        self.assertContains(
            r, f'/historial/corregir_vacancia/{self.historial.id}/'
        )


class DisenadorPlantillasTests(TestCase):
    """Diseñador de plantillas: permisos, configuración y formulario dinámico."""

    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            username='root_plantillas', email='root@example.com', password='x'
        )
        self.grupo_admin, _ = Group.objects.get_or_create(name='ADMINISTRADOR')
        self.admin = User.objects.create_user(
            username='admin_plantillas', password='x'
        )
        self.admin.groups.add(self.grupo_admin)
        self.regular = User.objects.create_user(
            username='normal_plantillas', password='x'
        )
        # /ajustes/ exige el permiso acceder_ajustes; se otorga a ambos para
        # comprobar que la tarjeta solo la ve el grupo ADMINISTRADOR.
        permiso_ajustes = Permission.objects.filter(
            codename='acceder_ajustes',
            content_type__app_label='gestion_escolar').first()
        if permiso_ajustes:
            self.admin.user_permissions.add(permiso_ajustes)
            self.regular.user_permissions.add(permiso_ajustes)
        self.motivo, _ = MotivoTramite.objects.get_or_create(
            id=901, defaults={'motivo_tramite': 'MOTIVO DE PRUEBA'}
        )
        self.sistema = PlantillaTramite.objects.create(
            nombre='PLANTILLA SISTEMA PRUEBA',
            ruta_archivo='gestion_escolar/templates/tramites/Plantillas/Word/NO_EXISTE.docx',
            tipo_documento='TRAMITE',
            es_sistema=True,
            activa=True,
            configuracion=config_sistema('REINGRESO'),
            variables_detectadas=['Nombre_Titular'],
        )

    # ------------------------------------------------------------------
    # Utilidades de prueba
    # ------------------------------------------------------------------
    @staticmethod
    def _docx_bytes(runs, header_runs=None):
        """Crea un .docx mínimo con los textos indicados, run por run."""
        ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        def parrafo(textos):
            contenido = ''.join(
                f'<w:r><w:t xml:space="preserve">{texto}</w:t></w:r>'
                for texto in textos
            )
            return f'<w:p>{contenido}</w:p>'

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archivo:
            archivo.writestr(
                'word/document.xml',
                '<?xml version="1.0" encoding="UTF-8"?>'
                f'<w:document xmlns:w="{ns}"><w:body>'
                f'{parrafo(runs)}</w:body></w:document>',
            )
            if header_runs is not None:
                archivo.writestr(
                    'word/header1.xml',
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    f'<w:hdr xmlns:w="{ns}">{parrafo(header_runs)}</w:hdr>',
                )
        return buffer.getvalue()

    def _crear_plantilla_usuario(self, nombre='PLANTILLA USUARIO',
                                 tipo='TRAMITE', config=None):
        return PlantillaTramite.objects.create(
            nombre=nombre,
            ruta_archivo='gestion_escolar/templates/tramites/Plantillas/Word/NO_EXISTE.docx',
            tipo_documento=tipo,
            es_sistema=False,
            activa=True,
            configuracion=config if config is not None else config_vacia(),
            variables_detectadas=['Numero_Oficio'],
        )

    def _config_con_campo_personalizado(self):
        config = config_vacia()
        config.update({
            'campos': ['folio'],
            'requeridos': ['folio'],
            'campos_personalizados': [{
                'variable': 'Numero_Oficio',
                'etiqueta': 'Número de oficio',
                'tipo': 'texto',
                'ayuda': 'Captura el número del oficio',
                'requerido': True,
                'opciones': [],
            }],
        })
        return config

    # ------------------------------------------------------------------
    # Permisos y acceso desde Ajustes
    # ------------------------------------------------------------------
    def test_anonimo_se_envia_al_login(self):
        r = self.client.get(reverse('lista_plantillas'))

        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r.url)

    def test_usuario_sin_grupo_no_accede(self):
        self.client.force_login(self.regular)

        self.assertEqual(
            self.client.get(reverse('lista_plantillas')).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('crear_plantilla')).status_code, 403)
        self.assertEqual(
            self.client.post(reverse('crear_plantilla'), {}).status_code, 403)

    def test_usuario_del_grupo_administrador_accede(self):
        self.client.force_login(self.admin)

        r = self.client.get(reverse('lista_plantillas'))

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nueva plantilla')
        self.assertContains(r, self.sistema.nombre)

    def test_superusuario_accede(self):
        self.client.force_login(self.superuser)

        self.assertEqual(
            self.client.get(reverse('lista_plantillas')).status_code, 200)

    def test_es_administrador(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertTrue(es_administrador(self.superuser))
        self.assertTrue(es_administrador(self.admin))
        self.assertFalse(es_administrador(self.regular))
        self.assertFalse(es_administrador(AnonymousUser()))

    def test_ajustes_muestra_tarjeta_solo_a_administradores(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('ajustes'))
        self.assertContains(r, 'Plantillas de Word')
        self.assertContains(r, reverse('lista_plantillas'))

        self.client.force_login(self.regular)
        r = self.client.get(reverse('ajustes'))
        self.assertNotContains(r, 'Plantillas de Word')

    # ------------------------------------------------------------------
    # Plantillas del sistema (no editables)
    # ------------------------------------------------------------------
    def test_plantillas_del_sistema_son_solo_lectura(self):
        for plantilla in PlantillaTramite.objects.filter(es_sistema=True):
            self.assertFalse(plantilla.es_editable)
            self.assertIsInstance(plantilla.configuracion, dict)
            self.assertTrue(plantilla.configuracion.get('campos'))

    def test_configuracion_migrada_coincide_con_el_catalogo(self):
        # 23 plantillas históricas + la variante Art. 36 de la solicitud.
        self.assertGreaterEqual(len(PLANTILLAS_SISTEMA), 23)
        self.assertIn('REINGRESO', PLANTILLAS_SISTEMA)
        self.assertIn('SOLICITUD DE ASIGNACION 36', PLANTILLAS_SISTEMA)

        plantilla = PlantillaTramite.objects.filter(
            nombre__iexact='CONSTANCIA DE CAMBIO').first()
        self.assertIsNotNone(plantilla)
        self.assertTrue(plantilla.es_sistema)
        esperada = config_sistema('CONSTANCIA DE CAMBIO')
        self.assertEqual(plantilla.configuracion['campos'], esperada['campos'])
        self.assertEqual(
            plantilla.configuracion['requeridos'], esperada['requeridos'])
        self.assertTrue(plantilla.configuracion['calcular_antiguedad'])

    def test_sistema_no_se_edita_por_post(self):
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('editar_plantilla', args=[self.sistema.pk]),
            {'nombre': 'NOMBRE CAMBIADO', 'tipo_documento': 'OFICIO'},
        )

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no se puede editar')
        self.sistema.refresh_from_db()
        self.assertEqual(self.sistema.nombre, 'PLANTILLA SISTEMA PRUEBA')
        self.assertEqual(self.sistema.tipo_documento, 'TRAMITE')

    def test_sistema_no_se_elimina(self):
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('eliminar_plantilla', args=[self.sistema.pk]))

        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            PlantillaTramite.objects.filter(pk=self.sistema.pk).exists())

    def test_sistema_no_se_desactiva(self):
        self.client.force_login(self.admin)

        self.client.post(reverse('alternar_plantilla', args=[self.sistema.pk]))

        self.sistema.refresh_from_db()
        self.assertTrue(self.sistema.activa)

    def test_duplicar_sistema_crea_copia_editable(self):
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('duplicar_plantilla', args=[self.sistema.pk]))

        copia = PlantillaTramite.objects.get(
            nombre__startswith=self.sistema.nombre + ' COPIA')
        self.assertEqual(r.status_code, 302)
        self.assertRedirects(
            r, reverse('editar_plantilla', args=[copia.pk]),
            fetch_redirect_response=False)
        self.assertFalse(copia.es_sistema)
        self.assertTrue(copia.es_editable)
        self.assertTrue(copia.activa)
        self.assertEqual(copia.configuracion['origen'], 'usuario')
        self.assertEqual(
            copia.configuracion['campos'],
            self.sistema.configuracion['campos'])

    # ------------------------------------------------------------------
    # Detección de variables del .docx
    # ------------------------------------------------------------------
    def test_detecta_variables_del_documento(self):
        variables, advertencias = extraer_variables_docx(
            io.BytesIO(self._docx_bytes(
                ['{{ Nombre_Titular }}', ' y ', '{{ Folio_Manual }}']))
        )

        self.assertEqual(variables, ['Folio_Manual', 'Nombre_Titular'])
        self.assertEqual(advertencias, [])

    def test_detecta_variable_partida_entre_runs(self):
        variables, advertencias = extraer_variables_docx(
            io.BytesIO(self._docx_bytes(['{{ Nom', 'bre_Titular }}']))
        )

        self.assertEqual(variables, ['Nombre_Titular'])
        self.assertTrue(
            any('Word dividió' in aviso for aviso in advertencias))

    def test_detecta_variables_en_encabezado(self):
        variables, _ = extraer_variables_docx(
            io.BytesIO(self._docx_bytes(
                ['{{ Nombre_Titular }}'], header_runs=['{{ Folio }}']))
        )

        self.assertIn('Folio', variables)
        self.assertIn('Nombre_Titular', variables)

    def test_archivo_invalido_devuelve_advertencia(self):
        variables, advertencias = extraer_variables_docx(
            io.BytesIO(b'esto no es un docx'))

        self.assertEqual(variables, [])
        self.assertTrue(advertencias)

    def test_guardar_docx_valida_extension_y_formato(self):
        with self.assertRaisesMessage(ValueError, 'documento de Word'):
            guardar_docx_subido(
                SimpleUploadedFile('archivo.txt', b'texto'), 'PRUEBA')

        with self.assertRaisesMessage(ValueError, 'no es un .docx válido'):
            guardar_docx_subido(
                SimpleUploadedFile('archivo.docx', b'no es zip'), 'PRUEBA')

    # ------------------------------------------------------------------
    # Alta de plantillas
    # ------------------------------------------------------------------
    def test_crear_plantilla_exige_archivo(self):
        self.client.force_login(self.admin)

        r = self.client.post(reverse('crear_plantilla'), {
            'nombre': 'SIN ARCHIVO',
            'tipo_documento': 'TRAMITE',
        })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Selecciona el archivo .docx')
        self.assertFalse(
            PlantillaTramite.objects.filter(nombre='SIN ARCHIVO').exists())

    def test_crear_plantilla_con_docx(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        archivo = SimpleUploadedFile(
            'mi_plantilla.docx',
            self._docx_bytes([
                '{{ Nombre_Titular }}', ' / ', '{{ Folio_Manual }}']),
            content_type=(
                'application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.document'),
        )
        self.client.force_login(self.admin)

        with patch('gestion_escolar.plantillas_utils.PLANTILLAS_WORD_DIR', tmp), \
                patch('gestion_escolar.plantillas_utils.REL_PLANTILLAS_WORD_DIR',
                      'plantillas_prueba'):
            r = self.client.post(reverse('crear_plantilla'), {
                'nombre': 'MI PLANTILLA NUEVA',
                'tipo_documento': 'TRAMITE',
                'descripcion': 'Plantilla de prueba',
                'archivo_docx': archivo,
            })

        plantilla = PlantillaTramite.objects.get(nombre='MI PLANTILLA NUEVA')
        self.assertEqual(r.status_code, 302)
        self.assertRedirects(
            r, reverse('editar_plantilla', args=[plantilla.pk]),
            fetch_redirect_response=False)
        self.assertFalse(plantilla.es_sistema)
        self.assertTrue(plantilla.activa)
        self.assertEqual(
            plantilla.configuracion['campos'],
            ['maestro_titular', 'folio', 'observaciones'])
        self.assertEqual(
            plantilla.variables_detectadas,
            ['Folio_Manual', 'Nombre_Titular'])
        self.assertTrue(os.path.exists(
            os.path.join(tmp, os.path.basename(plantilla.ruta_archivo))))

    def test_crear_plantilla_duplicada_se_rechaza(self):
        self.client.force_login(self.admin)

        r = self.client.post(reverse('crear_plantilla'), {
            'nombre': self.sistema.nombre,
            'tipo_documento': 'TRAMITE',
        })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una plantilla')
        self.assertEqual(
            PlantillaTramite.objects.filter(
                nombre=self.sistema.nombre).count(), 1)

    # ------------------------------------------------------------------
    # Edición y configuración
    # ------------------------------------------------------------------
    def test_editar_plantilla_guarda_configuracion(self):
        plantilla = self._crear_plantilla_usuario()
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('editar_plantilla', args=[plantilla.pk]), {
                'nombre': 'plantilla usuario editada',
                'tipo_documento': 'TRAMITE',
                'descripcion': 'Ahora con folio obligatorio',
                'campos': ['folio', 'observaciones'],
                'requeridos': ['folio'],
                'mostrar_motivo': 'on',
                'motivos': [str(self.motivo.id)],
                'calcular_antiguedad': 'on',
                'custom_variable': ['Numero_Oficio'],
                'custom_etiqueta': ['Número de oficio'],
                'custom_tipo': ['texto'],
                'custom_ayuda': ['Captura el número'],
                'custom_opciones': [''],
                'custom_requerido': ['0'],
            })

        self.assertEqual(r.status_code, 302)
        plantilla.refresh_from_db()
        self.assertEqual(plantilla.nombre, 'PLANTILLA USUARIO EDITADA')
        self.assertEqual(
            plantilla.configuracion['campos'], ['folio', 'observaciones'])
        self.assertEqual(plantilla.configuracion['requeridos'], ['folio'])
        self.assertTrue(plantilla.configuracion['mostrar_motivo'])
        self.assertEqual(
            plantilla.configuracion['motivos'], [self.motivo.id])
        self.assertTrue(plantilla.configuracion['calcular_antiguedad'])
        personalizado = plantilla.configuracion['campos_personalizados'][0]
        self.assertEqual(personalizado['variable'], 'Numero_Oficio')
        self.assertTrue(personalizado['requerido'])

    def test_editar_plantilla_rechaza_variable_invalida(self):
        config = config_vacia()
        config['campos'] = ['folio']
        plantilla = self._crear_plantilla_usuario(config=config)
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('editar_plantilla', args=[plantilla.pk]), {
                'nombre': plantilla.nombre,
                'tipo_documento': 'TRAMITE',
                'campos': ['folio'],
                'custom_variable': ['Numero Malo'],
                'custom_etiqueta': ['Número malo'],
                'custom_tipo': ['texto'],
            })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no es válida')
        plantilla.refresh_from_db()
        self.assertEqual(plantilla.configuracion['campos'], ['folio'])
        self.assertEqual(
            plantilla.configuracion['campos_personalizados'], [])

    def test_editar_plantilla_rechaza_lista_sin_opciones(self):
        plantilla = self._crear_plantilla_usuario()
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('editar_plantilla', args=[plantilla.pk]), {
                'nombre': plantilla.nombre,
                'tipo_documento': 'TRAMITE',
                'campos': ['folio'],
                'custom_variable': ['Color'],
                'custom_etiqueta': ['Color'],
                'custom_tipo': ['opciones'],
                'custom_opciones': [''],
            })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'necesita al menos una opción')

    def test_editar_plantilla_exige_al_menos_un_campo(self):
        plantilla = self._crear_plantilla_usuario()
        self.client.force_login(self.admin)

        r = self.client.post(
            reverse('editar_plantilla', args=[plantilla.pk]), {
                'nombre': plantilla.nombre,
                'tipo_documento': 'TRAMITE',
            })

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Marca al menos un campo')

    # ------------------------------------------------------------------
    # Formulario dinámico de generación
    # ------------------------------------------------------------------
    def test_formulario_respeta_campos_configurados(self):
        config = config_vacia()
        config.update({
            'campos': ['folio', 'observaciones'],
            'requeridos': ['folio'],
        })
        plantilla = self._crear_plantilla_usuario(config=config)

        form = TramiteForm(form_type='tramites', plantilla_id=plantilla.pk)

        self.assertEqual(form.plantilla_seleccionada, plantilla)
        self.assertTrue(form.fields['folio'].required)
        self.assertFalse(form.fields['maestro_titular'].required)
        self.assertFalse(form.fields['observaciones'].required)
        self.assertTrue(form.campos_visibles >= {'folio', 'observaciones'})

        valido = TramiteForm(
            {'plantilla': plantilla.pk, 'folio': 'OF-1'},
            form_type='tramites')
        self.assertTrue(valido.is_valid(), valido.errors)

        incompleto = TramiteForm(
            {'plantilla': plantilla.pk}, form_type='tramites')
        self.assertFalse(incompleto.is_valid())
        self.assertIn('folio', incompleto.errors)

    def test_formulario_campos_personalizados_por_tipo(self):
        config = config_vacia()
        config.update({
            'campos': ['folio'],
            'campos_personalizados': [
                {'variable': 'Fecha_Entrega', 'etiqueta': 'Fecha de entrega',
                 'tipo': 'fecha', 'requerido': False, 'ayuda': '',
                 'opciones': []},
                {'variable': 'Monto', 'etiqueta': 'Monto',
                 'tipo': 'numero', 'requerido': False, 'ayuda': '',
                 'opciones': []},
                {'variable': 'Turno_Entrega', 'etiqueta': 'Turno',
                 'tipo': 'opciones', 'requerido': False, 'ayuda': '',
                 'opciones': ['MATUTINO', 'VESPERTINO']},
            ],
        })
        plantilla = self._crear_plantilla_usuario(config=config)

        form = TramiteForm(form_type='tramites', plantilla_id=plantilla.pk)

        nombre_fecha = f'custom_{plantilla.pk}_Fecha_Entrega'
        nombre_monto = f'custom_{plantilla.pk}_Monto'
        nombre_turno = f'custom_{plantilla.pk}_Turno_Entrega'
        self.assertEqual(form.fields[nombre_fecha].widget.input_type, 'date')
        self.assertEqual(
            form.fields[nombre_monto].__class__.__name__, 'DecimalField')
        opciones = [
            valor for valor, _ in form.fields[nombre_turno].choices]
        self.assertIn('MATUTINO', opciones)
        self.assertIn('VESPERTINO', opciones)
        self.assertEqual(len(form.campos_personalizados), 3)

    def test_formulario_campo_personalizado_requerido(self):
        plantilla = self._crear_plantilla_usuario(
            config=self._config_con_campo_personalizado())
        nombre_campo = f'custom_{plantilla.pk}_Numero_Oficio'

        form = TramiteForm(form_type='tramites', plantilla_id=plantilla.pk)
        self.assertIn(nombre_campo, form.fields)
        self.assertTrue(form.fields[nombre_campo].required)

        incompleto = TramiteForm(
            {'plantilla': plantilla.pk, 'folio': 'OF-1'},
            form_type='tramites')
        self.assertFalse(incompleto.is_valid())
        self.assertIn(nombre_campo, incompleto.errors)

        completo = TramiteForm(
            {'plantilla': plantilla.pk, 'folio': 'OF-1',
             nombre_campo: 'OF-123'},
            form_type='tramites')
        self.assertTrue(completo.is_valid(), completo.errors)
        self.assertEqual(completo.cleaned_data[nombre_campo], 'OF-123')

    def test_formulario_no_ofrece_plantillas_inactivas(self):
        plantilla = self._crear_plantilla_usuario()
        plantilla.activa = False
        plantilla.save(update_fields=['activa'])

        form = TramiteForm(form_type='tramites')

        self.assertNotIn(
            plantilla, list(form.fields['plantilla'].queryset))

    def test_motivos_salen_de_la_configuracion(self):
        config = config_vacia()
        config.update({
            'campos': ['folio'],
            'mostrar_motivo': True,
            'motivos': [self.motivo.id],
        })
        plantilla = self._crear_plantilla_usuario(config=config)

        self.assertEqual(ids_permitidos(plantilla.nombre), [self.motivo.id])

        config['motivos'] = []
        plantilla.configuracion = config
        plantilla.save(update_fields=['configuracion'])

        self.assertEqual(ids_permitidos(plantilla.nombre), [])

    def test_alta_inicial_sugiere_su_unico_motivo(self):
        """ALTA INICIAL (09) preselecciona ALTA INICIAL aunque la config
        guardada no traiga ``motivo_auto``."""
        MotivoTramite.objects.get_or_create(
            id=39, defaults={'motivo_tramite': 'ALTA INICIAL'})
        plantilla, _ = PlantillaTramite.objects.get_or_create(
            nombre='ALTA INICIAL (09)',
            defaults={
                'ruta_archivo': 'gestion_escolar/templates/tramites/Plantillas/Word/NO_EXISTE.docx',
                'tipo_documento': 'TRAMITE',
                'es_sistema': True,
                'activa': True,
                'configuracion': config_sistema('ALTA INICIAL (09)'),
            },
        )
        config = dict(plantilla.configuracion or {})
        config.update({'mostrar_motivo': True, 'motivos': [39], 'motivo_auto': None})
        plantilla.configuracion = config
        plantilla.save(update_fields=['configuracion'])

        self.assertEqual(config_para_js(plantilla)['motivo_auto'], 39)

    # ------------------------------------------------------------------
    # Integración con la generación de documentos
    # ------------------------------------------------------------------
    def test_probar_plantilla_redirige_a_su_formulario(self):
        tramite = self._crear_plantilla_usuario(nombre='PLANTILLA TRAMITE')
        oficio = self._crear_plantilla_usuario(
            nombre='PLANTILLA OFICIO', tipo='OFICIO')
        self.client.force_login(self.admin)

        r_tramite = self.client.get(
            reverse('probar_plantilla', args=[tramite.pk]))
        r_oficio = self.client.get(
            reverse('probar_plantilla', args=[oficio.pk]))

        self.assertRedirects(
            r_tramite,
            reverse('generar_tramites_generales') + f'?plantilla={tramite.pk}',
            fetch_redirect_response=False)
        self.assertRedirects(
            r_oficio,
            reverse('generar_oficios') + f'?plantilla={oficio.pk}',
            fetch_redirect_response=False)

    def test_generar_tramite_muestra_campos_personalizados(self):
        plantilla = self._crear_plantilla_usuario(
            nombre='PLANTILLA CON CAMPO',
            config=self._config_con_campo_personalizado())
        self.client.force_login(self.superuser)

        r = self.client.get(
            reverse('generar_tramites_generales') + f'?plantilla={plantilla.pk}')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Datos Adicionales')
        self.assertContains(r, 'Número de oficio')
        self.assertContains(r, 'visibleFieldsConfig')
        self.assertContains(r, plantilla.nombre)

    def test_generar_oficios_carga_plantilla_de_oficio(self):
        plantilla = self._crear_plantilla_usuario(
            nombre='OFICIO DE PRUEBA', tipo='OFICIO')
        self.client.force_login(self.superuser)

        r = self.client.get(
            reverse('generar_oficios') + f'?plantilla={plantilla.pk}')

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, plantilla.nombre)


class MaestroNombreVisibleTests(TestCase):
    """Los registros sin nombre no deben imprimir 'None None None'."""

    def test_plaza_sin_docente_usa_etiqueta_y_plaza(self):
        plaza = Maestro.objects.create(num_plaza='806004', status='ACTIVO')
        self.assertTrue(plaza.es_plaza_sin_docente)
        self.assertEqual(plaza.nombre_completo_registro, '')
        self.assertEqual(plaza.nombre_visible, 'PLAZA VACANTE (Plaza 806004)')

    def test_nombre_completo_limpia_espacios(self):
        maestro = Maestro.objects.create(
            a_paterno=' CHACON ', a_materno='LOPEZ', nombres=' EMMA  ROSALIA ')
        self.assertFalse(maestro.es_plaza_sin_docente)
        self.assertEqual(maestro.nombre_completo_registro, 'EMMA  ROSALIA CHACON LOPEZ')

    def test_registro_marcado_duplicado_no_usar(self):
        maestro = Maestro.objects.create(
            observaciones='DUPLICADO HISTORICO - NO USAR')
        self.assertTrue(maestro.es_registro_duplicado_no_usar)
        self.assertEqual(maestro.nombre_visible, 'REGISTRO DUPLICADO / NO USAR')

    def test_vacancia_corrige_nombre_none(self):
        user = get_user_model().objects.create_user(username='u', password='x')
        lote = LoteReporteVacancia.objects.create(usuario_generador=user)
        maestro = Maestro.objects.create(nombres='EMMA', a_paterno='CHACON')
        vacancia = Vacancia.objects.create(
            lote=lote,
            maestro_titular=maestro,
            apreciacion=TipoApreciacion.objects.create(descripcion='LICENCIA'),
            tipo_vacante='TEMPORAL',
            fecha_inicio=date(2026, 1, 1),
            nombre_titular_reporte='None None None',
            municipio='DURANGO',
            direccion='ESCUELA',
            zona_economica='Zona III',
            destino='Admisión',
            tipo_plaza='JORNADA',
            sostenimiento='Federalizado',
            categoria='E0687',
            clave_presupuestal='CLAVE',
            techo_financiero='TECHO',
            clave_ct='10DML0002K',
            turno='Matutino',
        )
        self.assertEqual(vacancia.nombre_titular_visible, 'EMMA CHACON')


class MaestroFormNombreTests(TestCase):
    """Bloquear maestros sin nombre salvo que se marquen como plaza vacante."""

    def test_sin_nombre_se_bloquea(self):
        form = MaestroForm(
            data={'nombres': '', 'a_paterno': ''},
            validar_curp_rfc=True,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('nombres'))
        self.assertTrue(form.has_error('a_paterno'))
        self.assertIn('plaza vacante', form.errors['nombres'][0])

    def test_sin_nombre_pero_plaza_vacante_es_valido(self):
        form = MaestroForm(
            data={'nombres': '', 'a_paterno': '', 'es_plaza_vacante': 'on'},
            validar_curp_rfc=True,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_con_nombre_es_valido(self):
        form = MaestroForm(
            data={'nombres': 'EMMA', 'a_paterno': 'CHACON'},
            validar_curp_rfc=True,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_editar_plaza_vacante_la_deja_marcada(self):
        plaza = Maestro.objects.create(num_plaza='806004')
        form = MaestroForm(instance=plaza, validar_curp_rfc=True)
        self.assertTrue(form.fields['es_plaza_vacante'].initial)


class PlazaVacanteReclamacionTests(TestCase):
    """Buscar y reutilizar una plaza de nueva creación al registrar al docente."""

    def setUp(self):
        self.categoria = Categoria.objects.create(
            id_categoria='E0687', descripcion='CATEGORIA', horas='00.0')
        self.plaza = self._crear_plaza()

    def _crear_plaza(self, **kwargs):
        datos = {
            'dep': '07',
            'unid': '10',
            'sub_unid': '04',
            'categog': self.categoria,
            'hrs': '00.0',
            'num_plaza': '806004',
            'status': 'ACTIVO',
        }
        datos.update(kwargs)
        return Maestro.objects.create(**datos)

    def _datos_docente(self):
        return {
            'dep': '07',
            'unid': '10',
            'sub_unid': '04',
            'categog': self.categoria.pk,
            'hrs': '00.0',
            'num_plaza': '806004',
            'nombres': 'EMMA ROSALIA',
            'a_paterno': 'CHACON',
            'a_materno': 'LOPEZ',
        }

    def test_buscar_por_clave_devuelve_la_plaza(self):
        encontrada = buscar_plaza_vacante(
            clave_presupuestal=self.plaza.clave_presupuestal)
        self.assertEqual(encontrada.pk, self.plaza.pk)

    def test_buscar_excluye_marcadas_no_usar(self):
        self.plaza.observaciones = 'DUPLICADO / NO USAR'
        self.plaza.save()
        self.assertIsNone(buscar_plaza_vacante(
            clave_presupuestal=self.plaza.clave_presupuestal))

    def test_reclamar_copia_datos_y_conserva_observacion(self):
        self.plaza.observaciones = 'NUEVA CREACION Y EN ESPERA DE DOCENTE TITULAR'
        self.plaza.save()
        form = MaestroForm(data=self._datos_docente(), validar_curp_rfc=True)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        antes = Maestro.objects.count()

        reclamada = reclamar_plaza_vacante(self.plaza, form)

        self.assertEqual(Maestro.objects.count(), antes)
        self.assertEqual(reclamada.pk, self.plaza.pk)
        self.assertEqual(reclamada.nombre_completo_registro, 'EMMA ROSALIA CHACON LOPEZ')
        self.assertEqual(
            reclamada.observaciones,
            'NUEVA CREACION Y EN ESPERA DE DOCENTE TITULAR')


class AgregarMaestroPlazaVacanteViewTests(TestCase):
    """El alta de maestro debe ofrecer reclamar la plaza vacante antes de duplicar."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='tester', email='tester@example.com', password='x')
        self.categoria = Categoria.objects.create(
            id_categoria='E0687', descripcion='CATEGORIA', horas='00.0')
        self.plaza = Maestro.objects.create(
            dep='07', unid='10', sub_unid='04', categog=self.categoria,
            hrs='00.0', num_plaza='806004', status='ACTIVO',
            observaciones='NUEVA CREACION Y EN ESPERA DE DOCENTE TITULAR')
        self.client.force_login(self.user)

    def _datos(self):
        return {
            'dep': '07',
            'unid': '10',
            'sub_unid': '04',
            'categog': self.categoria.pk,
            'hrs': '00.0',
            'num_plaza': '806004',
            'nombres': 'EMMA ROSALIA',
            'a_paterno': 'CHACON',
            'a_materno': 'LOPEZ',
        }

    def test_primero_pide_confirmacion_sin_crear(self):
        r = self.client.post(reverse('agregar_maestro'), self._datos())

        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Se encontró una plaza vacante con la misma clave')
        self.assertContains(r, 'Asignar esta plaza')
        self.assertEqual(Maestro.objects.count(), 1)
        self.plaza.refresh_from_db()
        self.assertTrue(self.plaza.es_plaza_sin_docente)

    def test_confirmar_reutiliza_la_plaza(self):
        datos = self._datos()
        datos['confirmar_reclamar'] = self.plaza.pk

        r = self.client.post(reverse('agregar_maestro'), datos)

        self.assertRedirects(
            r, reverse('detalle_maestro', args=[self.plaza.pk]),
            fetch_redirect_response=False)
        self.assertEqual(Maestro.objects.count(), 1)
        self.plaza.refresh_from_db()
        self.assertEqual(
            self.plaza.nombre_completo_registro, 'EMMA ROSALIA CHACON LOPEZ')
        self.assertIn('NUEVA CREACION', self.plaza.observaciones)

    def test_crear_registro_nuevo_no_reutiliza(self):
        datos = self._datos()
        datos['crear_registro_nuevo'] = '1'

        self.client.post(reverse('agregar_maestro'), datos)

        self.assertEqual(Maestro.objects.count(), 2)
        self.plaza.refresh_from_db()
        self.assertTrue(self.plaza.es_plaza_sin_docente)


class FusionarMaestroTests(TestCase):
    """La fusión conserva historial/kardex y corrige nombres en vacantes."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='u', password='x')
        self.categoria = Categoria.objects.create(
            id_categoria='E0687', descripcion='CATEGORIA', horas='00.0')
        self.conservar = Maestro.objects.create(
            id_maestro='01669', nombres='EMMA ROSALIA', a_paterno='CHACON',
            a_materno='LOPEZ', curp=CURP_VALIDA_1985,
            observaciones='EN SUSTITUCION DE TITULAR',
            dep='07', unid='10', sub_unid='04', categog=self.categoria,
            hrs='00.0', num_plaza='806004')
        self.eliminar = Maestro.objects.create(
            id_maestro='01668', status='INACTIVO',
            observaciones='NUEVA CREACION Y EN ESPERA DE DOCENTE TITULAR',
            dep='07', unid='10', sub_unid='04', categog=self.categoria,
            hrs='00.0', num_plaza='806004')
        self.lote = LoteReporteVacancia.objects.create(usuario_generador=self.user)
        self.vacancia = Vacancia.objects.create(
            lote=self.lote,
            maestro_titular=self.eliminar,
            maestro_interino=self.conservar,
            apreciacion=TipoApreciacion.objects.create(descripcion='LICENCIA'),
            tipo_vacante='TEMPORAL',
            fecha_inicio=date(2026, 1, 1),
            nombre_titular_reporte='None None None',
            nombre_interino='None None None',
            municipio='DURANGO',
            direccion='ESCUELA',
            zona_economica='Zona III',
            destino='Admisión',
            tipo_plaza='JORNADA',
            sostenimiento='Federalizado',
            categoria='E0687',
            clave_presupuestal='CLAVE',
            techo_financiero='TECHO',
            clave_ct='10DML0002K',
            turno='Matutino',
        )
        self.historial = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Validación EO (Individual)',
            maestro=self.eliminar,
            ruta_archivo='C:/ruta/falsa/EO.xlsx',
        )
        self.kardex = KardexMovimiento.objects.create(
            maestro=self.eliminar,
            usuario=self.user,
            descripcion='ALTA DE PLAZA',
        )

    def _fusionar(self, **extra):
        call_command(
            'fusionar_maestro',
            conservar=self.conservar.pk,
            eliminar=self.eliminar.pk,
            stdout=io.StringIO(),
            **extra)

    def test_fusion_reapunta_y_corrige_nombres(self):
        self._fusionar()

        self.assertFalse(Maestro.objects.filter(pk='01668').exists())
        self.conservar.refresh_from_db()
        self.assertEqual(
            self.conservar.observaciones,
            'EN SUSTITUCION DE TITULAR\nNUEVA CREACION Y EN ESPERA DE DOCENTE TITULAR')

        self.historial.refresh_from_db()
        self.kardex.refresh_from_db()
        self.vacancia.refresh_from_db()
        self.assertEqual(self.historial.maestro_id, self.conservar.pk)
        self.assertEqual(self.kardex.maestro_id, self.conservar.pk)
        self.assertEqual(self.vacancia.maestro_titular_id, self.conservar.pk)
        self.assertEqual(self.vacancia.nombre_titular_reporte, 'EMMA ROSALIA CHACON LOPEZ')
        self.assertEqual(self.vacancia.nombre_interino, 'EMMA ROSALIA CHACON LOPEZ')

    def test_modo_seco_no_modifica(self):
        self._fusionar(seco=True)

        self.assertTrue(Maestro.objects.filter(pk='01668').exists())
        self.vacancia.refresh_from_db()
        self.assertEqual(self.vacancia.nombre_titular_reporte, 'None None None')


class CancelarTramiteTests(TestCase):
    """Pruebas para la funcionalidad de cancelación y reversión de trámites/oficios."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin_cancelar', email='admin@example.com', password='pass')
        self.client.force_login(self.user)

        self.zona = Zona.objects.create(numero=1)
        self.escuela_a = Escuela.objects.create(
            id_escuela='10DPR0001A', nombre_ct='PRIMARIA A', turno='MATUTINO', zona_esc=self.zona)
        self.escuela_b = Escuela.objects.create(
            id_escuela='10DPR0002B', nombre_ct='PRIMARIA B', turno='MATUTINO', zona_esc=self.zona)

        self.categoria = Categoria.objects.create(
            id_categoria='E0281', descripcion='DOCENTE DE GRUPO')

        self.maestro = Maestro.objects.create(
            id_maestro='M001',
            curp='TEST123456HDFR00',
            rfc='TEST123456AB1',
            nombres='CARLOS',
            a_paterno='GARCIA',
            a_materno='PEREZ',
            id_escuela=self.escuela_b,
            techo_f=self.escuela_b.id_escuela,
            categog=self.categoria,
            status='ACTIVO'
        )

    def test_cancelar_tramite_simple(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - REINGRESO',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='ACTIVO'
        )

        response = self.client.post(
            reverse('cancelar_tramite', args=[item.id]),
            data=json.dumps({'motivo_cancelacion': 'Petición de supervisión'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['estado'], 'CANCELADO')

        item.refresh_from_db()
        self.assertEqual(item.estado, 'CANCELADO')
        self.assertEqual(item.motivo_cancelacion, 'Petición de supervisión')
        self.assertIsNotNone(item.fecha_cancelacion)
        self.assertEqual(item.usuario_cancelacion, self.user)

    def test_cancelar_tramite_reversion_adscripcion(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Oficio - PRESENTACION LABORAL PARA CAMBIO DE ADSCRIPCION',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='ACTIVO',
            datos_tramite={
                'escuela_anterior_id': self.escuela_a.id,
                'escuela_anterior_cct': self.escuela_a.id_escuela,
                'techo_f_anterior': self.escuela_a.id_escuela
            }
        )

        self.assertEqual(self.maestro.id_escuela, self.escuela_b)

        response = self.client.post(
            reverse('cancelar_tramite', args=[item.id]),
            data=json.dumps({'motivo_cancelacion': 'Cancelación por reubicación improcedente'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        self.maestro.refresh_from_db()
        self.assertEqual(self.maestro.id_escuela, self.escuela_a)
        self.assertEqual(self.maestro.techo_f, self.escuela_a.id_escuela)

    def test_cancelar_tramite_ya_cancelado_rechaza(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - CONSTANCIA',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='CANCELADO',
            motivo_cancelacion='Ya cancelado'
        )

        response = self.client.post(
            reverse('cancelar_tramite', args=[item.id]),
            data=json.dumps({'motivo_cancelacion': 'Otro motivo'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('ya se encuentra cancelado', response.json()['message'])

    def test_corregir_tramite_cancelado_bloqueado(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - CONSTANCIA',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='CANCELADO'
        )

        response = self.client.get(reverse('corregir_tramite', args=[item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('historial_detalle_tramite', args=[item.id]), response.url)

    def test_info_cancelar_y_cancelar_interinato(self):
        interino = Maestro.objects.create(
            id_maestro='M002',
            curp='INTER123456HDFR00',
            rfc='INTER123456AB1',
            nombres='LAURA',
            a_paterno='SANCHEZ',
            a_materno='DIAZ',
            categog=self.categoria,
            status='ACTIVO'
        )
        interinato = Interinato.objects.create(
            maestro_titular=self.maestro,
            maestro_interino=interino,
            tipo='INTERINO',
            estatus='ACTIVO',
            fecha_inicio=date(2026, 1, 1),
            fecha_final=date(2026, 6, 30)
        )
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - ALTA PROVISIONAL',
            maestro=self.maestro,
            maestro_secundario_nombre='LAURA SANCHEZ DIAZ',
            ruta_archivo='falsa.docx',
            estado='ACTIVO'
        )

        resp_info = self.client.get(reverse('info_cancelar_tramite', args=[item.id]))
        self.assertEqual(resp_info.status_code, 200)
        self.assertTrue(resp_info.json()['tiene_interinato'])

        resp_cancel = self.client.post(
            reverse('cancelar_tramite', args=[item.id]),
            data=json.dumps({'motivo_cancelacion': 'Cancelación de interinato'}),
            content_type='application/json'
        )
        self.assertEqual(resp_cancel.status_code, 200)

        interinato.refresh_from_db()
        self.assertEqual(interinato.estatus, 'CANCELADO')
        self.assertIn('Cancelado por trámite', interinato.observaciones)

    def test_eliminar_historial_no_admin_bloqueado(self):
        usuario_comun = get_user_model().objects.create_user(
            username='operador', email='operador@example.com', password='pass')
        perm = Permission.objects.get(codename='delete_historial')
        usuario_comun.user_permissions.add(perm)
        self.client.force_login(usuario_comun)

        item = Historial.objects.create(
            usuario=usuario_comun,
            tipo_documento='Trámite - CONSTANCIA',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='ACTIVO'
        )

        response = self.client.post(reverse('eliminar_historial_item', args=[item.id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Historial.objects.filter(id=item.id).exists())

    def test_eliminar_historial_admin_permitido(self):
        item = Historial.objects.create(
            usuario=self.user,
            tipo_documento='Trámite - CONSTANCIA',
            maestro=self.maestro,
            ruta_archivo='falsa.docx',
            estado='ACTIVO'
        )

        response = self.client.post(reverse('eliminar_historial_item', args=[item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Historial.objects.filter(id=item.id).exists())
