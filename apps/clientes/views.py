from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.credenciales.models import Credencial
from apps.credenciales.permissions import puede_gestionar_credenciales, puede_ver_credenciales
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial
from apps.obligaciones.models import ConfiguracionCliente, Obligacion, TipoObligacion
from apps.tareas.models import Tarea

from .models import Cliente
from .permissions import puede_gestionar_clientes, solo_gestores_clientes


def _datos_formulario(request, cliente=None):
	if request.method == 'POST':
		return {
			'nombre': request.POST.get('nombre', '').strip(),
			'tipo': request.POST.get('tipo', Cliente.Tipo.PERSONA_NATURAL),
			'nit': request.POST.get('nit', '').strip(),
			'ci': request.POST.get('ci', '').strip(),
			'actividad': request.POST.get('actividad', Cliente.Actividad.OTRA),
			'telefono': request.POST.get('telefono', '').strip(),
			'whatsapp': request.POST.get('whatsapp', '').strip(),
			'correo': request.POST.get('correo', '').strip(),
			'direccion': request.POST.get('direccion', '').strip(),
			'estado': Cliente.Estado.ACTIVO if request.POST.get('estado') == 'activo' else Cliente.Estado.INACTIVO,
			'fecha_inicio': request.POST.get('fecha_inicio', '').strip(),
			'observaciones': request.POST.get('observaciones', '').strip(),
		}
	if cliente is None:
		return {
			'nombre': '', 'tipo': Cliente.Tipo.PERSONA_NATURAL, 'nit': '', 'ci': '',
			'actividad': Cliente.Actividad.OTRA, 'telefono': '', 'whatsapp': '',
			'correo': '', 'direccion': '', 'estado': Cliente.Estado.ACTIVO,
			'fecha_inicio': '', 'observaciones': '',
		}
	return {
		'nombre': cliente.nombre,
		'tipo': cliente.tipo,
		'nit': cliente.nit or '',
		'ci': cliente.ci,
		'actividad': cliente.actividad,
		'telefono': cliente.telefono,
		'whatsapp': cliente.whatsapp,
		'correo': cliente.correo,
		'direccion': cliente.direccion,
		'estado': cliente.estado,
		'fecha_inicio': cliente.fecha_inicio.isoformat() if cliente.fecha_inicio else '',
		'observaciones': cliente.observaciones,
	}


def _validar_formulario(request, cliente=None):
	datos = _datos_formulario(request, cliente)
	errores = {}
	if not datos['nombre']:
		errores['nombre'] = 'El nombre o razón social es obligatorio.'
	elif len(datos['nombre']) > 180:
		errores['nombre'] = 'El nombre no puede superar 180 caracteres.'

	if datos['nit']:
		duplicados = Cliente.objects.filter(nit__iexact=datos['nit'])
		if cliente is not None:
			duplicados = duplicados.exclude(pk=cliente.pk)
		if duplicados.exists():
			errores['nit'] = 'Ya existe un cliente con ese NIT.'
		if len(datos['nit']) > 20:
			errores['nit'] = 'El NIT no puede superar 20 caracteres.'
	if len(datos['ci']) > 20:
		errores['ci'] = 'La CI no puede superar 20 caracteres.'
	for campo, limite in (('telefono', 30), ('whatsapp', 30), ('correo', 254), ('direccion', 240)):
		if len(datos[campo]) > limite:
			errores[campo] = f'Este campo no puede superar {limite} caracteres.'

	if datos['correo']:
		try:
			validate_email(datos['correo'])
		except ValidationError:
			errores['correo'] = 'Ingresa un correo electrónico válido.'
	if datos['tipo'] not in {valor for valor, _ in Cliente.Tipo.choices}:
		errores['tipo'] = 'Selecciona un tipo de cliente válido.'
	if datos['actividad'] not in {valor for valor, _ in Cliente.Actividad.choices}:
		errores['actividad'] = 'Selecciona una actividad válida.'
	if datos['estado'] not in {valor for valor, _ in Cliente.Estado.choices}:
		errores['estado'] = 'Selecciona un estado válido.'
	if datos['fecha_inicio'] and parse_date(datos['fecha_inicio']) is None:
		errores['fecha_inicio'] = 'Ingresa una fecha válida.'
	return datos, errores


def _guardar_cliente(request, cliente=None):
	datos, errores = _validar_formulario(request, cliente)
	if errores:
		return None, datos, errores
	es_nuevo = cliente is None
	with transaction.atomic():
		if cliente is None:
			cliente = Cliente(creado_por=request.user)
		for campo in ('nombre', 'tipo', 'ci', 'actividad', 'telefono', 'whatsapp', 'correo', 'direccion', 'estado', 'observaciones'):
			setattr(cliente, campo, datos[campo])
		cliente.nit = datos['nit'] or None
		cliente.fecha_inicio = parse_date(datos['fecha_inicio']) if datos['fecha_inicio'] else None
		cliente.save()

		if es_nuevo:
			registrar_historial(
				cliente=cliente,
				usuario=request.user,
				tipo_accion=EntradaHistorial.TipoAccion.CREACION,
				titulo='Cliente creado',
				descripcion=f'Registro inicial como {cliente.get_tipo_display()} ({cliente.get_actividad_display()}).',
			)
		else:
			registrar_historial(
				cliente=cliente,
				usuario=request.user,
				tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
				titulo='Datos del cliente actualizados',
				descripcion=f'Estado: {cliente.get_estado_display()} · Actividad: {cliente.get_actividad_display()}',
			)

	return cliente, datos, {}


@login_required
def index(request):
	return render(request, 'clientes/clientes.html', _contexto_listado(request))


def _contexto_listado(request, datos=None, errores=None, modal_activo='', cliente_edicion=None):
	clientes = Cliente.objects.select_related('creado_por')
	busqueda = request.GET.get('q', '').strip()
	tipo = request.GET.get('tipo', '')
	estado = request.GET.get('estado', '')
	if busqueda:
		clientes = clientes.filter(
			Q(nombre__icontains=busqueda)
			| Q(nit__icontains=busqueda)
			| Q(ci__icontains=busqueda)
			| Q(correo__icontains=busqueda)
		)
	if tipo in {valor for valor, _ in Cliente.Tipo.choices}:
		clientes = clientes.filter(tipo=tipo)
	if estado in {valor for valor, _ in Cliente.Estado.choices}:
		clientes = clientes.filter(estado=estado)
	paginador = Paginator(clientes, 12)
	parametros = request.GET.copy()
	parametros.pop('page', None)
	page_obj = paginador.get_page(request.GET.get('page'))
	puede_gestionar = puede_gestionar_clientes(request.user)
	return {
		'clientes': page_obj.object_list,
		'page_obj': page_obj,
		'total_clientes': paginador.count,
		'query_string': parametros.urlencode(),
		'busqueda': busqueda,
		'tipo_filtro': tipo,
		'estado_filtro': estado,
		'tipos': Cliente.Tipo.choices,
		'actividades': Cliente.Actividad.choices,
		'estados': Cliente.Estado.choices,
		'puede_gestionar': puede_gestionar,
		'datos': datos or {},
		'errores': errores or {},
		'modal_activo': modal_activo,
		'cliente_edicion': cliente_edicion,
	}


@solo_gestores_clientes
@require_POST
def crear(request):
	cliente, datos, errores = _guardar_cliente(request)
	if cliente:
		messages.success(request, f'El cliente {cliente.nombre} fue creado.')
		return redirect('clientes:detalle', cliente_id=cliente.pk)
	contexto = _contexto_listado(request, datos=datos, errores=errores, modal_activo='modal-crear')
	return render(request, 'clientes/clientes.html', contexto)


@solo_gestores_clientes
@require_POST
def editar(request, cliente_id):
	cliente = get_object_or_404(Cliente, pk=cliente_id)
	cliente_guardado, datos, errores = _guardar_cliente(request, cliente)
	siguiente = request.POST.get('volver', '')
	if cliente_guardado:
		messages.success(request, f'El cliente {cliente_guardado.nombre} fue actualizado.')
		if siguiente:
			return redirect(siguiente)
		return redirect('clientes:detalle', cliente_id=cliente_guardado.pk)
	contexto = _contexto_listado(
		request,
		datos=datos,
		errores=errores,
		modal_activo='modal-editar',
		cliente_edicion=cliente,
	)
	return render(request, 'clientes/clientes.html', contexto)


@solo_gestores_clientes
@require_POST
def eliminar(request, cliente_id):
	cliente = get_object_or_404(Cliente, pk=cliente_id)
	nombre = cliente.nombre
	cliente.delete()
	messages.success(request, f'El cliente {nombre} fue eliminado.')
	return redirect('clientes:index')


@login_required
def detalle(request, cliente_id):
	cliente = get_object_or_404(Cliente.objects.select_related('creado_por'), pk=cliente_id)
	hoy = timezone.localdate()

	# Configuraciones de obligaciones activas
	configuraciones = (
		ConfiguracionCliente.objects.filter(cliente=cliente)
		.select_related('tipo')
		.order_by('tipo__periodicidad', 'tipo__nombre')
	)
	config_tipos_ids = {c.tipo_id for c in configuraciones if c.activa}

	# Todos los tipos de obligaciones disponibles agrupados
	tipos_disponibles = TipoObligacion.objects.filter(activa=True).order_by('periodicidad', 'nombre')
	tipos_mensuales = [t for t in tipos_disponibles if t.periodicidad == TipoObligacion.Periodicidad.MENSUAL]
	tipos_trimestrales = [t for t in tipos_disponibles if t.periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL]
	tipos_anuales = [t for t in tipos_disponibles if t.periodicidad == TipoObligacion.Periodicidad.ANUAL]

	# Credenciales
	puede_ver_cred = puede_ver_credenciales(request.user)
	puede_gest_cred = puede_gestionar_credenciales(request.user)
	credenciales = cliente.credenciales.select_related('creado_por', 'actualizado_por').all() if puede_ver_cred else []

	# Tareas del cliente
	tareas = Tarea.objects.filter(obligacion__cliente=cliente).select_related(
		'obligacion__tipo', 'responsable', 'evidencia_subida_por'
	).order_by('-obligacion__fecha_vencimiento')

	tareas_pendientes = [t for t in tareas if t.obligacion.estado in (Obligacion.Estado.PENDIENTE, Obligacion.Estado.EN_PROCESO)]
	tareas_vencidas = [t for t in tareas_pendientes if t.obligacion.fecha_vencimiento and t.obligacion.fecha_vencimiento < hoy]
	tareas_completadas = [t for t in tareas if t.obligacion.estado == Obligacion.Estado.COMPLETADA]

	# Historial reciente
	historial = cliente.historial.select_related('usuario')[:20]

	puede_gestionar = puede_gestionar_clientes(request.user)

	return render(request, 'clientes/detalle.html', {
		'cliente': cliente,
		'configuraciones': configuraciones,
		'config_tipos_ids': config_tipos_ids,
		'tipos_mensuales': tipos_mensuales,
		'tipos_trimestrales': tipos_trimestrales,
		'tipos_anuales': tipos_anuales,
		'credenciales': credenciales,
		'puede_ver_cred': puede_ver_cred,
		'puede_gest_cred': puede_gest_cred,
		'sistemas_credenciales': Credencial.Sistema.choices,
		'tareas_pendientes': tareas_pendientes[:15],
		'tareas_vencidas': tareas_vencidas,
		'tareas_completadas': tareas_completadas[:10],
		'total_tareas': len(tareas),
		'historial': historial,
		'hoy': hoy,
		'puede_gestionar': puede_gestionar,
		'tipos': Cliente.Tipo.choices,
		'actividades': Cliente.Actividad.choices,
		'estados': Cliente.Estado.choices,
	})
