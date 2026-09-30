from django.conf import settings
from django.db import models
from django.utils import timezone


class Notificacion(models.Model):
	class Tipo(models.TextChoices):
		TAREA_ASIGNADA = 'tarea_asignada', 'Tarea asignada'
		TAREA_COMPLETADA = 'tarea_completada', 'Tarea completada'

	destinatario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='notificaciones',
	)
	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='notificaciones_generadas',
	)
	tipo = models.CharField(max_length=24, choices=Tipo.choices)
	titulo = models.CharField(max_length=140)
	mensaje = models.CharField(max_length=280)
	url = models.CharField(max_length=500, blank=True)
	creada_en = models.DateTimeField(auto_now_add=True)
	leida_en = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ('-creada_en', '-pk')
		verbose_name = 'notificación'
		verbose_name_plural = 'notificaciones'

	@property
	def leida(self):
		return self.leida_en is not None

	def marcar_leida(self):
		if self.leida_en is None:
			self.leida_en = timezone.now()
			self.save(update_fields=('leida_en',))

	def __str__(self):
		return f'{self.get_tipo_display()}: {self.titulo}'
