from django.conf import settings
from django.db import models


class Credencial(models.Model):
	class Sistema(models.TextChoices):
		IMPUESTOS = 'impuestos', 'Impuestos Nacionales (SIAT)'
		CAJA_SALUD = 'caja_salud', 'Caja de Salud (CNS/Otras)'
		GESTORA = 'gestora', 'Gestora Pública'
		MINISTERIO = 'ministerio', 'Ministerio de Trabajo (OVT)'
		SEPREC = 'seprec', 'SEPREC'
		BANCO = 'banco', 'Banca / Portal Financiero'
		OTRO = 'otro', 'Otro sistema'

	cliente = models.ForeignKey(
		'clientes.Cliente',
		on_delete=models.CASCADE,
		related_name='credenciales',
	)
	sistema = models.CharField(max_length=24, choices=Sistema.choices, default=Sistema.IMPUESTOS)
	sistema_personalizado = models.CharField(max_length=120, blank=True)
	usuario = models.CharField(max_length=150)
	password = models.CharField(max_length=255)
	url = models.URLField(max_length=300, blank=True)
	codigo_extra = models.CharField(max_length=120, blank=True, help_text='PIN, tarjeta de coordenadas, correo vinculado u otro dato.')
	observaciones = models.TextField(blank=True)

	creado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='credenciales_creadas',
	)
	actualizado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='credenciales_actualizadas',
	)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('cliente__nombre', 'sistema', 'usuario')
		verbose_name = 'credencial'
		verbose_name_plural = 'credenciales'

	@property
	def nombre_sistema(self):
		if self.sistema == self.Sistema.OTRO and self.sistema_personalizado:
			return self.sistema_personalizado
		return self.get_sistema_display()

	def __str__(self):
		return f'{self.cliente.nombre} - {self.nombre_sistema} ({self.usuario})'
