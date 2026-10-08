from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RegistroFinanciero(models.Model):
	class Tipo(models.TextChoices):
		GASTO = 'gasto', 'Gasto'
		INVERSION = 'inversion', 'Inversión'
		EGRESO = 'egreso', 'Egreso / salida'

	class Categoria(models.TextChoices):
		ALQUILER = 'alquiler', 'Alquiler de oficina'
		SUELDO_AUXILIAR = 'sueldo_auxiliar', 'Sueldo de auxiliar'
		SUELDO_CAPTADORES = 'sueldo_captadores', 'Sueldos de captadores'
		SUELDO_EEFF = 'sueldo_eeff', 'Sueldo extra EEFF'
		FIRMAS_AUDITORIA = 'firmas_auditoria', 'Firmas de auditoría'
		AGUINALDO = 'aguinaldo', 'Aguinaldo'
		INTERNET = 'internet', 'Internet'
		LUZ = 'luz', 'Luz'
		REFRIGERIO = 'refrigerio', 'Refrigerio'
		PASAJES = 'pasajes', 'Pasajes'
		SUMINISTROS = 'suministros', 'Suministros de oficina'
		IMPUESTOS = 'impuestos', 'Impuestos'
		FACTURAS = 'facturas', 'Facturas'
		TALONARIOS = 'talonarios', 'Talonarios'
		PASANKU = 'pasanku', 'Pasanku'
		SILLAS = 'sillas', 'Sillas'
		MONITOR = 'monitor', 'Monitor'
		ESCRITORIO = 'escritorio', 'Escritorio'
		COMPUTADORA = 'computadora', 'Computadora'
		IMPRESORA = 'impresora', 'Impresora'
		MUEBLES = 'muebles', 'Muebles y equipos'
		OTRO = 'otro', 'Otro'

	class Periodicidad(models.TextChoices):
		MENSUAL = 'mensual', 'Mensual'
		ANUAL = 'anual', 'Anual'
		UNICO = 'unico', 'Único'
		EXTRAORDINARIO = 'extraordinario', 'Extraordinario'

	class EstadoPago(models.TextChoices):
		PENDIENTE = 'pendiente', 'Pendiente de pago'
		PAGADO = 'pagado', 'Pagado'

	class EstadoRecuperacion(models.TextChoices):
		PENDIENTE = 'pendiente', 'Pendiente de recuperar'
		RECUPERADO = 'recuperado', 'Recuperado'

	class EstadoActivo(models.TextChoices):
		EN_USO = 'en_uso', 'En uso'
		BAJA = 'baja', 'Dado de baja'

	concepto = models.CharField(max_length=180)
	tipo = models.CharField(max_length=16, choices=Tipo.choices)
	categoria = models.CharField(max_length=24, choices=Categoria.choices)
	periodicidad = models.CharField(max_length=18, choices=Periodicidad.choices, default=Periodicidad.UNICO)
	monto = models.DecimalField(max_digits=12, decimal_places=2)
	fecha = models.DateField(default=timezone.localdate)
	proveedor = models.CharField(max_length=180, blank=True, default='')
	responsable = models.CharField(max_length=180, blank=True, default='')
	comprobante = models.CharField(max_length=120, blank=True, default='')
	estado_pago = models.CharField(max_length=12, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
	recuperable = models.BooleanField(default=False)
	estado_recuperacion = models.CharField(
		max_length=12,
		choices=EstadoRecuperacion.choices,
		default=EstadoRecuperacion.PENDIENTE,
	)
	cliente = models.ForeignKey(
		'clientes.Cliente',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='registros_financieros',
	)
	vida_util_meses = models.PositiveSmallIntegerField(null=True, blank=True)
	estado_activo = models.CharField(max_length=8, choices=EstadoActivo.choices, default=EstadoActivo.EN_USO)
	ubicacion = models.CharField(max_length=180, blank=True, default='')
	observaciones = models.TextField(blank=True, default='')
	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='registros_financieros_creados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-fecha', '-pk')
		verbose_name = 'registro financiero'
		verbose_name_plural = 'registros financieros'

	def clean(self):
		errores = {}
		if self.monto is not None and self.monto <= 0:
			errores['monto'] = 'El monto debe ser mayor a cero.'
		if self.recuperable and self.cliente_id is None:
			errores['cliente'] = 'Selecciona el cliente al que se cobrará este egreso.'
		if self.tipo != self.Tipo.INVERSION and self.vida_util_meses:
			errores['vida_util_meses'] = 'La vida útil solo corresponde a una inversión.'
		if errores:
			raise ValidationError(errores)

	@property
	def depreciacion_mensual(self):
		if self.tipo != self.Tipo.INVERSION or not self.vida_util_meses:
			return Decimal('0.00')
		return (self.monto / self.vida_util_meses).quantize(Decimal('0.01'))

	@property
	def depreciacion_acumulada(self):
		if self.tipo != self.Tipo.INVERSION or not self.vida_util_meses:
			return Decimal('0.00')
		hoy = timezone.localdate()
		meses = max(0, (hoy.year - self.fecha.year) * 12 + hoy.month - self.fecha.month)
		meses = min(meses, self.vida_util_meses)
		return min(self.monto, self.depreciacion_mensual * meses)

	def __str__(self):
		return f'{self.concepto} - Bs {self.monto}'