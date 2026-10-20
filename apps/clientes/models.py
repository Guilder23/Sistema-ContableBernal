from django.conf import settings
from django.db import models


class Cliente(models.Model):
	class Tipo(models.TextChoices):
		PERSONA_NATURAL = 'persona_natural', 'Persona natural'
		UNIPERSONAL = 'unipersonal', 'Empresa unipersonal'
		JURIDICA = 'juridica', 'Empresa jurídica'
		SIN_FINES_LUCRO = 'sin_fines_lucro', 'Empresa sin fines de lucro'

	class FormaJuridica(models.TextChoices):
		SRL = 'srl', 'SRL'
		SA = 'sa', 'SA'
		OTRA = 'otra', 'Otra'

	class TipoFacturacion(models.TextChoices):
		MANUAL = 'manual', 'Manual'
		PORTAL_WEB = 'portal_web', 'Portal web'
		COMPUTARIZADO_EN_LINEA = 'computarizado_en_linea', 'Computarizado en línea'
		ELECTRONICA_EN_LINEA = 'electronica_en_linea', 'Electrónica en línea'

	class Actividad(models.TextChoices):
		PROFESIONAL = 'profesional', 'Profesional'
		TECNICO = 'tecnico', 'Técnico'
		ALQUILER = 'alquiler', 'Alquiler'
		DEPENDIENTE = 'dependiente', 'Dependiente'
		CONSULTOR_EN_LINEA = 'consultor_en_linea', 'Consultor en línea'
		COMERCIAL = 'comercial', 'Comercial'
		SERVICIOS = 'servicios', 'Servicios'
		INDUSTRIAL = 'industrial', 'Industrial'
		CONSTRUCTORA = 'constructora', 'Constructora'
		AGRICOLA = 'agricola', 'Agrícola'
		AGROPECUARIA = 'agropecuaria', 'Agropecuaria'
		GANADERA = 'ganadera', 'Ganadera'
		AGROINDUSTRIAL = 'agroindustrial', 'Agroindustrial'
		MINERA = 'minera', 'Minera'
		ASOCIACION = 'asociacion', 'Asociación'
		ONG = 'ong', 'ONG'
		OTRA = 'otra', 'Otra'

	class Estado(models.TextChoices):
		ACTIVO = 'activo', 'Activo'
		INACTIVO = 'inactivo', 'Inactivo'

	nombre = models.CharField(max_length=180)
	razon_social = models.CharField(max_length=180, blank=True, default='')
	tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PERSONA_NATURAL)
	forma_juridica = models.CharField(max_length=8, choices=FormaJuridica.choices, blank=True, default='')
	forma_juridica_detalle = models.CharField(max_length=100, blank=True, default='')
	actividad_detalle = models.CharField(max_length=120, blank=True, default='')
	tiene_seprec = models.BooleanField(default=False)
	tiene_roe = models.BooleanField(default=False)
	nit = models.CharField(max_length=20, unique=True, null=True, blank=True)
	ci = models.CharField(max_length=20, blank=True)
	ci_complemento = models.CharField(max_length=10, blank=True, default='')
	ci_expedido = models.CharField(max_length=20, blank=True, default='')
	fecha_nacimiento = models.DateField(null=True, blank=True)
	cambio_contador = models.BooleanField(default=False)
	fecha_cambio_contador = models.CharField(max_length=7, blank=True, default='')
	actividad = models.CharField(max_length=24, choices=Actividad.choices, default=Actividad.OTRA)
	telefono = models.CharField(max_length=30, blank=True)
	whatsapp = models.CharField(max_length=30, blank=True)
	correo = models.EmailField(blank=True)
	direccion = models.CharField(max_length=240, blank=True)
	estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
	fecha_inicio = models.DateField(null=True, blank=True)
	tipo_facturacion = models.CharField(max_length=28, choices=TipoFacturacion.choices, blank=True, default='')
	fecha_vencimiento_facturacion = models.DateField(null=True, blank=True)
	evento_vencimiento_facturacion = models.OneToOneField(
		'agenda.EventoAgenda',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='cliente_vencimiento_facturacion',
	)
	tiene_representante_legal = models.BooleanField(default=False)
	representante_legal_nombre = models.CharField(max_length=180, blank=True, default='')
	representante_legal_carnet = models.CharField(max_length=20, blank=True, default='')
	representante_legal_complemento = models.CharField(max_length=10, blank=True, default='')
	representante_legal_expedido = models.CharField(max_length=20, blank=True, default='')
	representante_legal_celular = models.CharField(max_length=30, blank=True, default='')
	representante_legal_fecha_nacimiento = models.DateField(null=True, blank=True)
	observaciones = models.TextField(blank=True)
	creado_en = models.DateTimeField(auto_now_add=True)
	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='clientes_creados',
	)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('nombre',)
		verbose_name = 'cliente'
		verbose_name_plural = 'clientes'

	def __str__(self):
		return self.nombre
