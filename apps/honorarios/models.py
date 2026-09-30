from decimal import Decimal

from django.conf import settings
from django.db import models


class TarifaCliente(models.Model):
	cliente = models.OneToOneField(
		'clientes.Cliente',
		on_delete=models.CASCADE,
		related_name='tarifa',
	)
	monto_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	monto_trimestral = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	monto_anual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

	# Extras recurrentes automáticos en Bs.
	extra_bancarizacion = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	extra_gestora = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	extra_ministerio = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	extra_caja = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	extra_otros = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

	observaciones = models.TextField(blank=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'tarifa de cliente'
		verbose_name_plural = 'tarifas de clientes'

	@property
	def total_mensual_sugerido(self):
		return (
			self.monto_mensual
			+ self.extra_bancarizacion
			+ self.extra_gestora
			+ self.extra_ministerio
			+ self.extra_caja
			+ self.extra_otros
		)

	def __str__(self):
		return f'Tarifa de {self.cliente.nombre} (Bs {self.monto_mensual})'


class CobroHonorario(models.Model):
	class Estado(models.TextChoices):
		PENDIENTE = 'pendiente', 'Pendiente'
		PARCIAL = 'parcial', 'Pago Parcial'
		PAGADO = 'pagado', 'Pagado'
		CANCELADO = 'cancelado', 'Anulado / Cancelado'

	class Periodicidad(models.TextChoices):
		MENSUAL = 'mensual', 'Mensual'
		TRIMESTRAL = 'trimestral', 'Trimestral'
		ANUAL = 'anual', 'Anual'
		EXTRA = 'extra', 'Servicio Extraordinario'

	cliente = models.ForeignKey(
		'clientes.Cliente',
		on_delete=models.CASCADE,
		related_name='cobros_honorarios',
	)
	periodo_tipo = models.CharField(
		max_length=15,
		choices=Periodicidad.choices,
		default=Periodicidad.MENSUAL,
	)
	anio = models.PositiveSmallIntegerField()
	periodo_numero = models.PositiveSmallIntegerField(default=0, help_text='Mes (1-12) o Trimestre (1-4)')

	concepto = models.CharField(max_length=200)
	monto_base = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	monto_extras = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

	estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
	fecha_vencimiento = models.DateField(null=True, blank=True)
	observaciones = models.TextField(blank=True)

	generado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='honorarios_generados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-anio', '-periodo_numero', 'cliente__nombre')
		verbose_name = 'cobro de honorario'
		verbose_name_plural = 'cobros de honorarios'

	@property
	def monto_pagado(self):
		total = sum((pago.monto for pago in self.pagos.all()), Decimal('0.00'))
		return total

	@property
	def saldo_pendiente(self):
		saldo = self.monto_total - self.monto_pagado
		return saldo if saldo > Decimal('0.00') else Decimal('0.00')

	def actualizar_estado(self):
		pagado = self.monto_pagado
		if pagado <= Decimal('0.00'):
			self.estado = self.Estado.PENDIENTE
		elif pagado >= self.monto_total:
			self.estado = self.Estado.PAGADO
		else:
			self.estado = self.Estado.PARCIAL
		self.save(update_fields=('estado', 'actualizado_en'))

	def __str__(self):
		return f'{self.cliente.nombre} - {self.concepto} (Bs {self.monto_total})'


class PagoHonorario(models.Model):
	class MetodoPago(models.TextChoices):
		EFECTIVO = 'efectivo', 'Efectivo'
		TRANSFERENCIA = 'transferencia', 'Transferencia QR / Bancaria'
		DEPOSITO = 'deposito', 'Depósito bancario'
		CHEQUE = 'cheque', 'Cheque'
		OTRO = 'otro', 'Otro'

	cobro = models.ForeignKey(
		CobroHonorario,
		on_delete=models.CASCADE,
		related_name='pagos',
	)
	monto = models.DecimalField(max_digits=10, decimal_places=2)
	fecha_pago = models.DateField()
	numero_recibo = models.CharField(max_length=60, blank=True)
	metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices, default=MetodoPago.EFECTIVO)
	comprobante = models.FileField(upload_to='comprobantes/pagos/%Y/%m/', blank=True)
	observaciones = models.TextField(blank=True)

	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='pagos_honorarios_registrados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-fecha_pago', '-creado_en')
		verbose_name = 'pago de honorario'
		verbose_name_plural = 'pagos de honorarios'

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		self.cobro.actualizar_estado()

	def delete(self, *args, **kwargs):
		cobro = self.cobro
		super().delete(*args, **kwargs)
		cobro.actualizar_estado()

	def __str__(self):
		return f'Pago Bs {self.monto} - {self.cobro.cliente.nombre} ({self.fecha_pago})'
