from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from apps.usuarios.models import PerfilUsuario


CREDENCIALES_REAUTH_SESSION_KEY = 'credenciales_reautenticadas'


def requiere_reautenticacion_credenciales(vista):
	@wraps(vista)
	@login_required
	def protegida(request, *args, **kwargs):
		if not request.session.get(CREDENCIALES_REAUTH_SESSION_KEY):
			login_url = reverse('usuarios:login')
			parametros = urlencode({
				'next': request.get_full_path(),
				'reauth': 'credenciales',
			})
			return redirect(f'{login_url}?{parametros}')
		return vista(request, *args, **kwargs)
	return protegida


def limpiar_reautenticacion_credenciales(request):
	request.session.pop(CREDENCIALES_REAUTH_SESSION_KEY, None)


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
