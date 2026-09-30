from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_usuario(sender, instance, created, raw=False, **kwargs):
	if created and not raw:
		rol = PerfilUsuario.Rol.ADMINISTRADOR if instance.is_superuser else PerfilUsuario.Rol.AUXILIAR
		PerfilUsuario.objects.create(usuario=instance, rol=rol)