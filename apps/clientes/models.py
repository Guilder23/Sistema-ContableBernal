from django.conf import settings
from django.db import models


class Cliente(models.Model):
	class Tipo(models.TextChoices):
		PERSONA_NATURAL = 'persona_natural', 'Persona natural'
		UNIPERSONAL = 'unipersonal', 'Empresa unipersonal'
		JURIDICA = 'juridica', 'Empresa jurídica'

	class Actividad(models.TextChoices):
		PROFESIONAL = 'profesional', 'Profesional'
		TECNICO = 'tecnico', 'Técnico'
		ALQUILER = 'alquiler', 'Alquiler'
		COMERCIAL = 'comercial', 'Comercial'
		SERVICIOS = 'servicios', 'Servicios'
		INDUSTRIAL = 'industrial', 'Industrial'
		CONSTRUCTORA = 'constructora', 'Constructora'
		AGRICOLA = 'agricola', 'Agrícola'
		GANADERA = 'ganadera', 'Ganadera'
		AGROINDUSTRIAL = 'agroindustrial', 'Agroindustrial'
		MINERA = 'minera', 'Minera'
		OTRA = 'otra', 'Otra'

	class Estado(models.TextChoices):
		ACTIVO = 'activo', 'Activo'
		INACTIVO = 'inactivo', 'Inactivo'

	nombre = models.CharField(max_length=180)
	razon_social = models.CharField(max_length=180, blank=True, default='')
	tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PERSONA_NATURAL)
	nit = models.CharField(max_length=20, unique=True, null=True, blank=True)
	ci = models.CharField(max_length=20, blank=True)
	ci_complemento = models.CharField(max_length=10, blank=True, default='')
	ci_expedido = models.CharField(max_length=20, blank=True, default='')
	fecha_nacimiento = models.DateField(null=True, blank=True)
	cambio_contador = models.BooleanField(default=False)
	actividad = models.CharField(max_length=24, choices=Actividad.choices, default=Actividad.OTRA)
	telefono = models.CharField(max_length=30, blank=True)
	whatsapp = models.CharField(max_length=30, blank=True)
	correo = models.EmailField(blank=True)
	direccion = models.CharField(max_length=240, blank=True)
	estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
	fecha_inicio = models.DateField(null=True, blank=True)
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
