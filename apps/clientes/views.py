from decimal import Decimal

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
			'razon_social': request.POST.get('razon_social', '').strip(),
			'tipo': request.POST.get('tipo', Cliente.Tipo.PERSONA_NATURAL),
			'nit': request.POST.get('nit', '').strip(),
			'ci': request.POST.get('ci', '').strip(),
			'ci_complemento': request.POST.get('ci_complemento', '').strip(),
			'ci_expedido': request.POST.get('ci_expedido', '').strip(),
			'fecha_nacimiento': request.POST.get('fecha_nacimiento', '').strip(),
			'cambio_contador': request.POST.get('cambio_contador') in {'1', 'on', 'true', 'True'},
			'actividad': request.POST.get('actividad', Cliente.Actividad.OTRA),
			'telefono': request.POST.get('telefono', '').strip(),
			'whatsapp': request.POST.get('whatsapp', '').strip(),
			'correo': request.POST.get('correo', '').strip(),
			'direccion': request.POST.get('direccion', '').strip(),
			'estado': Cliente.Estado.ACTIVO if request.POST.get('estado') == 'activo' else Cliente.Estado.INACTIVO,
			'fecha_inicio': request.POST.get('fecha_inicio', '').strip(),
			'tiene_representante_legal': request.POST.get('tiene_representante_legal') in {'1', 'on', 'true', 'True'},
			'representante_legal_nombre': request.POST.get('representante_legal_nombre', '').strip(),
			'representante_legal_carnet': request.POST.get('representante_legal_carnet', '').strip(),
			'representante_legal_complemento': request.POST.get('representante_legal_complemento', '').strip(),
			'representante_legal_expedido': request.POST.get('representante_legal_expedido', '').strip(),
			'representante_legal_celular': request.POST.get('representante_legal_celular', '').strip(),
			'representante_legal_fecha_nacimiento': request.POST.get('representante_legal_fecha_nacimiento', '').strip(),
			'observaciones': request.POST.get('observaciones', '').strip(),
		}
	if cliente is None:
		return {
			'nombre': '', 'razon_social': '', 'tipo': Cliente.Tipo.PERSONA_NATURAL, 'nit': '', 'ci': '',
			'ci_complemento': '', 'ci_expedido': '', 'fecha_nacimiento': '', 'cambio_contador': False,
			'actividad': Cliente.Actividad.OTRA, 'telefono': '', 'whatsapp': '',
			'correo': '', 'direccion': '', 'estado': Cliente.Estado.ACTIVO,
			'fecha_inicio': '', 'tiene_representante_legal': False,
			'representante_legal_nombre': '', 'representante_legal_carnet': '', 'representante_legal_complemento': '',
			'representante_legal_expedido': '', 'representante_legal_celular': '', 'representante_legal_fecha_nacimiento': '',
			'observaciones': '',
		}
	return {
		'nombre': cliente.nombre,
		'razon_social': cliente.razon_social,
		'tipo': cliente.tipo,
		'nit': cliente.nit or '',
		'ci': cliente.ci,
		'ci_complemento': cliente.ci_complemento,
		'ci_expedido': cliente.ci_expedido,
		'fecha_nacimiento': cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else '',
		'cambio_contador': cliente.cambio_contador,
		'actividad': cliente.actividad,
		'telefono': cliente.telefono,
		'whatsapp': cliente.whatsapp,
		'correo': cliente.correo,
		'direccion': cliente.direccion,
		'estado': cliente.estado,
		'fecha_inicio': cliente.fecha_inicio.isoformat() if cliente.fecha_inicio else '',
		'tiene_representante_legal': cliente.tiene_representante_legal,
		'representante_legal_nombre': cliente.representante_legal_nombre,
		'representante_legal_carnet': cliente.representante_legal_carnet,
		'representante_legal_complemento': cliente.representante_legal_complemento,
		'representante_legal_expedido': cliente.representante_legal_expedido,
		'representante_legal_celular': cliente.representante_legal_celular,
		'representante_legal_fecha_nacimiento': cliente.representante_legal_fecha_nacimiento.isoformat() if cliente.representante_legal_fecha_nacimiento else '',
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
	for campo, limite in (
		('nombre', 180), ('razon_social', 180), ('ci', 20), ('ci_complemento', 10), ('ci_expedido', 20),
		('representante_legal_nombre', 180), ('representante_legal_carnet', 20),
		('representante_legal_complemento', 10), ('representante_legal_expedido', 20),
		('representante_legal_celular', 30), ('telefono', 30), ('whatsapp', 30),
		('correo', 254), ('direccion', 240),
	):
		if len(datos[campo]) > limite:
			errores[campo] = f'Este campo no puede superar {limite} caracteres.'
	if datos['tiene_representante_legal']:
		if not datos['representante_legal_nombre']:
			errores['representante_legal_nombre'] = 'El nombre del representante legal es obligatorio.'
		if not datos['representante_legal_carnet']:
			errores['representante_legal_carnet'] = 'El número de carnet del representante legal es obligatorio.'
	if datos['fecha_nacimiento'] and parse_date(datos['fecha_nacimiento']) is None:
		errores['fecha_nacimiento'] = 'Ingresa una fecha de nacimiento válida.'
	if datos['representante_legal_fecha_nacimiento'] and parse_date(datos['representante_legal_fecha_nacimiento']) is None:
		errores['representante_legal_fecha_nacimiento'] = 'Ingresa una fecha válida para el representante legal.'
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
		cliente.nombre = datos['nombre']
		cliente.razon_social = datos['razon_social']
		cliente.tipo = datos['tipo']
		cliente.nit = datos['nit'] or None
		cliente.ci = datos['ci']
		cliente.ci_complemento = datos['ci_complemento']
		cliente.ci_expedido = datos['ci_expedido']
		cliente.fecha_nacimiento = parse_date(datos['fecha_nacimiento']) if datos['fecha_nacimiento'] else None
		cliente.cambio_contador = bool(datos['cambio_contador'])
		cliente.actividad = datos['actividad']
		cliente.telefono = datos['telefono']
		cliente.whatsapp = datos['whatsapp']
		cliente.correo = datos['correo']
		cliente.direccion = datos['direccion']
		cliente.estado = datos['estado']
		cliente.fecha_inicio = parse_date(datos['fecha_inicio']) if datos['fecha_inicio'] else None
		cliente.tiene_representante_legal = bool(datos['tiene_representante_legal'])
		cliente.representante_legal_nombre = datos['representante_legal_nombre']
		cliente.representante_legal_carnet = datos['representante_legal_carnet']
		cliente.representante_legal_complemento = datos['representante_legal_complemento']
		cliente.representante_legal_expedido = datos['representante_legal_expedido']
		cliente.representante_legal_celular = datos['representante_legal_celular']
		cliente.representante_legal_fecha_nacimiento = parse_date(datos['representante_legal_fecha_nacimiento']) if datos['representante_legal_fecha_nacimiento'] else None
		cliente.observaciones = datos['observaciones']
		cliente.save()

		if es_nuevo:
			registrar_historial(
				cliente=cliente,
				usuario=request.user,
				tipo_accion=EntradaHistorial.TipoAccion.CREACION,
				seccion=EntradaHistorial.Seccion.CLIENTES,
				titulo='Cliente creado',
				descripcion=f'Registro inicial como {cliente.get_tipo_display()} ({cliente.get_actividad_display()}).',
			)
		else:
			registrar_historial(
				cliente=cliente,
				usuario=request.user,
				tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
				seccion=EntradaHistorial.Seccion.CLIENTES,
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
	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.OTRO,
		seccion=EntradaHistorial.Seccion.CLIENTES,
		referencia=nombre,
		titulo=f'Cliente eliminado: {nombre}',
		descripcion='La ficha del cliente fue eliminada.',
	)
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

	# Tarifa y Cobros de honorarios
	from apps.honorarios.models import CobroHonorario, DetalleCobroHonorario, PagoHonorario, TarifaCliente
	tarifa, _ = TarifaCliente.objects.get_or_create(cliente=cliente)
	cobros_honorarios = cliente.cobros_honorarios.prefetch_related('pagos').order_by('-anio', '-periodo_numero', '-creado_en')
	total_cobros_pendientes = sum((c.saldo_pendiente for c in cobros_honorarios if c.estado in (CobroHonorario.Estado.PENDIENTE, CobroHonorario.Estado.PARCIAL)), Decimal('0.00'))

	puede_gestionar = puede_gestionar_clientes(request.user)

	return render(request, 'clientes/detalle.html', {
		'cliente': cliente,
		'tarifa': tarifa,
		'cobros_honorarios': cobros_honorarios[:15],
		'total_cobros_pendientes': total_cobros_pendientes,
		'metodos_pago': PagoHonorario.MetodoPago.choices,
		'periodos_tipo': CobroHonorario.Periodicidad.choices,
		'tipos_ingreso': CobroHonorario.TipoIngreso.choices,
		'servicios_cobro': DetalleCobroHonorario.TipoServicio.choices,
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

