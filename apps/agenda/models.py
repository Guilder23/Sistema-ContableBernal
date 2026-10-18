import base64
import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from cryptography.fernet import Fernet


class GoogleCalendarCredential(models.Model):
	singleton = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
	refresh_token_encrypted = models.TextField()
	conectado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'conexión de Google Calendar'
		verbose_name_plural = 'conexión de Google Calendar'

	@staticmethod
	def _fernet():
		key = getattr(settings, 'GOOGLE_TOKEN_ENCRYPTION_KEY', '')
		if not key:
			clave_derivada = hmac.new(
				settings.SECRET_KEY.encode(),
				b'contablebernal-google-calendar-token',
				hashlib.sha256,
			).digest()
			key = base64.urlsafe_b64encode(clave_derivada).decode()
		return Fernet(key.encode())

	def set_refresh_token(self, token):
		self.refresh_token_encrypted = self._fernet().encrypt(token.encode()).decode()

	def get_refresh_token(self):
		return self._fernet().decrypt(self.refresh_token_encrypted.encode()).decode()


class EventoAgenda(models.Model):
	class Tipo(models.TextChoices):
		CITA = 'cita', 'Cita'
		RECORDATORIO = 'recordatorio', 'Recordatorio'

	class Estado(models.TextChoices):
		PROGRAMADO = 'programado', 'Programado'
		COMPLETADO = 'completado', 'Completado'
		CANCELADO = 'cancelado', 'Cancelado'

	titulo = models.CharField(max_length=160)
	tipo = models.CharField(max_length=16, choices=Tipo.choices, default=Tipo.CITA)
	fecha = models.DateField()
	hora_inicio = models.TimeField()
	hora_fin = models.TimeField()
	cliente = models.ForeignKey(
		'clientes.Cliente',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='eventos_agenda',
	)
	responsable = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='eventos_agenda_asignados',
	)
	estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADO)
	lugar = models.CharField(max_length=160, blank=True, default='')
	observaciones = models.TextField(blank=True, default='')
	google_event_id = models.CharField(max_length=255, blank=True, default='')
	google_sync_status = models.CharField(
		max_length=12,
		choices=(('pending', 'Pendiente'), ('synced', 'Sincronizado'), ('error', 'Error')),
		default='pending',
	)
	google_sync_error = models.CharField(max_length=500, blank=True, default='')
	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='eventos_agenda_creados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('fecha', 'hora_inicio', 'titulo')
		verbose_name = 'evento de agenda'
		verbose_name_plural = 'eventos de agenda'

	def clean(self):
		super().clean()
		if not self.fecha or not self.hora_inicio or not self.hora_fin:
			return
		if self.hora_fin <= self.hora_inicio:
			raise ValidationError({'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'})
		if not self.responsable_id or self.estado == self.Estado.CANCELADO:
			return
		solapados = type(self).objects.filter(
			responsable_id=self.responsable_id,
			fecha=self.fecha,
			estado=self.Estado.PROGRAMADO,
			hora_inicio__lt=self.hora_fin,
			hora_fin__gt=self.hora_inicio,
		)
		if self.pk:
			solapados = solapados.exclude(pk=self.pk)
		if solapados.exists():
			raise ValidationError({'hora_inicio': 'El horario se cruza con otro evento del mismo responsable.'})

	def __str__(self):
		return f'{self.titulo} - {self.fecha:%d/%m/%Y}'