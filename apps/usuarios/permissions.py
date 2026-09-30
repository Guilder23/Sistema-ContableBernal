from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .models import PerfilUsuario


def es_administrador(usuario):
	if not usuario.is_authenticated:
		return False
	return usuario.is_superuser or PerfilUsuario.objects.filter(
		usuario=usuario,
		rol=PerfilUsuario.Rol.ADMINISTRADOR,
	).exists()


def solo_administradores(vista):
	@wraps(vista)
	@login_required
	def protegida(request, *args, **kwargs):
		if not es_administrador(request.user):
			return HttpResponseForbidden('Esta sección requiere rol administrador.')
		return vista(request, *args, **kwargs)
	return protegida
