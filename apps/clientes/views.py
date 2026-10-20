from decimal import Decimal
from datetime import datetime

from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
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

from .services import ErrorRecordatorioAgenda, sincronizar_recordatorio_vencimiento
from .models import Cliente
from .permissions import puede_gestionar_clientes, solo_gestores_clientes


ACTIVIDADES_POR_TIPO = {
	Cliente.Tipo.PERSONA_NATURAL: {
		Cliente.Actividad.PROFESIONAL,
		Cliente.Actividad.TECNICO,
		Cliente.Actividad.ALQUILER,
		Cliente.Actividad.DEPENDIENTE,
		Cliente.Actividad.CONSULTOR_EN_LINEA,
		Cliente.Actividad.OTRA,
	},
	Cliente.Tipo.UNIPERSONAL: {
		Cliente.Actividad.COMERCIAL,
		Cliente.Actividad.SERVICIOS,
		Cliente.Actividad.INDUSTRIAL,
		Cliente.Actividad.CONSTRUCTORA,
		Cliente.Actividad.AGRICOLA,
		Cliente.Actividad.AGROPECUARIA,
		Cliente.Actividad.GANADERA,
		Cliente.Actividad.AGROINDUSTRIAL,
		Cliente.Actividad.MINERA,
		Cliente.Actividad.OTRA,
	},
	Cliente.Tipo.JURIDICA: {
		Cliente.Actividad.COMERCIAL,
		Cliente.Actividad.SERVICIOS,
		Cliente.Actividad.INDUSTRIAL,
		Cliente.Actividad.CONSTRUCTORA,
		Cliente.Actividad.AGRICOLA,
		Cliente.Actividad.AGROPECUARIA,
		Cliente.Actividad.GANADERA,
		Cliente.Actividad.AGROINDUSTRIAL,
		Cliente.Actividad.MINERA,
		Cliente.Actividad.OTRA,
	},
	Cliente.Tipo.SIN_FINES_LUCRO: {
		Cliente.Actividad.ASOCIACION,
		Cliente.Actividad.ONG,
		Cliente.Actividad.OTRA,
	},
}


def _datos_formulario(request, cliente=None):
	if request.method == 'POST':
		return {
			'nombre': request.POST.get('nombre', '').strip(),
			'razon_social': request.POST.get(
				'razon_social', cliente.razon_social if cliente else '',
			).strip(),
			'tipo': request.POST.get('tipo', Cliente.Tipo.PERSONA_NATURAL),
			'forma_juridica': request.POST.get('forma_juridica', '').strip(),
			'forma_juridica_detalle': request.POST.get('forma_juridica_detalle', '').strip(),
			'actividad_detalle': request.POST.get('actividad_detalle', '').strip(),
			'tiene_seprec': request.POST.get('tiene_seprec') in {'1', 'on', 'true', 'True', 'si'},
			'tiene_roe': request.POST.get('tiene_roe') in {'1', 'on', 'true', 'True', 'si'},
			'nit': request.POST.get('nit', '').strip(),
			'ci': request.POST.get('ci', '').strip(),
			'ci_complemento': request.POST.get('ci_complemento', '').strip(),
			'ci_expedido': request.POST.get('ci_expedido', '').strip(),
			'fecha_nacimiento': request.POST.get('fecha_nacimiento', '').strip(),
			'cambio_contador': request.POST.get('cambio_contador') in {'1', 'on', 'true', 'True'},
			'fecha_cambio_contador': request.POST.get('fecha_cambio_contador', '').strip(),
			'actividad': request.POST.get('actividad', ''),
			'telefono': request.POST.get('telefono', '').strip(),
			'whatsapp': request.POST.get('whatsapp', '').strip(),
			'correo': cliente.correo if cliente else '',
			'direccion': request.POST.get('direccion', '').strip(),
			'estado': Cliente.Estado.ACTIVO if request.POST.get('estado') == 'activo' else Cliente.Estado.INACTIVO,
			'fecha_inicio': request.POST.get('fecha_inicio', '').strip(),
			'tipo_facturacion': request.POST.get('tipo_facturacion', '').strip(),
			'fecha_vencimiento_facturacion': request.POST.get('fecha_vencimiento_facturacion', '').strip(),
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
			'nombre': '', 'razon_social': '', 'tipo': Cliente.Tipo.PERSONA_NATURAL,
			'forma_juridica': '', 'forma_juridica_detalle': '', 'actividad_detalle': '',
			'tiene_seprec': False, 'tiene_roe': False, 'nit': '', 'ci': '',
			'ci_complemento': '', 'ci_expedido': '', 'fecha_nacimiento': '', 'cambio_contador': False,
			'fecha_cambio_contador': '',
			'actividad': '', 'telefono': '', 'whatsapp': '',
			'correo': '', 'direccion': '', 'estado': Cliente.Estado.ACTIVO,
			'fecha_inicio': '', 'tipo_facturacion': '', 'fecha_vencimiento_facturacion': '',
			'tiene_representante_legal': False,
			'representante_legal_nombre': '', 'representante_legal_carnet': '', 'representante_legal_complemento': '',
			'representante_legal_expedido': '', 'representante_legal_celular': '', 'representante_legal_fecha_nacimiento': '',
			'observaciones': '',
		}
	return {
		'nombre': cliente.nombre,
		'razon_social': cliente.razon_social,
		'tipo': cliente.tipo,
		'forma_juridica': cliente.forma_juridica,
		'forma_juridica_detalle': cliente.forma_juridica_detalle,
		'actividad_detalle': cliente.actividad_detalle,
		'tiene_seprec': cliente.tiene_seprec,
		'tiene_roe': cliente.tiene_roe,
		'nit': cliente.nit or '',
		'ci': cliente.ci,
		'ci_complemento': cliente.ci_complemento,
		'ci_expedido': cliente.ci_expedido,
		'fecha_nacimiento': cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else '',
		'cambio_contador': cliente.cambio_contador,
		'fecha_cambio_contador': cliente.fecha_cambio_contador,
		'actividad': cliente.actividad,
		'telefono': cliente.telefono,
		'whatsapp': cliente.whatsapp,
		'correo': cliente.correo,
		'direccion': cliente.direccion,
		'estado': cliente.estado,
		'fecha_inicio': cliente.fecha_inicio.isoformat() if cliente.fecha_inicio else '',
		'tipo_facturacion': cliente.tipo_facturacion,
		'fecha_vencimiento_facturacion': cliente.fecha_vencimiento_facturacion.isoformat() if cliente.fecha_vencimiento_facturacion else '',
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
		('forma_juridica_detalle', 100), ('actividad_detalle', 120),
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
	if datos['tipo'] not in {valor for valor, _ in Cliente.Tipo.choices}:
		errores['tipo'] = 'Selecciona un tipo de cliente válido.'
	elif datos['actividad'] not in ACTIVIDADES_POR_TIPO[datos['tipo']]:
		actividad_heredada_sin_cambios = (
			cliente is not None
			and cliente.tipo == datos['tipo']
			and cliente.actividad == datos['actividad']
		)
		if not actividad_heredada_sin_cambios:
			errores['actividad'] = 'Selecciona una actividad correspondiente al tipo de cliente.'
	if datos['actividad'] not in {valor for valor, _ in Cliente.Actividad.choices}:
		errores['actividad'] = 'Selecciona una actividad válida.'
	if datos['tipo'] == Cliente.Tipo.JURIDICA:
		if datos['forma_juridica'] not in {valor for valor, _ in Cliente.FormaJuridica.choices}:
			errores['forma_juridica'] = 'Selecciona la forma jurídica.'
		elif datos['forma_juridica'] == Cliente.FormaJuridica.OTRA and not datos['forma_juridica_detalle']:
			errores['forma_juridica_detalle'] = 'Especifica la forma jurídica.'
	if datos['tiene_seprec'] and not datos['razon_social']:
		errores['razon_social'] = 'Ingresa la razón social o nombre de la empresa.'
	if datos['estado'] not in {valor for valor, _ in Cliente.Estado.choices}:
		errores['estado'] = 'Selecciona un estado válido.'
	if datos['fecha_inicio'] and parse_date(datos['fecha_inicio']) is None:
		errores['fecha_inicio'] = 'Ingresa una fecha válida.'
	if datos['cambio_contador']:
		try:
			datetime.strptime(datos['fecha_cambio_contador'], '%Y-%m')
		except ValueError:
			errores['fecha_cambio_contador'] = 'Indica el mes y año del cambio de contador.'
	if datos['tipo_facturacion'] and datos['tipo_facturacion'] not in {
		valor for valor, _ in Cliente.TipoFacturacion.choices
	}:
		errores['tipo_facturacion'] = 'Selecciona un tipo de facturación válido.'
	if datos['fecha_vencimiento_facturacion']:
		if parse_date(datos['fecha_vencimiento_facturacion']) is None:
			errores['fecha_vencimiento_facturacion'] = 'Ingresa una fecha de vencimiento válida.'
		elif not datos['tipo_facturacion']:
			errores['tipo_facturacion'] = 'Selecciona el tipo de facturación para registrar el vencimiento.'
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
		cliente.forma_juridica = datos['forma_juridica'] if datos['tipo'] == Cliente.Tipo.JURIDICA else ''
		cliente.forma_juridica_detalle = (
			datos['forma_juridica_detalle']
			if datos['tipo'] == Cliente.Tipo.JURIDICA and datos['forma_juridica'] == Cliente.FormaJuridica.OTRA
			else ''
		)
		cliente.actividad_detalle = datos['actividad_detalle'] if datos['actividad'] == Cliente.Actividad.OTRA else ''
		cliente.tiene_seprec = bool(datos['tiene_seprec'])
		cliente.tiene_roe = bool(datos['tiene_roe'])
		cliente.nit = datos['nit'] or None
		persona_juridica = datos['tipo'] == Cliente.Tipo.JURIDICA
		cliente.ci = '' if persona_juridica else datos['ci']
		cliente.ci_complemento = '' if persona_juridica else datos['ci_complemento']
		cliente.ci_expedido = '' if persona_juridica else datos['ci_expedido']
		cliente.fecha_nacimiento = (
			parse_date(datos['fecha_nacimiento'])
			if datos['fecha_nacimiento'] and not persona_juridica
			else None
		)
		cliente.cambio_contador = bool(datos['cambio_contador'])
		cliente.fecha_cambio_contador = datos['fecha_cambio_contador'] if datos['cambio_contador'] else ''
		cliente.actividad = datos['actividad']
		cliente.telefono = datos['telefono']
		cliente.whatsapp = datos['whatsapp']
		cliente.correo = datos['correo']
		cliente.direccion = datos['direccion']
		cliente.estado = datos['estado']
		cliente.fecha_inicio = parse_date(datos['fecha_inicio']) if datos['fecha_inicio'] else None
		cliente.tipo_facturacion = datos['tipo_facturacion']
		cliente.fecha_vencimiento_facturacion = (
			parse_date(datos['fecha_vencimiento_facturacion'])
			if datos['fecha_vencimiento_facturacion']
			else None
		)
		cliente.tiene_representante_legal = bool(datos['tiene_representante_legal'])
		cliente.representante_legal_nombre = datos['representante_legal_nombre']
		cliente.representante_legal_carnet = datos['representante_legal_carnet']
		cliente.representante_legal_complemento = datos['representante_legal_complemento']
		cliente.representante_legal_expedido = datos['representante_legal_expedido']
		cliente.representante_legal_celular = datos['representante_legal_celular']
		cliente.representante_legal_fecha_nacimiento = parse_date(datos['representante_legal_fecha_nacimiento']) if datos['representante_legal_fecha_nacimiento'] else None
		cliente.observaciones = datos['observaciones']
		cliente.save()
		try:
			sincronizar_recordatorio_vencimiento(cliente, request.user)
		except ErrorRecordatorioAgenda as error:
			transaction.set_rollback(True)
			return None, datos, {'fecha_vencimiento_facturacion': str(error)}

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
		'formas_juridicas': Cliente.FormaJuridica.choices,
		'actividades': Cliente.Actividad.choices,
		'tipos_facturacion': Cliente.TipoFacturacion.choices,
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
		'formas_juridicas': Cliente.FormaJuridica.choices,
		'actividades': Cliente.Actividad.choices,
		'tipos_facturacion': Cliente.TipoFacturacion.choices,
		'estados': Cliente.Estado.choices,
	})

