from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


MAX_EVIDENCIA_BYTES = 10 * 1024 * 1024
EXTENSIONES_EVIDENCIA = ('pdf', 'png', 'jpg', 'jpeg')


def validar_tamano_evidencia(archivo):
	if archivo.size > MAX_EVIDENCIA_BYTES:
		raise ValidationError('La evidencia no puede superar 10 MB.')


class Tarea(models.Model):
	class Prioridad(models.TextChoices):
		BAJA = 'baja', 'Baja'
		NORMAL = 'normal', 'Normal'
		ALTA = 'alta', 'Alta'
		URGENTE = 'urgente', 'Urgente'

	obligacion = models.OneToOneField(
		'obligaciones.Obligacion',
		on_delete=models.CASCADE,
		related_name='tarea',
	)
	responsable = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='tareas_asignadas',
	)
	asignada_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='tareas_asignadas_por_mi',
	)
	prioridad = models.CharField(max_length=8, choices=Prioridad.choices, default=Prioridad.NORMAL)
	observaciones = models.TextField(blank=True)
	evidencia = models.FileField(
		upload_to='evidencias/tareas/%Y/%m/',
		blank=True,
		validators=[FileExtensionValidator(allowed_extensions=EXTENSIONES_EVIDENCIA), validar_tamano_evidencia],
	)
	evidencia_subida_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='evidencias_tareas_subidas',
	)
	creada_en = models.DateTimeField(auto_now_add=True)
	actualizada_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('obligacion__fecha_vencimiento', 'prioridad', 'obligacion__cliente__nombre')
		verbose_name = 'tarea'
		verbose_name_plural = 'tareas'

	@property
	def estado(self):
		return self.obligacion.estado

	@property
	def cliente(self):
		return self.obligacion.cliente

	@property
	def fecha_limite(self):
		return self.obligacion.fecha_vencimiento

	@property
	def titulo(self):
		return f'{self.obligacion.tipo.nombre} - {self.obligacion.periodo_etiqueta}'

	@property
	def evidencia_nombre(self):
		return Path(self.evidencia.name).name if self.evidencia else ''

	def __str__(self):
		return f'{self.titulo} - {self.cliente.nombre}'
