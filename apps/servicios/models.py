from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ClienteOcasional(models.Model):
	nombre = models.CharField(max_length=180)
	documento = models.CharField(max_length=30, blank=True, default='')
	telefono = models.CharField(max_length=30, blank=True, default='')
	correo = models.EmailField(blank=True, default='')
	direccion = models.CharField(max_length=240, blank=True, default='')
	observaciones = models.TextField(blank=True, default='')
	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='clientes_ocasionales_creados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('nombre', 'pk')
		verbose_name = 'cliente ocasional'
		verbose_name_plural = 'clientes ocasionales'

	def __str__(self):
		return self.nombre


class ServicioTramite(models.Model):
	class Tipo(models.TextChoices):
		LICENCIA = 'licencia', 'Licencia'
		TRAMITE = 'tramite', 'Trámite'
		CERTIFICADO = 'certificado', 'Certificado'
		OTRO = 'otro', 'Otro'

	class Estado(models.TextChoices):
		NUEVO = 'nuevo', 'Nuevo'
		EN_PROCESO = 'en_proceso', 'En proceso'
		LISTO = 'listo', 'Listo para entrega'
		ENTREGADO = 'entregado', 'Entregado'

	class Prioridad(models.TextChoices):
		NORMAL = 'normal', 'Normal'
		ALTA = 'alta', 'Alta'
		URGENTE = 'urgente', 'Urgente'

	class EstadoCobro(models.TextChoices):
		PENDIENTE = 'pendiente', 'Pendiente'
		PARCIAL = 'parcial', 'Pago parcial'
		PAGADO = 'pagado', 'Pagado'

	cliente = models.ForeignKey(
		ClienteOcasional,
		on_delete=models.PROTECT,
		related_name='servicios',
	)
	tipo = models.CharField(max_length=16, choices=Tipo.choices, default=Tipo.TRAMITE)
	concepto = models.CharField(max_length=180)
	descripcion = models.TextField(blank=True, default='')
	estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.NUEVO)
	prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL)
	fecha_solicitud = models.DateField(default=timezone.localdate)
	fecha_limite = models.DateField(null=True, blank=True)
	fecha_entrega = models.DateField(null=True, blank=True)
	monto_total = models.DecimalField(max_digits=12, decimal_places=2)
	responsable = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='servicios_ocasionales_asignados',
	)
	observaciones = models.TextField(blank=True, default='')
	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='servicios_ocasionales_registrados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-fecha_solicitud', '-pk')
		verbose_name = 'servicio o trámite ocasional'
		verbose_name_plural = 'servicios y trámites ocasionales'

	def clean(self):
		if self.monto_total is not None and self.monto_total <= 0:
			raise ValidationError({'monto_total': 'El monto total debe ser mayor a cero.'})

	@property
	def total_pagado(self):
		return sum((pago.monto for pago in self.pagos.all()), Decimal('0.00'))

	@property
	def saldo_pendiente(self):
		return max(Decimal('0.00'), self.monto_total - self.total_pagado)

	@property
	def estado_cobro(self):
		if self.saldo_pendiente <= Decimal('0.00'):
			return self.EstadoCobro.PAGADO
		if self.total_pagado > Decimal('0.00'):
			return self.EstadoCobro.PARCIAL
		return self.EstadoCobro.PENDIENTE

	def get_estado_cobro_display(self):
		return self.EstadoCobro(self.estado_cobro).label

	def __str__(self):
		return f'{self.cliente.nombre} - {self.concepto}'


class PagoServicioTramite(models.Model):
	class MetodoPago(models.TextChoices):
		EFECTIVO = 'efectivo', 'Efectivo'
		TRANSFERENCIA = 'transferencia', 'Transferencia QR / bancaria'
		DEPOSITO = 'deposito', 'Depósito bancario'
		CHEQUE = 'cheque', 'Cheque'
		OTRO = 'otro', 'Otro'

	servicio = models.ForeignKey(ServicioTramite, on_delete=models.PROTECT, related_name='pagos')
	monto = models.DecimalField(max_digits=12, decimal_places=2)
	fecha_pago = models.DateField(default=timezone.localdate)
	metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices, default=MetodoPago.EFECTIVO)
	numero_recibo = models.CharField(max_length=60, blank=True, default='')
	observaciones = models.TextField(blank=True, default='')
	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='pagos_servicios_ocasionales_registrados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('fecha_pago', 'pk')
		verbose_name = 'pago de servicio ocasional'
		verbose_name_plural = 'pagos de servicios ocasionales'

	def clean(self):
		if self.monto is not None and self.monto <= 0:
			raise ValidationError({'monto': 'El pago debe ser mayor a cero.'})

	def __str__(self):
		return f'Pago Bs {self.monto} - {self.servicio.concepto}'
