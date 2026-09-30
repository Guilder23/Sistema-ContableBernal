from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import Credencial
from .permissions import puede_gestionar_credenciales, puede_ver_credenciales, solo_gestores_credenciales


def _volver(request, default_url='credenciales:index', cliente_id=None):
	destino = request.POST.get('volver', '')
	if url_has_allowed_host_and_scheme(
		destino,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	):
		return redirect(destino)
	if cliente_id:
		return redirect('clientes:detalle', cliente_id=cliente_id)
	return redirect(default_url)


@login_required
def index(request):
	if not puede_ver_credenciales(request.user):
		return HttpResponseForbidden('No tienes acceso a las credenciales.')

	busqueda = request.GET.get('q', '').strip()
	sistema_filtro = request.GET.get('sistema', '').strip()
	cliente_filtro = request.GET.get('cliente', '').strip()

	credenciales = Credencial.objects.select_related('cliente', 'creado_por', 'actualizado_por').all()

	if busqueda:
		credenciales = credenciales.filter(
			Q(cliente__nombre__icontains=busqueda)
			| Q(cliente__nit__icontains=busqueda)
			| Q(usuario__icontains=busqueda)
			| Q(sistema_personalizado__icontains=busqueda)
			| Q(observaciones__icontains=busqueda)
		)
	if sistema_filtro in {valor for valor, _ in Credencial.Sistema.choices}:
		credenciales = credenciales.filter(sistema=sistema_filtro)
	if cliente_filtro.isdigit():
		credenciales = credenciales.filter(cliente_id=int(cliente_filtro))

	paginador = Paginator(credenciales, 25)
	query_params = request.GET.copy()
	query_params.pop('page', None)
	page_obj = paginador.get_page(request.GET.get('page'))

	clientes = Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre')
	puede_gestionar = puede_gestionar_credenciales(request.user)

	return render(request, 'credenciales/credenciales.html', {
		'credenciales': page_obj.object_list,
		'page_obj': page_obj,
		'total_credenciales': paginador.count,
		'query_string': query_params.urlencode(),
		'busqueda': busqueda,
		'sistema_filtro': sistema_filtro,
		'cliente_filtro': cliente_filtro,
		'sistemas': Credencial.Sistema.choices,
		'clientes': clientes,
		'puede_gestionar': puede_gestionar,
		'volver': request.get_full_path(),
	})


@login_required
def revelar_password(request, credencial_id):
	if not puede_ver_credenciales(request.user):
		return JsonResponse({'error': 'No autorizado'}, status=403)

	credencial = get_object_or_404(Credencial, pk=credencial_id)
	return JsonResponse({'password': credencial.password})


@solo_gestores_credenciales
@require_POST
def crear(request):
	cliente_id = request.POST.get('cliente_id')
	cliente = get_object_or_404(Cliente, pk=cliente_id)

	sistema = request.POST.get('sistema', Credencial.Sistema.IMPUESTOS)
	sistema_personalizado = request.POST.get('sistema_personalizado', '').strip()
	usuario = request.POST.get('usuario', '').strip()
	password = request.POST.get('password', '').strip()
	url = request.POST.get('url', '').strip()
	codigo_extra = request.POST.get('codigo_extra', '').strip()
	observaciones = request.POST.get('observaciones', '').strip()

	if not usuario or not password:
		messages.error(request, 'El usuario y la contraseña son obligatorios.')
		return _volver(request, cliente_id=cliente.pk)

	credencial = Credencial.objects.create(
		cliente=cliente,
		sistema=sistema,
		sistema_personalizado=sistema_personalizado,
		usuario=usuario,
		password=password,
		url=url,
		codigo_extra=codigo_extra,
		observaciones=observaciones,
		creado_por=request.user,
		actualizado_por=request.user,
	)

	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.CREDENCIAL,
		titulo=f'Credencial creada: {credencial.nombre_sistema}',
		descripcion=f'Usuario: {usuario}',
	)

	messages.success(request, f'Credencial de {credencial.nombre_sistema} agregada correctamente.')
	return _volver(request, cliente_id=cliente.pk)


@solo_gestores_credenciales
@require_POST
def editar(request, credencial_id):
	credencial = get_object_or_404(Credencial, pk=credencial_id)
	cliente = credencial.cliente

	sistema = request.POST.get('sistema', credencial.sistema)
	sistema_personalizado = request.POST.get('sistema_personalizado', '').strip()
	usuario = request.POST.get('usuario', '').strip()
	password = request.POST.get('password', '').strip()
	url = request.POST.get('url', '').strip()
	codigo_extra = request.POST.get('codigo_extra', '').strip()
	observaciones = request.POST.get('observaciones', '').strip()

	if not usuario:
		messages.error(request, 'El usuario es obligatorio.')
		return _volver(request, cliente_id=cliente.pk)

	credencial.sistema = sistema
	credencial.sistema_personalizado = sistema_personalizado
	credencial.usuario = usuario
	if password:
		credencial.password = password
	credencial.url = url
	credencial.codigo_extra = codigo_extra
	credencial.observaciones = observaciones
	credencial.actualizado_por = request.user
	credencial.save()

	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.CREDENCIAL,
		titulo=f'Credencial actualizada: {credencial.nombre_sistema}',
		descripcion=f'Usuario: {usuario}',
	)

	messages.success(request, f'Credencial de {credencial.nombre_sistema} actualizada.')
	return _volver(request, cliente_id=cliente.pk)


@solo_gestores_credenciales
@require_POST
def eliminar(request, credencial_id):
	credencial = get_object_or_404(Credencial, pk=credencial_id)
	cliente = credencial.cliente
	sistema_nombre = credencial.nombre_sistema
	credencial.delete()

	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.CREDENCIAL,
		titulo=f'Credencial eliminada: {sistema_nombre}',
		descripcion=f'Sistema {sistema_nombre} eliminado de la ficha del cliente.',
	)

	messages.success(request, f'Credencial de {sistema_nombre} eliminada.')
	return _volver(request, cliente_id=cliente.pk)
