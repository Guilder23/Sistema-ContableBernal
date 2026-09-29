from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
	class Rol(models.TextChoices):
		ADMINISTRADOR = 'administrador', 'Administrador'
		AUXILIAR = 'auxiliar', 'Auxiliar'
		SECRETARIO = 'secretario', 'Secretario'

	usuario = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='perfil',
	)
	rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.AUXILIAR)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('usuario__username',)
		verbose_name = 'perfil de usuario'
		verbose_name_plural = 'perfiles de usuario'

	def __str__(self):
		return f'{self.usuario.get_username()} - {self.get_rol_display()}'
