from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Requerimiento(models.Model):
	class Estado(models.TextChoices):
		NUEVO = 'nuevo', 'Nuevo'
		EN_PROCESO = 'en_proceso', 'En proceso'
		TERMINADO = 'terminado', 'Terminado'

	class Prioridad(models.TextChoices):
		BAJA = 'baja', 'Baja'
		NORMAL = 'normal', 'Normal'
		ALTA = 'alta', 'Alta'
		URGENTE = 'urgente', 'Urgente'

	cliente = models.ForeignKey(
		'clientes.Cliente',
		on_delete=models.CASCADE,
		related_name='requerimientos',
	)
	titulo = models.CharField(max_length=180)
	descripcion = models.TextField()
	estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.NUEVO)
	prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL)
	fecha_limite = models.DateField(null=True, blank=True)
	responsable = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='requerimientos_asignados',
	)
	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='requerimientos_creados',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)
	terminado_en = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ('estado', 'fecha_limite', '-creado_en')
		verbose_name = 'requerimiento'
		verbose_name_plural = 'requerimientos'

	def __str__(self):
		return f'{self.cliente.nombre}: {self.titulo}'


class ComentarioRequerimiento(models.Model):
	requerimiento = models.ForeignKey(Requerimiento, on_delete=models.CASCADE, related_name='comentarios')
	autor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='comentarios_requerimientos',
	)
	texto = models.TextField()
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('creado_en', 'pk')
		verbose_name = 'comentario de requerimiento'
		verbose_name_plural = 'comentarios de requerimientos'


class ArchivoRequerimiento(models.Model):
	requerimiento = models.ForeignKey(Requerimiento, on_delete=models.CASCADE, related_name='archivos')
	archivo = models.FileField(upload_to='requerimientos/%Y/%m/')
	nombre = models.CharField(max_length=255)
	subido_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='archivos_requerimientos_subidos',
	)
	subido_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-subido_en',)
		verbose_name = 'archivo de requerimiento'
		verbose_name_plural = 'archivos de requerimientos'

	def clean(self):
		if self.archivo and self.archivo.size > 10 * 1024 * 1024:
			raise ValidationError({'archivo': 'El archivo no puede superar 10 MB.'})
