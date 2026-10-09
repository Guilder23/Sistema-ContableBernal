from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import PerfilUsuario
from .permissions import solo_administradores


def _datos_formulario(request, usuario=None):
	if request.method == 'POST':
		return {
			'username': request.POST.get('username', '').strip(),
			'first_name': request.POST.get('first_name', '').strip(),
			'last_name': request.POST.get('last_name', '').strip(),
			'email': request.POST.get('email', '').strip(),
			'rol': request.POST.get('rol', PerfilUsuario.Rol.AUXILIAR),
			'is_active': request.POST.get('is_active') == 'on',
		}
	if usuario is None:
		return {'username': '', 'first_name': '', 'last_name': '', 'email': '', 'rol': PerfilUsuario.Rol.AUXILIAR, 'is_active': True}
	return {
		'username': usuario.username,
		'first_name': usuario.first_name,
		'last_name': usuario.last_name,
		'email': usuario.email,
		'rol': usuario.perfil.rol,
		'is_active': usuario.is_active,
	}


def _validar_formulario(request, usuario=None, es_nuevo=False):
	datos = _datos_formulario(request, usuario)
	errores = {}
	modelo_usuario = get_user_model()
	username = datos['username']
	email = datos['email']
	password = request.POST.get('password', '')
	confirmacion = request.POST.get('password_confirm', '')
	roles_validos = {valor for valor, _ in PerfilUsuario.Rol.choices}

	if not username:
		errores['username'] = 'El nombre de usuario es obligatorio.'
	elif len(username) > 150:
		errores['username'] = 'El nombre de usuario no puede superar 150 caracteres.'
	else:
		usuarios_existentes = modelo_usuario.objects.filter(username__iexact=username)
		if usuario is not None:
			usuarios_existentes = usuarios_existentes.exclude(pk=usuario.pk)
		if usuarios_existentes.exists():
			errores['username'] = 'Ya existe una cuenta con ese nombre de usuario.'

	if email:
		try:
			validate_email(email)
		except ValidationError:
			errores['email'] = 'Ingresa un correo electrónico válido.'
		if len(email) > 254:
			errores['email'] = 'El correo no puede superar 254 caracteres.'

	if datos['rol'] not in roles_validos:
		errores['rol'] = 'Selecciona un rol válido.'

	if es_nuevo and not password:
		errores['password'] = 'La contraseña es obligatoria.'
	elif password:
		if password != confirmacion:
			errores['password_confirm'] = 'Las contraseñas no coinciden.'
		else:
			cuenta_validar = usuario or modelo_usuario(username=username, email=email)
			try:
				from django.contrib.auth.password_validation import validate_password

				validate_password(password, user=cuenta_validar)
			except ValidationError as error:
				errores['password'] = ' '.join(error.messages)
	elif confirmacion:
		errores['password_confirm'] = 'Escribe primero la contraseña nueva.'

	if usuario is not None and usuario.is_superuser and not request.user.is_superuser:
		errores['general'] = 'Solo un superusuario puede modificar esta cuenta.'

	if usuario is not None and usuario.is_active and usuario.perfil.rol == PerfilUsuario.Rol.ADMINISTRADOR:
		seguira_como_admin = datos['is_active'] and datos['rol'] == PerfilUsuario.Rol.ADMINISTRADOR
		if not seguira_como_admin:
			admins_activos = PerfilUsuario.objects.filter(
				rol=PerfilUsuario.Rol.ADMINISTRADOR,
				usuario__is_active=True,
			).exclude(usuario=usuario).count()
			if admins_activos == 0:
				errores['rol'] = 'No puedes desactivar o cambiar el rol del único administrador activo.'

	return datos, errores, password


def _guardar_usuario(request, usuario=None, es_nuevo=False):
	datos, errores, password = _validar_formulario(request, usuario, es_nuevo)
	if errores:
		return None, datos, errores

	modelo_usuario = get_user_model()
	usuario_nuevo = usuario is None
	with transaction.atomic():
		if usuario is None:
			usuario = modelo_usuario(username=datos['username'])
		usuario.username = datos['username']
		usuario.first_name = datos['first_name']
		usuario.last_name = datos['last_name']
		usuario.email = datos['email']
		usuario.is_active = datos['is_active']
		if password:
			usuario.set_password(password)
		usuario.save()
		perfil, _ = PerfilUsuario.objects.get_or_create(
			usuario=usuario,
			defaults={'creado_por': request.user},
		)
		if usuario_nuevo and perfil.creado_por_id is None:
			perfil.creado_por = request.user
		perfil.rol = datos['rol']
		campos_actualizados = ['rol', 'actualizado_en']
		if usuario_nuevo:
			campos_actualizados.append('creado_por')
		perfil.save(update_fields=campos_actualizados)
	return usuario, datos, {}


def login_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard:index')

	siguiente = request.POST.get('next') or request.GET.get('next', '')
	error = ''
	if request.method == 'POST':
		usuario = request.POST.get('username', '').strip()
		contrasena = request.POST.get('password', '')
		cuenta = authenticate(request, username=usuario, password=contrasena)
		if cuenta is not None:
			login(request, cuenta)
			if siguiente and url_has_allowed_host_and_scheme(
				siguiente,
				allowed_hosts={request.get_host()},
				require_https=request.is_secure(),
			):
				return redirect(siguiente)
			return redirect('dashboard:index')
		error = 'Usuario o contraseña incorrectos.'

	return render(request, 'usuarios/login.html', {'error': error, 'siguiente': siguiente})


@login_required
def logout_view(request):
	if request.method == 'POST':
		logout(request)
	return redirect('usuarios:login')


@solo_administradores
def index(request):
	return render(request, 'usuarios/usuarios.html', _contexto_listado(request))


def _contexto_listado(request, datos=None, errores=None, modal_activo='', usuario_edicion=None):
	usuarios = get_user_model().objects.select_related('perfil', 'perfil__creado_por').order_by('username')
	busqueda = request.GET.get('q', '').strip()
	rol = request.GET.get('rol', '')
	estado = request.GET.get('estado', '')
	if busqueda:
		usuarios = usuarios.filter(
			Q(username__icontains=busqueda)
			| Q(first_name__icontains=busqueda)
			| Q(last_name__icontains=busqueda)
			| Q(email__icontains=busqueda)
		)
	if rol in {valor for valor, _ in PerfilUsuario.Rol.choices}:
		usuarios = usuarios.filter(perfil__rol=rol)
	if estado == 'activo':
		usuarios = usuarios.filter(is_active=True)
	elif estado == 'inactivo':
		usuarios = usuarios.filter(is_active=False)
	paginador = Paginator(usuarios, 12)
	parametros = request.GET.copy()
	parametros.pop('page', None)
	page_obj = paginador.get_page(request.GET.get('page'))
	return {
		'usuarios': page_obj.object_list,
		'page_obj': page_obj,
		'total_usuarios': paginador.count,
		'query_string': parametros.urlencode(),
		'busqueda': busqueda,
		'rol_filtro': rol,
		'estado_filtro': estado,
		'roles': PerfilUsuario.Rol.choices,
		'datos': datos or {},
		'errores': errores or {},
		'modal_activo': modal_activo,
		'usuario_edicion': usuario_edicion,
	}


@solo_administradores
@require_POST
def crear(request):
	usuario, datos, errores = _guardar_usuario(request, es_nuevo=True)
	if usuario:
		registrar_historial(
			cliente=None,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.CREACION,
			seccion=EntradaHistorial.Seccion.USUARIOS,
			referencia=usuario.username,
			titulo=f'Usuario creado: {usuario.username}',
			descripcion=f'Rol asignado: {usuario.perfil.get_rol_display()}',
		)
		messages.success(request, f'La cuenta {usuario.username} fue creada.')
		return redirect('usuarios:index')
	contexto = _contexto_listado(request, datos=datos, errores=errores, modal_activo='modal-crear')
	return render(request, 'usuarios/usuarios.html', contexto)


@solo_administradores
@require_POST
def editar(request, usuario_id):
	usuario = get_object_or_404(get_user_model().objects.select_related('perfil'), pk=usuario_id)
	usuario_guardado, datos, errores = _guardar_usuario(request, usuario=usuario)
	if usuario_guardado:
		registrar_historial(
			cliente=None,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
			seccion=EntradaHistorial.Seccion.USUARIOS,
			referencia=usuario_guardado.username,
			titulo=f'Usuario actualizado: {usuario_guardado.username}',
			descripcion=f'Rol actual: {usuario_guardado.perfil.get_rol_display()} · Activo: {"Sí" if usuario_guardado.is_active else "No"}',
		)
		messages.success(request, f'La cuenta {usuario_guardado.username} fue actualizada.')
		return redirect('usuarios:index')
	contexto = _contexto_listado(
		request,
		datos=datos,
		errores=errores,
		modal_activo='modal-editar',
		usuario_edicion=usuario,
	)
	return render(request, 'usuarios/usuarios.html', contexto)


@solo_administradores
@require_POST
def eliminar(request, usuario_id):
	usuario = get_object_or_404(get_user_model().objects.select_related('perfil'), pk=usuario_id)
	if usuario.is_superuser and not request.user.is_superuser:
		return HttpResponseForbidden('No tienes permiso para eliminar esta cuenta.')
	if usuario.pk == request.user.pk:
		messages.error(request, 'No puedes eliminar tu propia cuenta.')
	elif usuario.is_active and usuario.perfil.rol == PerfilUsuario.Rol.ADMINISTRADOR and not PerfilUsuario.objects.filter(
		rol=PerfilUsuario.Rol.ADMINISTRADOR,
		usuario__is_active=True,
	).exclude(usuario=usuario).exists():
		messages.error(request, 'No puedes eliminar el único administrador activo.')
	else:
		username = usuario.username
		registrar_historial(
			cliente=None,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.OTRO,
			seccion=EntradaHistorial.Seccion.USUARIOS,
			referencia=username,
			titulo=f'Usuario eliminado: {username}',
		)
		usuario.delete()
		messages.success(request, f'La cuenta {username} fue eliminada.')
	return redirect('usuarios:index')
