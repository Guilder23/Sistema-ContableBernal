from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum


class CobroAnterior(models.Model):
	cliente = models.ForeignKey(
		'clientes.Cliente',
		on_delete=models.PROTECT,
		related_name='deudas_anteriores',
	)
	fecha_cobro = models.DateField()
	detalle = models.CharField(max_length=200)
	monto_total = models.DecimalField(max_digits=10, decimal_places=2)
	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='deudas_anteriores_registradas',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-fecha_cobro', 'cliente__nombre', '-pk')
		verbose_name = 'deuda anterior'
		verbose_name_plural = 'deudas anteriores'

	@property
	def monto_pagado(self):
		if hasattr(self, '_prefetched_objects_cache') and 'abonos' in self._prefetched_objects_cache:
			return sum((abono.monto for abono in self.abonos.all()), Decimal('0.00'))
		return self.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

	@property
	def saldo_pendiente(self):
		return max(self.monto_total - self.monto_pagado, Decimal('0.00'))

	@property
	def estado(self):
		if self.saldo_pendiente == Decimal('0.00'):
			return 'pagado'
		if self.monto_pagado > Decimal('0.00'):
			return 'parcial'
		return 'pendiente'

	def get_estado_display(self):
		return {
			'pendiente': 'Pendiente',
			'parcial': 'Pago parcial',
			'pagado': 'Pagado',
		}[self.estado]

	def __str__(self):
		return f'{self.cliente.nombre} - {self.detalle} (Bs {self.monto_total})'


class AbonoDeudaAnterior(models.Model):
	class TipoPago(models.TextChoices):
		EFECTIVO = 'efectivo', 'Efectivo'
		TRANSFERENCIA = 'transferencia', 'Transferencia QR / Bancaria'
		DEPOSITO = 'deposito', 'Depósito bancario'
		CHEQUE = 'cheque', 'Cheque'
		OTRO = 'otro', 'Otro'

	deuda = models.ForeignKey(CobroAnterior, on_delete=models.CASCADE, related_name='abonos')
	fecha_cobro = models.DateField()
	detalle = models.CharField(max_length=200)
	monto = models.DecimalField(max_digits=10, decimal_places=2)
	numero_recibo = models.CharField(max_length=60, blank=True)
	tipo_pago = models.CharField(max_length=20, choices=TipoPago.choices)
	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='abonos_deudas_anteriores_registrados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-fecha_cobro', '-creado_en', '-pk')
		verbose_name = 'abono de deuda anterior'
		verbose_name_plural = 'abonos de deudas anteriores'

	def __str__(self):
		return f'Abono Bs {self.monto} - {self.deuda.cliente.nombre} ({self.fecha_cobro})'
