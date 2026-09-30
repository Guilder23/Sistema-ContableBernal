from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from apps.usuarios.models import PerfilUsuario


def puede_ver_credenciales(usuario):
	if not usuario.is_authenticated:
		return False
	if usuario.is_superuser:
		return True
	try:
		return usuario.perfil.rol in {
			PerfilUsuario.Rol.ADMINISTRADOR,
			PerfilUsuario.Rol.SECRETARIO,
			PerfilUsuario.Rol.AUXILIAR,
		}
	except PerfilUsuario.DoesNotExist:
		return False


def puede_gestionar_credenciales(usuario):
	if not usuario.is_authenticated:
		return False
	if usuario.is_superuser:
		return True
	try:
		return usuario.perfil.rol in {
			PerfilUsuario.Rol.ADMINISTRADOR,
			PerfilUsuario.Rol.SECRETARIO,
		}
	except PerfilUsuario.DoesNotExist:
		return False


def solo_gestores_credenciales(vista):
	@wraps(vista)
	@login_required
	def protegida(request, *args, **kwargs):
		if not puede_gestionar_credenciales(request.user):
			return HttpResponseForbidden('No tienes permisos para crear o modificar credenciales.')
		return vista(request, *args, **kwargs)
	return protegida
