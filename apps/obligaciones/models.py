from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


MESES_EN_ESPANOL = (
	'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
	'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)


class TipoObligacion(models.Model):
	class Periodicidad(models.TextChoices):
		MENSUAL = 'mensual', 'Mensual'
		TRIMESTRAL = 'trimestral', 'Trimestral'
		ANUAL = 'anual', 'Anual'

	class ReglaVencimiento(models.TextChoices):
		DIA_FIJO = 'dia_fijo', 'Día fijo del mes siguiente'
		DIGITO_NIT = 'digito_nit', 'Según terminación del NIT'
		ULTIMO_HABIL = 'ultimo_habil', 'Último día hábil del mes siguiente'
		CIERRE_FISCAL_120 = 'cierre_fiscal_120', '120 días después del cierre fiscal'
		MANUAL = 'manual', 'Fecha definida manualmente'

	codigo = models.SlugField(max_length=40, unique=True)
	nombre = models.CharField(max_length=100)
	periodicidad = models.CharField(max_length=12, choices=Periodicidad.choices)
	regla_vencimiento = models.CharField(
		max_length=20,
		choices=ReglaVencimiento.choices,
		default=ReglaVencimiento.MANUAL,
	)
	dia_vencimiento = models.PositiveSmallIntegerField(null=True, blank=True)
	meses_despues_periodo = models.PositiveSmallIntegerField(default=1)
	activa = models.BooleanField(default=True)

	class Meta:
		ordering = ('periodicidad', 'nombre')
		verbose_name = 'tipo de obligación'
		verbose_name_plural = 'tipos de obligación'

	def clean(self):
		if self.regla_vencimiento == self.ReglaVencimiento.DIA_FIJO and not 1 <= (self.dia_vencimiento or 0) <= 31:
			raise ValidationError({'dia_vencimiento': 'Indica un día entre 1 y 31.'})
		if not 0 <= self.meses_despues_periodo <= 12:
			raise ValidationError({'meses_despues_periodo': 'El desplazamiento debe estar entre 0 y 12 meses.'})
		if self.regla_vencimiento == self.ReglaVencimiento.CIERRE_FISCAL_120 and self.periodicidad != self.Periodicidad.ANUAL:
			raise ValidationError({'regla_vencimiento': 'La regla de cierre fiscal solo corresponde a obligaciones anuales.'})

	def __str__(self):
		return self.nombre


class ConfiguracionCliente(models.Model):
	cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='configuraciones_obligaciones')
	tipo = models.ForeignKey(TipoObligacion, on_delete=models.PROTECT, related_name='configuraciones_clientes')
	fecha_inicio = models.DateField()
	activa = models.BooleanField(default=True)
	creada_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('cliente__nombre', 'tipo__nombre')
		constraints = [models.UniqueConstraint(fields=('cliente', 'tipo'), name='obligacion_cliente_tipo_unico')]
		verbose_name = 'configuración de obligación por cliente'
		verbose_name_plural = 'configuraciones de obligaciones por cliente'

	def __str__(self):
		return f'{self.cliente}: {self.tipo}'


class DiaNoLaborable(models.Model):
	fecha = models.DateField(unique=True)
	descripcion = models.CharField(max_length=120)

	class Meta:
		ordering = ('fecha',)
		verbose_name = 'día no laborable'
		verbose_name_plural = 'días no laborables'

	def __str__(self):
		return f'{self.fecha:%d/%m/%Y} - {self.descripcion}'


class Obligacion(models.Model):
	class Estado(models.TextChoices):
		PENDIENTE = 'pendiente', 'Pendiente'
		EN_PROCESO = 'en_proceso', 'En proceso'
		COMPLETADA = 'completada', 'Completada'
		CANCELADA = 'cancelada', 'Cancelada'

	cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='obligaciones')
	tipo = models.ForeignKey(TipoObligacion, on_delete=models.PROTECT, related_name='obligaciones')
	anio = models.PositiveSmallIntegerField()
	periodo_numero = models.PositiveSmallIntegerField(default=0)
	periodo_inicio = models.DateField()
	periodo_fin = models.DateField()
	fecha_vencimiento = models.DateField(null=True, blank=True)
	estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
	observaciones = models.TextField(blank=True)
	completada_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='obligaciones_completadas',
	)
	completada_en = models.DateTimeField(null=True, blank=True)
	creada_en = models.DateTimeField(auto_now_add=True)
	actualizada_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('fecha_vencimiento', 'cliente__nombre', 'tipo__nombre')
		constraints = [
			models.UniqueConstraint(
				fields=('cliente', 'tipo', 'anio', 'periodo_numero'),
				name='obligacion_cliente_periodo_unico',
			)
		]
		verbose_name = 'obligación'
		verbose_name_plural = 'obligaciones'

	@property
	def periodo_etiqueta(self):
		if self.tipo.periodicidad == TipoObligacion.Periodicidad.MENSUAL:
			return f'{MESES_EN_ESPANOL[self.periodo_inicio.month - 1]} {self.anio}'
		if self.tipo.periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL:
			return f'{self.periodo_numero}.er trimestre {self.anio}'
		return f'Ejercicio fiscal {self.anio}'

	@property
	def vencida(self):
		return (
			self.fecha_vencimiento is not None
			and self.fecha_vencimiento < timezone.localdate()
			and self.estado in (self.Estado.PENDIENTE, self.Estado.EN_PROCESO)
		)

	def __str__(self):
		return f'{self.tipo} - {self.cliente} - {self.periodo_etiqueta}'
