from django.db import models
from django.contrib.auth.models import User
from .validators import validate_cct_format
import re
from colorfield.fields import ColorField
from unidecode import unidecode

class Zona(models.Model):
    numero = models.IntegerField(unique=True, verbose_name="Número de Zona")
    supervisor = models.ForeignKey(
        'Maestro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Supervisor",
        related_name='zonas_supervisadas',
        limit_choices_to={'funcion__in': ['SUPERVISOR(A)']},
    )
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    
    class Meta:
        verbose_name = "Zona"
        verbose_name_plural = "Zonas"
        ordering = ['numero']
    
    def __str__(self):
        return f"Zona {self.numero}"

class Escuela(models.Model):
    TURNOS = [
        ('MATUTINO', 'Matutino'),
        ('VESPERTINO', 'Vespertino'),
        ('DISCONTINUO', 'Discontinuo'),
    ]
    
    ZONAS_ECONOMICAS = [
        ('II', 'II'),
        ('III', 'III'),
    ]
    
    SOSTENIMIENTOS = [
        ('FEDERAL', 'Federal'),
        ('ESTATAL', 'Estatal'),
    ]

    # U.D. con códigos del 001 al 011
    UNIDADES_DEPARTAMENTALES = [
        ('000', '000'),
        ('001', '001'),
        ('002', '002'),
        ('003', '003'),
        ('004', '004'),
        ('005', '005'),
        ('006', '006'),
        ('007', '007'),
        ('008', '008'),
        ('009', '009'),
        ('010', '010'),
        ('011', '011'),
        ('012', '012'),
        ('013', '013'),
    ]
    
    # ID único con formato específico (ej: 10DML0013Q)
    id_escuela = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Clave de Centro de Trabajo (CCT)",
        help_text="Formato: 2 dígitos + 3 letras + 4 dígitos + 1 letra (ej: 10DML0013Q)",
        validators=[validate_cct_format]  
    )
    nombre_ct = models.CharField(max_length=200, verbose_name="Nombre del Centro de Trabajo")
    zona_esc = models.ForeignKey(Zona, on_delete=models.CASCADE, verbose_name="Zona Escolar")
    turno = models.CharField(max_length=20, choices=TURNOS, verbose_name="Turno")
    domicilio = models.TextField(verbose_name="Domicilio")
    telefono_ct = models.CharField(
        max_length=20, 
        verbose_name="Teléfono", 
        blank=True,
        help_text="Formato: (000) 000-0000"
    )
    zona_economica = models.CharField(
        max_length=3, 
        choices=ZONAS_ECONOMICAS, 
        verbose_name="Zona Económica"
    )
    region = models.CharField(max_length=100, verbose_name="Región")
    u_d = models.CharField(
        max_length=3, 
        choices=UNIDADES_DEPARTAMENTALES, 
        verbose_name="U.D.",
        help_text="Unidad Departamental (001 al 011)"
    )
    sostenimiento = models.CharField(
        max_length=10, 
        choices=SOSTENIMIENTOS, 
        verbose_name="Sostenimiento"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Centro de Trabajo"
        verbose_name_plural = "Centros de Trabajo"
        ordering = ['nombre_ct']
        indexes = [
            models.Index(fields=['id_escuela']),
            models.Index(fields=['zona_esc']),
            models.Index(fields=['sostenimiento']),
        ]
    
    def __str__(self):
        return f"{self.nombre_ct} (CCT: {self.id_escuela})"
    
    def clean(self):
        """Validación personalizada para el formato del CCT"""
        from django.core.exceptions import ValidationError
        import re
        
        # Validar formato del CCT (ej: 10DML0013Q)
        cct_pattern = re.compile(r'^\d{2}[A-Z]{3}\d{4}[A-Z]$')
        if not cct_pattern.match(self.id_escuela):
            raise ValidationError({
                'id_escuela': 'Formato de CCT inválido. Debe ser: 2 dígitos + 3 letras + 4 dígitos + 1 letra (ej: 10DML0013Q)'
            })

class Categoria(models.Model):
    id_categoria = models.CharField(max_length=50, primary_key=True, verbose_name="ID Categoría")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['id_categoria']

    def __str__(self):
        return f"{self.id_categoria} - {self.descripcion}"

class Maestro(models.Model):
    SEXO_OPCIONES = [
        ('H', 'Hombre'),
        ('M', 'Mujer'),
    ]
    
    ESTADO_CIVIL_OPCIONES = [
        ('SOLTERO', 'Soltero(a)'),
        ('SOLTERA', 'Soltera'),
        ('CASADO', 'Casado(a)'),
        ('CASADA', 'Casada'),
        ('DIVORCIADO', 'Divorciado(a)'),
        ('VIUDO', 'Viudo(a)'),
        ('UNION_LIBRE', 'Unión Libre'),
        ('SOLTERO(A)', 'Soltero(a)'),
        ('CASADO(A)', 'Casado(a)'),
        ('', 'No especificado'),
    ]
    
    NIVEL_ESTUDIO_OPCIONES = [
        ('DRA.', 'DRA.'),
        ('PROFRA.', 'PROFRA.'),
        ('PROF.', 'PROF.'),
        ('MTRA.', 'MTRA.'),
        ('PROFR.', 'PROFR.'),
        ('PSIC.', 'PSIC.'),
        ('DR.', 'DR.'),
        ('MTRO.', 'MTRO.'),
        ('C.', 'C.'),
    ]
    
    STATUS_OPCIONES = [
        ('ACTIVO', 'Activo'),
        ('ACTIVA', 'Activa'),
        ('BAJA', 'Baja'),
        ('LICENCIA', 'Licencia'),
        ('JUBILADO', 'Jubilado'),
        ('INACTIVO', 'Inactivo'),
        ('', 'No especificado'),
    ]
    
    FUNCION_OPCIONES = [
        ('ADMINISTRATIVO ESPECIALIZADO', 'ADMINISTRATIVO ESPECIALIZADO'),
        ('APOYO TÉCNICO PEDAGÓGICO', 'APOYO TÉCNICO PEDAGÓGICO'),
        ('ASESOR JURÍDICO', 'ASESOR JURÍDICO'),
        ('ASISTENTE DE SERVICIOS', 'ASISTENTE DE SERVICIOS'),
        ('AUXILIAR DE GRUPO', 'AUXILIAR DE GRUPO'),
        ('BIBLIOTECARIO', 'BIBLIOTECARIO'),
        ('DIRECTOR(A)', 'DIRECTOR(A)'),
        ('MAESTRO(A) AULA HOSPITALARIA', 'MAESTRO(A) AULA HOSPITALARIA'),
        ('MAESTRO(A) DE COMUNICACIÓN', 'MAESTRO(A) DE COMUNICACIÓN'),
        ('MAESTRO(A) DE EDUCACIÓN FÍSICA', 'MAESTRO(A) DE EDUCACIÓN FÍSICA'),
        ('MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO', 'MAESTRO(A) ESPECIALISTA DOCENTE DE APOYO'),
        ('MAESTRO(A) DE GRUPO ESPECIALISTA', 'MAESTRO(A) DE GRUPO ESPECIALISTA'),
        ('MAESTRO(A) MÚSICA', 'MAESTRO(A) MÚSICA'),
        ('MAESTRO(A) DE TALLER', 'MAESTRO(A) DE TALLER'),
        ('MÉDICO(A)', 'MÉDICO(A)'),
        ('NIÑERO(A)', 'NIÑERO(A)'),
        ('NO ESPECIFICADO', 'NO ESPECIFICADO'),
        ('OFICIAL DE SERVICIOS Y MANTENIMIENTO', 'OFICIAL DE SERVICIOS Y MANTENIMIENTO'),
        ('PROMOTOR TIC', 'PROMOTOR TIC'),
        ('PSICÓLOGO(A)', 'PSICÓLOGO(A)'),
        ('SECRETARIO(A)', 'SECRETARIO(A)'),
        ('SUPERVISOR(A)', 'SUPERVISOR(A)'),
        ('TERAPISTA FÍSICO', 'TERAPISTA FÍSICO'),
        ('TRABAJADOR(A) SOCIAL', 'TRABAJADOR(A) SOCIAL'),
        ('VELADOR', 'VELADOR'),
        ('VIGILANTE', 'VIGILANTE'),
    ]
    
    # Datos personales
    id_maestro = models.CharField(
        max_length=5,
        unique=True,
        verbose_name="ID Maestro",
        primary_key=True,
        editable=False,  # No editable manualmente
        help_text="ID único de 5 dígitos para el personal (ej: 00001, 00002)"
    )
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='maestro_profile')
    a_paterno = models.CharField(max_length=50, verbose_name="Apellido Paterno", blank=True, null=True)
    a_materno = models.CharField(max_length=50, verbose_name="Apellido Materno", blank=True, null=True)
    nombres = models.CharField(max_length=100, verbose_name="Nombres", blank=True, null=True)
    curp = models.CharField(max_length=18, verbose_name="CURP", blank=True, null=True)
    rfc = models.CharField(max_length=13, verbose_name="RFC", blank=True, null=True)
    sexo = models.CharField(max_length=1, choices=SEXO_OPCIONES, verbose_name="Sexo", blank=True, null=True)
    est_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_OPCIONES, verbose_name="Estado Civil", blank=True, null=True)
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento", null=True, blank=True)
    id_escuela = models.ForeignKey(Escuela, on_delete=models.CASCADE, verbose_name="Escuela", blank=True, null=True)
    techo_f = models.CharField(max_length=50, verbose_name="Techo Financiero", blank=True, null=True)
    dep = models.CharField(max_length=10, verbose_name="Dependencia", blank=True, null=True)
    unid = models.CharField(max_length=10, verbose_name="Unidad", blank=True, null=True)
    sub_unid = models.CharField(max_length=10, verbose_name="Subunidad", blank=True, null=True)
    categog = models.ForeignKey(Categoria, on_delete=models.SET_NULL, verbose_name="Categoría", blank=True, null=True, to_field='id_categoria', help_text="Categoría presupuestal del personal")
    hrs = models.CharField(max_length=10, verbose_name="Horas", blank=True, null=True)
    num_plaza = models.CharField(max_length=20, verbose_name="Número de Plaza", blank=True, null=True)
    codigo = models.CharField(max_length=50, verbose_name="Código", blank=True, null=True)
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso", null=True, blank=True)
    fecha_promocion = models.DateField(verbose_name="Fecha de Promoción", null=True, blank=True)
    form_academica = models.CharField(max_length=100, verbose_name="Formación Académica", blank=True, null=True)
    horario = models.CharField(max_length=100, verbose_name="Horario", blank=True, null=True)
    funcion = models.CharField(max_length=50, choices=FUNCION_OPCIONES, verbose_name="Función", blank=True, null=True)
    nivel_estudio = models.CharField(max_length=20, choices=NIVEL_ESTUDIO_OPCIONES, verbose_name="Titulo o Tratamiento (Prefijo a usar)", blank=True, null=True)
    domicilio_part = models.TextField(verbose_name="Domicilio Particular", blank=True, null=True)
    poblacion = models.CharField(max_length=100, verbose_name="Población", blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, verbose_name="Código Postal", blank=True, null=True)
    telefono = models.CharField(max_length=50, verbose_name="Teléfono", blank=True, null=True)
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_OPCIONES, default='ACTIVO', verbose_name="Status", blank=True, null=True)
    observaciones = models.TextField(verbose_name="Observaciones", blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    clave_presupuestal = models.CharField(max_length=50, verbose_name="Clave Presupuestal", blank=True, null=True, editable=False)
    
    # Campos para búsqueda normalizada
    a_paterno_normalized = models.CharField(max_length=50, editable=False, db_index=True, blank=True, null=True)
    a_materno_normalized = models.CharField(max_length=50, editable=False, db_index=True, blank=True, null=True)
    nombres_normalized = models.CharField(max_length=100, editable=False, db_index=True, blank=True, null=True)
    nombre_completo_normalized = models.CharField(max_length=202, editable=False, db_index=True, blank=True, null=True)
    nombre_completo_unaccented = models.CharField(max_length=511, blank=True, null=True, db_index=True, editable=False)

    class Meta:
        verbose_name = "Personal"
        verbose_name_plural = "Todo el personal"  # Cambia el nombre del menú lateral
        ordering = ['a_paterno', 'a_materno', 'nombres']
    
    def __str__(self):
        return f"{self.a_paterno} {self.a_materno} {self.nombres}"
    
    def generar_clave_presupuestal(self):
        """Genera la clave presupuestal concatenando los campos en el orden correcto"""
        # Asegurar que todos los campos tengan valores por defecto si están vacíos
        dep = self.dep or "00"
        unid = self.unid or "00"
        sub_unid = self.sub_unid or "00"
        categog = self.categog.id_categoria if self.categog else ""
        hrs = self.hrs or "00.0"
        num_plaza = self.num_plaza or "000000"
        
        return f"{dep}{unid}{sub_unid}{categog}{hrs}{num_plaza}"

    def generar_id_maestro(self):
        """Genera un ID autoincremental de 5 dígitos"""
        # Obtener todos los IDs existentes que sean numéricos
        ids_numericos = []
        for maestro in Maestro.objects.all():
            try:
                ids_numericos.append(int(maestro.id_maestro))
            except (ValueError, TypeError):
                continue  # Saltar IDs no numéricos
        
        if ids_numericos:
            # Encontrar el máximo ID numérico y aumentar en 1
            nuevo_numero = max(ids_numericos) + 1
        else:
            # Si no hay maestros con IDs numéricos, comenzar desde 1
            nuevo_numero = 1
        
        # Formatear a 5 dígitos con ceros a la izquierda
        return f"{nuevo_numero:05d}"
    
    def save(self, *args, **kwargs):
        # Generar ID automáticamente si no existe o está vacío
        if not self.id_maestro or self.id_maestro.strip() == '':
            self.id_maestro = self.generar_id_maestro()
        
        # Generar la clave presupuestal antes de guardar
        self.clave_presupuestal = self.generar_clave_presupuestal()

        # Lógica solicitada por el usuario para el nuevo campo
        from unidecode import unidecode
        full_name = f"{self.nombres or ''} {self.a_paterno or ''} {self.a_materno or ''}".strip().upper()
        self.nombre_completo_unaccented = unidecode(full_name)

        # Mantener la lógica de normalización anterior para otros campos si es necesario
        self.a_paterno_normalized = unidecode(self.a_paterno.upper()) if self.a_paterno else None
        self.a_materno_normalized = unidecode(self.a_materno.upper()) if self.a_materno else None
        self.nombres_normalized = unidecode(self.nombres.upper()) if self.nombres else None
        parts = [
            self.nombres_normalized,
            self.a_paterno_normalized,
            self.a_materno_normalized
        ]
        self.nombre_completo_normalized = ' '.join(filter(None, parts))

        super().save(*args, **kwargs)
    
    def clean(self):
        """Valida y genera la clave presupuestal"""
        from django.core.exceptions import ValidationError
        import re
        
        # La validación de categoría ahora es manejada por la ForeignKey
        
        # Validar formatos individuales
        campos_validar = [
            ('dep', r'^\d{2}$', 'Dependencia debe tener 2 dígitos'),
            ('unid', r'^\d{2}$', 'Unidad debe tener 2 dígitos'),
            ('sub_unid', r'^\d{2}$', 'Subunidad debe tener 2 dígitos'),
            ('hrs', r'^\d{2}\.\d$', 'Horas deben tener formato XX.X'),
            ('num_plaza', r'^\d{6}$', 'Número de plaza debe tener 6 dígitos'),
        ]
        
        for campo, patron, mensaje in campos_validar:
            valor = getattr(self, campo, '')
            if valor and not re.match(patron, str(valor)):
                raise ValidationError({campo: mensaje})
        
        # Generar la clave presupuestal
        self.clave_presupuestal = self.generar_clave_presupuestal()
        
        super().clean()

class Director(models.Model):
    maestro = models.OneToOneField(Maestro, on_delete=models.CASCADE, verbose_name="Maestro")
    escuela = models.OneToOneField(Escuela, on_delete=models.CASCADE, verbose_name="Escuela")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin", null=True, blank=True)
    acuerdo = models.CharField(max_length=100, verbose_name="Acuerdo de Nombramiento", blank=True)
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    
    class Meta:
        verbose_name = "Director"
        verbose_name_plural = "Directores"
        ordering = ['escuela', 'fecha_inicio']
    
    def __str__(self):
        return f"Director: {self.maestro} - Escuela: {self.escuela}"

class MotivoTramite(models.Model):
    id = models.IntegerField(primary_key=True)
    motivo_tramite = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Motivo de Trámite"
        verbose_name_plural = "Motivos de Trámite"
        ordering = ['motivo_tramite']

    def __str__(self):
        return self.motivo_tramite

class PlantillaTramite(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de Plantilla")
    ruta_archivo = models.CharField(max_length=255, verbose_name="Ruta del Archivo de Plantilla")
    
    TIPO_DOCUMENTO_CHOICES = [
        ('OFICIO', 'Oficio'),
        ('TRAMITE', 'Trámite'),
    ]
    tipo_documento = models.CharField(
        max_length=10, 
        choices=TIPO_DOCUMENTO_CHOICES, 
        default='TRAMITE',
        verbose_name="Tipo de Documento",
        help_text="Indica si la plantilla es para un Oficio o un Trámite general."
    )

    class Meta:
        verbose_name = "Plantilla de Trámite"
        verbose_name_plural = "Plantillas de Trámite"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Prelacion(models.Model):
    pos_orden = models.IntegerField(verbose_name="Posición de Orden")
    folio = models.CharField(max_length=50, unique=True, verbose_name="Folio de Prelación")
    curp = models.CharField(max_length=18, verbose_name="CURP del Aspirante")
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Aspirante")
    tipo_val = models.CharField(max_length=255, verbose_name="Tipo de Valoración")

    class Meta:
        verbose_name = "Registro de Prelación"
        verbose_name_plural = "Registros de Prelación"
        ordering = ['pos_orden']

    def __str__(self):
        return f"{self.folio} - {self.nombre} ({self.tipo_val})"

class TipoApreciacion(models.Model):
    descripcion = models.TextField(unique=True, verbose_name="Descripción de Apreciación")

    class Meta:
        verbose_name = "Tipo de Apreciación"
        verbose_name_plural = "Tipos de Apreciación"
        ordering = ['descripcion']

    def __str__(self):
        return self.descripcion

class LoteReporteVacancia(models.Model):
    ESTADOS = [
        ('EN_PROCESO', 'En Proceso'),
        ('GENERADO', 'Generado'),
    ]
    usuario_generador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario Generador")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_generado = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Generación")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN_PROCESO', verbose_name="Estado")
    archivo_generado = models.FileField(upload_to='tramites_generados/vacancias/', null=True, blank=True, verbose_name="Archivo Generado")

    class Meta:
        verbose_name = "Lote de Reporte de Vacancia"
        verbose_name_plural = "Lotes de Reportes de Vacancia"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Lote {self.id} - {self.usuario_generador.username if self.usuario_generador else 'N/A'} - {self.get_estado_display()}"

class Vacancia(models.Model):
    MOTIVO_MOVIMIENTO_CHOICES = [
        ('LICENCIA POR ASUNTOS PARTICULARES', 'LICENCIA POR ASUNTOS PARTICULARES'),
        ('LICENCIA POR PASAR A OTRO EMPLEO', 'LICENCIA POR PASAR A OTRO EMPLEO'),
        ('LICENCIA POR COMISION SINDICAL O ELECCION POPULAR', 'LICENCIA POR COMISION SINDICAL O ELECCION POPULAR'),
        ('LICENCIA POR GRAVIDEZ', 'LICENCIA POR GRAVIDEZ'),
        ('LICENCIA POR INCAPACIDAD MEDICA', 'LICENCIA POR INCAPACIDAD MEDICA'),
        ('LICENCIA POR BECA', 'LICENCIA POR BECA'),
        ('LICENCIA PREPENSIONARIA', 'LICENCIA PREPENSIONARIA'),
        ('LICENCIA SIN GOCE DE SUELDO', 'LICENCIA SIN GOCE DE SUELDO'),
    ]

    TIPO_VACANTE_CHOICES = [
        ('TEMPORAL', 'Temporal'),
        ('DEFINITIVA', 'Definitiva'),
    ]

    lote = models.ForeignKey(LoteReporteVacancia, related_name='vacancias', on_delete=models.CASCADE, verbose_name="Lote de Reporte")
    # Campos del formulario original
    maestro_titular = models.ForeignKey(Maestro, on_delete=models.CASCADE, verbose_name="Maestro Titular")
    maestro_interino = models.ForeignKey(Maestro, on_delete=models.SET_NULL, null=True, blank=True, related_name='vacancias_interino', verbose_name="Maestro Interino")
    apreciacion = models.ForeignKey(TipoApreciacion, on_delete=models.PROTECT, verbose_name="Apreciación")
    tipo_vacante = models.CharField(max_length=100, choices=TIPO_VACANTE_CHOICES, verbose_name="Tipo de Vacante")
    tipo_movimiento_original = models.CharField(max_length=100, choices=MOTIVO_MOVIMIENTO_CHOICES, verbose_name="Motivo del Movimiento", null=True, blank=True) # Ej: BECA COMISIÓN
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_final = models.DateField(verbose_name="Fecha Final", null=True)
    observaciones = models.TextField(blank=True, null=True)
    nombre_interino = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre Interino (manual)")
    curp_interino = models.CharField(max_length=18, blank=True, null=True, verbose_name="CURP Interino (manual)")
    posicion_orden = models.CharField(max_length=50, blank=True, null=True, verbose_name="Posición de Orden (Prelación)")
    folio_prelacion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Folio de Prelación")
    # Campos generados para el excel
    nivel = models.CharField(max_length=100, default="Educación Especial")
    entidad = models.CharField(max_length=100, default="DURANGO")
    municipio = models.CharField(max_length=100)
    direccion = models.TextField()
    region = models.CharField(max_length=100, default="Durango")
    zona_economica = models.CharField(max_length=50)
    destino = models.CharField(max_length=100)
    tipo_plaza = models.CharField(max_length=50)
    horas = models.CharField(max_length=10, null=True, blank=True)
    sostenimiento = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    clave_presupuestal = models.CharField(max_length=100)
    techo_financiero = models.CharField(max_length=50)
    clave_ct = models.CharField(max_length=20)
    turno = models.CharField(max_length=50)
    tipo_movimiento_reporte = models.CharField(max_length=100, verbose_name="Tipo de Movimiento para Reporte", null=True, blank=True) # Ej: LICENCIA POR BECA
    nombre_titular_reporte = models.CharField(max_length=255)
    pseudoplaza = models.CharField(max_length=1, blank=True, null=True, verbose_name="Pseudoplaza")

    class Meta:
        verbose_name = "Vacancia"
        verbose_name_plural = "Vacancias"
        ordering = ['-lote__fecha_creacion']

    def __str__(self):
        return f"Vacancia para {self.nombre_titular_reporte} en Lote {self.lote.id}"

class Historial(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    tipo_documento = models.CharField(max_length=100, verbose_name="Tipo de Documento")
    maestro = models.ForeignKey(Maestro, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Maestro")
    maestro_secundario_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name="Maestro Interino/Secundario")
    ruta_archivo = models.CharField(max_length=255, verbose_name="Ruta del Archivo")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    motivo = models.CharField(max_length=255, blank=True, null=True, verbose_name="Motivo")
    lote_reporte = models.ForeignKey(LoteReporteVacancia, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lote de Reporte")
    datos_tramite = models.JSONField(blank=True, null=True, verbose_name="Datos del Trámite/Oficio")

    class Meta:
        verbose_name = "Historial"
        verbose_name_plural = "Historial"
        ordering = ['-fecha_creacion']

    def __str__(self):
        maestro_str = self.maestro.__str__() if self.maestro else "N/A"
        usuario_str = self.usuario.username if self.usuario else "N/A"
        return f"{self.tipo_documento} por {usuario_str} para {maestro_str} el {self.fecha_creacion.strftime('%Y-%m-%d %H:%M')}"


class DocumentoExpediente(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('TALON_PAGO', 'Talón de Pago'),
        ('ACTA_NACIMIENTO', 'Acta de Nacimiento'),
        ('INE', 'INE'),
        ('CURP_DOC', 'CURP (Documento)'),
        ('OFICIO_PRESENTACION', 'Oficio de Presentación'),
        ('FUP', 'FUP'),
        ('OTRO', 'Otro'),
    ]

    maestro = models.ForeignKey(Maestro, on_delete=models.CASCADE, related_name='documentos_expediente', verbose_name="Maestro")
    tipo_documento = models.CharField(max_length=50, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento")
    archivo = models.FileField(upload_to='expedientes/%Y/%m/%d/', verbose_name="Archivo PDF")
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Subido por")

    class Meta:
        verbose_name = "Documento de Expediente"
        verbose_name_plural = "Documentos de Expediente"
        ordering = ['maestro__a_paterno', 'tipo_documento', '-fecha_subida']
        unique_together = ('maestro', 'tipo_documento', 'archivo')

    def __str__(self):
        return f"{self.get_tipo_documento_display()} de {self.maestro} ({self.fecha_subida.strftime('%Y-%m-%d')})"

    def get_file_name(self):
        import os
        return os.path.basename(self.archivo.name)

# --- INICIO DE NUEVOS MODELOS ---

class Correspondencia(models.Model):
    remitente = models.ForeignKey(User, related_name='mensajes_enviados', on_delete=models.CASCADE, verbose_name="Remitente")
    destinatario = models.ForeignKey(User, related_name='mensajes_recibidos', on_delete=models.CASCADE, verbose_name="Destinatario")
    asunto = models.CharField(max_length=200, verbose_name="Asunto")
    cuerpo = models.TextField(verbose_name="Cuerpo del Mensaje")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    leido = models.BooleanField(default=False, verbose_name="Leído")
    archivado = models.BooleanField(default=False, verbose_name="Archivado")

    class Meta:
        verbose_name = "Correspondencia"
        verbose_name_plural = "Correspondencias"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"De: {self.remitente.username} | Para: {self.destinatario.username} | Asunto: {self.asunto}"

class RegistroCorrespondencia(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('OFICIO', 'Oficio'),
        ('TARJETA', 'Tarjeta'),
        ('CIRCULAR', 'Circular'),
        ('INVITACION', 'Invitación'),
        ('OTRO', 'Otro'),
    ]
    AREA_CHOICES = [
        ('OPERATIVO', 'Operativo'),
        ('ACADEMICA', 'Académica'),
        ('DIRECCION', 'Dirección'),
        ('OTRO', 'Otro'),
    ]

    fecha_recibido = models.DateField(verbose_name="Fecha de Recibido")
    fecha_oficio = models.DateField(verbose_name="Fecha del Oficio")
    maestro = models.ForeignKey(
        Maestro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Maestro Relacionado (Opcional)",
        related_name='correspondencia_recibida'
    )
    tipo_documento = models.CharField(
        max_length=20, 
        choices=TIPO_DOCUMENTO_CHOICES, 
        verbose_name="Tipo de Documento"
    )
    folio_documento = models.CharField(max_length=100, verbose_name="Folio del Documento", blank=True)
    remitente = models.CharField(max_length=255, verbose_name="Remitente (De)")
    contenido = models.TextField(verbose_name="Contenido del Oficio")
    area = models.CharField(
        max_length=20, 
        choices=AREA_CHOICES, 
        verbose_name="Área Destino"
    )
    observaciones = models.TextField(verbose_name="Observaciones", blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    archivo_adjunto = models.FileField(upload_to='correspondencia/', blank=True, null=True, verbose_name="Archivo Adjunto (PDF)")
    quien_recibio = models.CharField(max_length=255, verbose_name="Quien Recibió", blank=True, null=True)

    class Meta:
        verbose_name = "Registro de Correspondencia"
        verbose_name_plural = "Registros de Correspondencia"
        ordering = ['-fecha_recibido', '-fecha_registro']

    def __str__(self):
        return f"Oficio {self.folio_documento} de {self.remitente} ({self.fecha_recibido})"

# --- MODELOS ANCLA PARA PERMISOS PERSONALIZADOS ---
# Estos modelos no crean tablas en la BD (managed=False)
# Su único propósito es servir como ancla para permisos
# que se pueden asignar a los roles en la matriz visual.

class ModuloOficios(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Oficios"
        permissions = (("acceder_oficios", "Puede acceder al módulo de Oficios"),)

class ModuloTramites(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Trámites"
        permissions = (("acceder_tramites", "Puede acceder al módulo de Trámites"),)

class ModuloVacancias(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Asignación de Vacancia"
        permissions = (("acceder_vacancias", "Puede acceder al módulo de Asignación de Vacancia"),)

class ModuloHistorial(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Historial"
        permissions = (("acceder_historial", "Puede acceder al módulo de Historial"),)

class ModuloAjustes(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Ajustes"
        permissions = (("acceder_ajustes", "Puede acceder al módulo de Ajustes"),)

class ModuloBandejaEntrada(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Bandeja de Entrada"
        permissions = (("acceder_bandeja_entrada", "Puede acceder a la Bandeja de Entrada"),)

class ModuloReportes(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Reportes"
        permissions = (("acceder_reportes", "Puede acceder al módulo de Reportes"),)

class ModuloMisPendientes(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Mis Pendientes"
        permissions = (("acceder_pendientes", "Puede acceder al módulo de Mis Pendientes"),)


class ModuloFUP(models.Model):
    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de FUP"
        permissions = (("acceder_fup", "Puede acceder al módulo de FUP"),)


class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones', verbose_name="Usuario")
    mensaje = models.CharField(max_length=255, verbose_name="Mensaje")
    leida = models.BooleanField(default=False, verbose_name="Leída")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    correspondencia = models.ForeignKey(Correspondencia, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Mensaje Relacionado")

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Notificación para {self.usuario.username}: {self.mensaje}"

class Pendiente(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pendientes', verbose_name="Usuario")
    titulo = models.CharField(max_length=255, verbose_name="Título")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_programada = models.DateField(verbose_name="Fecha Programada")
    completado = models.BooleanField(default=False, verbose_name="Completado")

    class Meta:
        verbose_name = "Pendiente"
        verbose_name_plural = "Pendientes"
        ordering = ['-fecha_programada', 'titulo']

    def __str__(self):
        return self.titulo

# --- FIN DE NUEVOS MODELOS ---

class ModuloDashboard(models.Model):

    class Meta:
        managed = False
        verbose_name_plural = "Acceso al Módulo de Dashboard"
        permissions = (
            ("ver_estadisticas_generales", "Puede ver las estadísticas generales del dashboard"),
            ("ver_grafico_distribucion_zona", "Puede ver el gráfico de distribución por zona"),
            ("ver_lista_pendientes", "Puede ver la lista de pendientes próximos"),
            ("ver_lista_ultimo_personal", "Puede ver la lista de último personal registrado"),
            ("ver_ultima_correspondencia", "Puede ver la tarjeta de última correspondencia registrada"),
        )

class KardexMovimiento(models.Model):
    maestro = models.ForeignKey(Maestro, on_delete=models.CASCADE, verbose_name="Maestro")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Movimiento")
    descripcion = models.TextField(verbose_name="Descripción del Movimiento")

    class Meta:
        verbose_name = "Movimiento de Kardex"
        verbose_name_plural = "Movimientos de Kardex"
        ordering = ['-fecha']

    def __str__(self):
        return f"Movimiento {self.id} - {self.maestro}"

class Tema(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Tema")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    imagen_fondo = models.ImageField(upload_to='themes/', blank=True, null=True, verbose_name="Imagen de Fondo (Opcional)")
    color_principal = ColorField(default='#2c3e50', verbose_name="Color Principal (Gradiente Superior)")
    color_secundario = ColorField(default='#34495e', verbose_name="Color Secundario (Gradiente Inferior)")
    color_texto = ColorField(default='#FFFFFF', verbose_name="Color del Texto del Sidebar")
    color_dropdown = ColorField(default='#3a506b', verbose_name="Color de Fondo del Submenú", help_text="Color de fondo para los menús desplegables del sidebar")
    usar_filtro_oscuro = models.BooleanField(default=True, verbose_name="Usar filtro oscuro en imagen", help_text="Si está activo, se aplicará un filtro oscuro sobre la imagen de fondo para mejorar la legibilidad del texto blanco.")
    activo = models.BooleanField(default=True, verbose_name="Activo", help_text="Solo un tema puede estar activo a la vez para un rango de fechas.")

    class Meta:
        verbose_name = "Tema de Personalización"
        verbose_name_plural = "Temas de Personalización"
        ordering = ['fecha_inicio']

    def __str__(self):
        return self.nombre

class FUP(models.Model):
    """Formato Único de Personal - Registro de documentos FUP con snapshot de datos del maestro"""
    
    SOSTENIMIENTOS = [
        ('FEDERAL', 'Federal'),
        ('ESTATAL', 'Estatal'),
    ]
    
    # Relación con maestro
    maestro = models.ForeignKey(
        Maestro,
        on_delete=models.CASCADE,
        verbose_name="Maestro",
        related_name='fups'
    )
    
    # Snapshot de datos del maestro al momento de crear el FUP
    nombre_completo = models.CharField(max_length=250, verbose_name="Nombre Completo", editable=False)
    rfc = models.CharField(max_length=13, verbose_name="RFC", blank=True, null=True, editable=False)
    curp = models.CharField(max_length=18, verbose_name="CURP", blank=True, null=True, editable=False)
    clave_presupuestal = models.CharField(max_length=50, verbose_name="Clave Presupuestal", blank=True, null=True, editable=False)
    
    # Datos del FUP
    fecha = models.DateField(auto_now_add=True, verbose_name="Fecha de FUP")
    techo_financiero = models.CharField(max_length=50, verbose_name="Techo Financiero", blank=True, null=True)
    efectos = models.CharField(max_length=100, verbose_name="Efectos", blank=True, null=True)
    folio = models.CharField(max_length=50, verbose_name="Folio", blank=True, null=True)
    observaciones = models.TextField(verbose_name="Observaciones", blank=True, null=True)
    sostenimiento = models.CharField(max_length=10, choices=SOSTENIMIENTOS, verbose_name="Sostenimiento", blank=True, null=True)
    
    # Archivo PDF
    archivo = models.FileField(upload_to='fups/%Y/%m/', verbose_name="Archivo PDF", blank=True, null=True)
    
    class Meta:
        verbose_name = "FUP"
        verbose_name_plural = "FUPs"
        ordering = ['-fecha', '-id']
    
    def __str__(self):
        return f"FUP {self.folio} - {self.nombre_completo}"
    
    def save(self, *args, **kwargs):
        # Snapshot de datos del maestro
        if not self.pk:  # Solo en creación
            self.nombre_completo = f"{self.maestro.a_paterno or ''} {self.maestro.a_materno or ''} {self.maestro.nombres or ''}".strip()
            self.rfc = self.maestro.rfc
            self.curp = self.maestro.curp
            self.clave_presupuestal = self.maestro.clave_presupuestal
            
            # Si no se especifica techo_financiero, usar el del maestro
            if not self.techo_financiero:
                self.techo_financiero = self.maestro.techo_f
        
        # Actualizar techo_f del maestro si cambió
        if self.techo_financiero and self.techo_financiero != self.maestro.techo_f:
            self.maestro.techo_f = self.techo_financiero
            self.maestro.save(update_fields=['techo_f'])
        
        super().save(*args, **kwargs)