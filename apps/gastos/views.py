from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes

from .models import RecuperacionGasto, RegistroFinanciero


MESES_ES = (
	'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
	'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)

CATEGORIAS_POR_TIPO = {
	RegistroFinanciero.Tipo.GASTO: {
		RegistroFinanciero.Categoria.ALQUILER,
		RegistroFinanciero.Categoria.SUELDO_AUXILIAR,
		RegistroFinanciero.Categoria.SUELDO_CAPTADORES,
		RegistroFinanciero.Categoria.SUELDO_EEFF,
		RegistroFinanciero.Categoria.FIRMAS_AUDITORIA,
		RegistroFinanciero.Categoria.AGUINALDO,
		RegistroFinanciero.Categoria.INTERNET,
		RegistroFinanciero.Categoria.LUZ,
		RegistroFinanciero.Categoria.REFRIGERIO,
		RegistroFinanciero.Categoria.PASAJES,
		RegistroFinanciero.Categoria.SUMINISTROS,
		RegistroFinanciero.Categoria.OTRO,
	},
	RegistroFinanciero.Tipo.INVERSION: {
		RegistroFinanciero.Categoria.SILLAS,
		RegistroFinanciero.Categoria.MONITOR,
		RegistroFinanciero.Categoria.ESCRITORIO,
		RegistroFinanciero.Categoria.COMPUTADORA,
		RegistroFinanciero.Categoria.IMPRESORA,
		RegistroFinanciero.Categoria.MUEBLES,
		RegistroFinanciero.Categoria.OTRO,
	},
	RegistroFinanciero.Tipo.EGRESO: {
		RegistroFinanciero.Categoria.IMPUESTOS,
		RegistroFinanciero.Categoria.FACTURAS,
		RegistroFinanciero.Categoria.TALONARIOS,
		RegistroFinanciero.Categoria.PASANKU,
		RegistroFinanciero.Categoria.OTRO,
	},
}


def _datos_post(request):
	return {
		'concepto': request.POST.get('concepto', '').strip(),
		'tipo': request.POST.get('tipo', '').strip(),
		'categoria': request.POST.get('categoria', '').strip(),
		'periodicidad': request.POST.get('periodicidad', '').strip(),
		'monto': request.POST.get('monto', '').strip(),
		'fecha': request.POST.get('fecha', '').strip(),
		'proveedor': request.POST.get('proveedor', '').strip(),
		'responsable': request.POST.get('responsable', '').strip(),
		'comprobante': request.POST.get('comprobante', '').strip(),
		'estado_pago': request.POST.get('estado_pago', '').strip(),
		'recuperable': request.POST.get('recuperable') in {'1', 'on', 'true'},
		'estado_recuperacion': request.POST.get('estado_recuperacion', '').strip(),
		'cliente': request.POST.get('cliente', '').strip(),
		'vida_util_meses': request.POST.get('vida_util_meses', '').strip(),
		'estado_activo': request.POST.get('estado_activo', '').strip(),
		'ubicacion': request.POST.get('ubicacion', '').strip(),
		'observaciones': request.POST.get('observaciones', '').strip(),
	}


def _validar_y_guardar(request, registro=None):
	datos = _datos_post(request)
	errores = {}
	valores = {value for value, _ in RegistroFinanciero.Tipo.choices}
	categorias = {value for value, _ in RegistroFinanciero.Categoria.choices}
	periodicidades = {value for value, _ in RegistroFinanciero.Periodicidad.choices}
	if not datos['concepto'] or len(datos['concepto']) > 180:
		errores['concepto'] = 'Ingresa un concepto de hasta 180 caracteres.'
	if datos['tipo'] not in valores:
		errores['tipo'] = 'Selecciona un tipo de registro válido.'
	if datos['categoria'] not in categorias:
		errores['categoria'] = 'Selecciona una categoría válida.'
	elif datos['tipo'] in CATEGORIAS_POR_TIPO and datos['categoria'] not in CATEGORIAS_POR_TIPO[datos['tipo']]:
		errores['categoria'] = 'La categoría no corresponde al tipo de movimiento seleccionado.'
	if datos['periodicidad'] not in periodicidades:
		errores['periodicidad'] = 'Selecciona una periodicidad válida.'
	try:
		monto = Decimal(datos['monto'])
		if not monto.is_finite() or monto <= 0 or monto.as_tuple().exponent < -2 or monto >= Decimal('10000000000'):
			raise InvalidOperation
	except (InvalidOperation, TypeError, ValueError):
		monto = None
		errores['monto'] = 'Ingresa un monto positivo válido con hasta dos decimales.'
	fecha = parse_date(datos['fecha'])
	if fecha is None:
		errores['fecha'] = 'Ingresa una fecha válida.'
	if datos['estado_pago'] not in {value for value, _ in RegistroFinanciero.EstadoPago.choices}:
		errores['estado_pago'] = 'Selecciona un estado de pago válido.'
	if datos['tipo'] == RegistroFinanciero.Tipo.INVERSION and datos['estado_activo'] not in {value for value, _ in RegistroFinanciero.EstadoActivo.choices}:
		errores['estado_activo'] = 'Selecciona un estado de activo válido.'
	if any(len(datos[campo]) > limite for campo, limite in (
		('proveedor', 180), ('responsable', 180), ('comprobante', 120), ('ubicacion', 180),
	)):
		errores['general'] = 'Proveedor, responsable, comprobante o ubicación excede su longitud permitida.'
	vida_util = None
	if datos['vida_util_meses']:
		try:
			vida_util = int(datos['vida_util_meses'])
			if not 1 <= vida_util <= 1200:
				raise ValueError
		except (TypeError, ValueError):
			vida_util = None
			errores['vida_util_meses'] = 'La vida útil debe estar entre 1 y 1200 meses.'
	cliente = None
	if datos['cliente']:
		if not datos['cliente'].isdigit():
			errores['cliente'] = 'Selecciona un cliente válido.'
		else:
			cliente = Cliente.objects.filter(pk=int(datos['cliente'])).first()
			if cliente is None:
				errores['cliente'] = 'El cliente seleccionado no existe.'
	if datos['recuperable'] and cliente is None:
		errores['cliente'] = 'Selecciona el cliente al que se cobrará este egreso recuperable.'
	if registro and registro.recuperaciones.exists():
		if cliente and cliente.pk != registro.cliente_id:
			errores['cliente'] = 'No se puede cambiar el cliente después de registrar una recuperación.'
		if monto is not None and monto < registro.monto_recuperado:
			errores['monto'] = 'El monto no puede ser menor a lo que ya se recuperó.'
	if datos['tipo'] == RegistroFinanciero.Tipo.INVERSION and not vida_util:
		errores['vida_util_meses'] = 'Indica la vida útil de la inversión en meses.'
	if datos['tipo'] != RegistroFinanciero.Tipo.INVERSION and vida_util:
		errores['vida_util_meses'] = 'La vida útil solo corresponde a una inversión.'
	if errores:
		return None, datos, errores
	if registro is None:
		registro = RegistroFinanciero(creado_por=request.user)
	registro.concepto = datos['concepto']
	registro.tipo = datos['tipo']
	registro.categoria = datos['categoria']
	registro.periodicidad = datos['periodicidad']
	registro.monto = monto
	registro.fecha = fecha
	registro.proveedor = datos['proveedor']
	registro.responsable = datos['responsable']
	registro.comprobante = datos['comprobante']
	registro.estado_pago = datos['estado_pago']
	registro.recuperable = datos['recuperable']
	if datos['recuperable']:
		monto_recuperado = registro.monto_recuperado if registro.pk else Decimal('0.00')
		recuperacion_historica = (
			registro.pk
			and registro.estado_recuperacion == RegistroFinanciero.EstadoRecuperacion.RECUPERADO
			and not registro.recuperaciones.exists()
		)
		registro.estado_recuperacion = (
			RegistroFinanciero.EstadoRecuperacion.RECUPERADO
			if recuperacion_historica or monto_recuperado >= monto
			else RegistroFinanciero.EstadoRecuperacion.PENDIENTE
		)
	else:
		registro.estado_recuperacion = RegistroFinanciero.EstadoRecuperacion.PENDIENTE
	registro.cliente = cliente if datos['recuperable'] else None
	registro.vida_util_meses = vida_util if datos['tipo'] == RegistroFinanciero.Tipo.INVERSION else None
	registro.estado_activo = datos['estado_activo'] if datos['tipo'] == RegistroFinanciero.Tipo.INVERSION else RegistroFinanciero.EstadoActivo.EN_USO
	registro.ubicacion = datos['ubicacion'] if datos['tipo'] == RegistroFinanciero.Tipo.INVERSION else ''
	registro.observaciones = datos['observaciones']
	try:
		registro.full_clean()
	except ValidationError as error:
		return None, datos, {'general': ' '.join(error.messages)}
	registro.save()
	return registro, datos, {}


def _contexto_index(request, form_data=None, errores=None, modal_activo='', registro_edicion=None):
	hoy = timezone.localdate()
	registros = RegistroFinanciero.objects.select_related('cliente', 'creado_por').prefetch_related('recuperaciones').all()
	busqueda = request.GET.get('q', '').strip()
	tipo_filtro = request.GET.get('tipo', '').strip()
	categoria_filtro = request.GET.get('categoria', '').strip()
	pago_filtro = request.GET.get('estado_pago', '').strip()
	recuperacion_filtro = request.GET.get('recuperacion', '').strip()
	if busqueda:
		registros = registros.filter(
			Q(concepto__icontains=busqueda)
			| Q(categoria__icontains=busqueda)
			| Q(proveedor__icontains=busqueda)
			| Q(comprobante__icontains=busqueda)
			| Q(cliente__nombre__icontains=busqueda)
			| Q(cliente__razon_social__icontains=busqueda)
		)
	if tipo_filtro in {value for value, _ in RegistroFinanciero.Tipo.choices}:
		registros = registros.filter(tipo=tipo_filtro)
	if categoria_filtro in {value for value, _ in RegistroFinanciero.Categoria.choices}:
		registros = registros.filter(categoria=categoria_filtro)
	if pago_filtro in {value for value, _ in RegistroFinanciero.EstadoPago.choices}:
		registros = registros.filter(estado_pago=pago_filtro)
	if recuperacion_filtro in {value for value, _ in RegistroFinanciero.EstadoRecuperacion.choices}:
		registros = registros.filter(recuperable=True, estado_recuperacion=recuperacion_filtro)

	page_obj = Paginator(registros, 20).get_page(request.GET.get('page'))
	mes_actual = RegistroFinanciero.objects.filter(tipo=RegistroFinanciero.Tipo.GASTO, fecha__year=hoy.year, fecha__month=hoy.month)
	gastos_anuales = RegistroFinanciero.objects.filter(
		tipo=RegistroFinanciero.Tipo.GASTO,
		fecha__year=hoy.year,
		periodicidad__in=(RegistroFinanciero.Periodicidad.ANUAL, RegistroFinanciero.Periodicidad.EXTRAORDINARIO),
	)
	inversiones = RegistroFinanciero.objects.filter(
		tipo=RegistroFinanciero.Tipo.INVERSION,
		estado_activo=RegistroFinanciero.EstadoActivo.EN_USO,
	)
	eg_resumen = RegistroFinanciero.objects.filter(tipo=RegistroFinanciero.Tipo.EGRESO)
	por_cobrar = RegistroFinanciero.objects.filter(
		recuperable=True,
		estado_recuperacion=RegistroFinanciero.EstadoRecuperacion.PENDIENTE,
	)
	pendientes_pago = RegistroFinanciero.objects.filter(estado_pago=RegistroFinanciero.EstadoPago.PENDIENTE)
	montos_por_mes = {
		item['fecha__month']: item['total']
		for item in RegistroFinanciero.objects.filter(
			tipo=RegistroFinanciero.Tipo.GASTO,
			fecha__year=hoy.year,
		).values('fecha__month').annotate(total=Sum('monto'))
	}
	maximo_mes = max(montos_por_mes.values(), default=Decimal('0.00'))
	gastos_mensuales = [
		{
			'nombre': nombre,
			'monto': montos_por_mes.get(numero, Decimal('0.00')),
			'porcentaje': int(montos_por_mes.get(numero, Decimal('0.00')) / maximo_mes * 100) if maximo_mes else 0,
		}
		for numero, nombre in enumerate(MESES_ES, start=1)
	]
	categorias_query = RegistroFinanciero.objects.filter(
		tipo=RegistroFinanciero.Tipo.GASTO,
		fecha__year=hoy.year,
	).values('categoria').annotate(total=Sum('monto')).order_by('-total')
	categoria_labels = dict(RegistroFinanciero.Categoria.choices)
	maximo_categoria = max((item['total'] for item in categorias_query), default=Decimal('0.00'))
	gastos_por_categoria = [
		{
			'nombre': categoria_labels.get(item['categoria'], item['categoria']),
			'monto': item['total'],
			'porcentaje': int(item['total'] / maximo_categoria * 100) if maximo_categoria else 0,
		}
		for item in categorias_query
	]
	total_recuperable = RegistroFinanciero.objects.filter(recuperable=True).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
	total_no_recuperable = RegistroFinanciero.objects.filter(recuperable=False).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
	total_depreciacion = sum((activo.depreciacion_acumulada for activo in inversiones), Decimal('0.00'))
	query_params = request.GET.copy()
	query_params.pop('page', None)
	return {
		'registros': page_obj.object_list,
		'page_obj': page_obj,
		'total_registros': registros.count(),
		'query_string': query_params.urlencode(),
		'busqueda': busqueda,
		'tipo_filtro': tipo_filtro,
		'categoria_filtro': categoria_filtro,
		'pago_filtro': pago_filtro,
		'recuperacion_filtro': recuperacion_filtro,
		'tipos': RegistroFinanciero.Tipo.choices,
		'categorias': RegistroFinanciero.Categoria.choices,
		'categorias_por_tipo': {
			tipo: tuple(choice for choice in RegistroFinanciero.Categoria.choices if choice[0] in categorias)
			for tipo, categorias in CATEGORIAS_POR_TIPO.items()
		},
		'estados_pago': RegistroFinanciero.EstadoPago.choices,
		'estados_recuperacion': RegistroFinanciero.EstadoRecuperacion.choices,
		'periodicidades': RegistroFinanciero.Periodicidad.choices,
		'estados_activo': RegistroFinanciero.EstadoActivo.choices,
		'clientes': Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre'),
		'puede_gestionar': puede_gestionar_clientes(request.user),
		'total_gastos_mes': mes_actual.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'),
		'total_gastos_anuales': gastos_anuales.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'),
		'total_inversiones': inversiones.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'),
		'total_egresos': eg_resumen.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'),
		'total_por_cobrar': sum((registro.saldo_por_recuperar for registro in por_cobrar.prefetch_related('recuperaciones')), Decimal('0.00')),
		'total_pendiente_pago': pendientes_pago.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'),
		'total_depreciacion': total_depreciacion,
		'total_recuperable': total_recuperable,
		'total_no_recuperable': total_no_recuperable,
		'gastos_mensuales': gastos_mensuales,
		'gastos_por_categoria': gastos_por_categoria,
		'form_data': form_data or {},
		'errores': errores or {},
		'modal_activo': modal_activo,
		'registro_edicion': registro_edicion,
		'hoy': hoy,
	}


@login_required
def index(request):
	return render(request, 'gastos/gastos.html', _contexto_index(request))


@solo_gestores_clientes
@require_POST
def crear(request):
	registro, datos, errores = _validar_y_guardar(request)
	if registro:
		messages.success(request, f'Se registró «{registro.concepto}» por Bs {registro.monto}.')
		return redirect('gastos:index')
	contexto = _contexto_index(request, datos, errores, 'modal-registro')
	return render(request, 'gastos/gastos.html', contexto, status=400)


@solo_gestores_clientes
@require_POST
def editar(request, registro_id):
	registro = get_object_or_404(RegistroFinanciero, pk=registro_id)
	registro_guardado, datos, errores = _validar_y_guardar(request, registro)
	if registro_guardado:
		messages.success(request, f'Se actualizaron los datos de «{registro_guardado.concepto}».')
		return redirect('gastos:index')
	contexto = _contexto_index(request, datos, errores, 'modal-editar', registro)
	return render(request, 'gastos/gastos.html', contexto, status=400)


@solo_gestores_clientes
@require_POST
def registrar_recuperacion(request, registro_id):
	try:
		monto = Decimal(request.POST.get('monto', '0') or '0')
		if not monto.is_finite() or monto <= 0 or monto.as_tuple().exponent < -2:
			raise InvalidOperation
	except (InvalidOperation, TypeError, ValueError):
		messages.error(request, 'Ingresa un monto recuperado válido, con hasta dos decimales.')
		return redirect('gastos:index')
	fecha = parse_date(request.POST.get('fecha', ''))
	if fecha is None:
		messages.error(request, 'Ingresa una fecha válida para la recuperación.')
		return redirect('gastos:index')
	with transaction.atomic():
		registro = get_object_or_404(RegistroFinanciero.objects.select_for_update(), pk=registro_id)
		if not registro.recuperable:
			messages.error(request, 'Este movimiento no está marcado como recuperable.')
			return redirect('gastos:index')
		saldo = registro.saldo_por_recuperar
		if monto > saldo:
			messages.error(request, f'El monto supera el saldo pendiente de Bs {saldo:.2f}.')
			return redirect('gastos:index')
		RecuperacionGasto.objects.create(
			registro=registro,
			monto=monto,
			fecha=fecha,
			comprobante=request.POST.get('comprobante', '').strip()[:120],
			observaciones=request.POST.get('observaciones', '').strip(),
			registrado_por=request.user,
		)
		registro.estado_recuperacion = (
			RegistroFinanciero.EstadoRecuperacion.RECUPERADO
			if registro.monto_recuperado >= registro.monto
			else RegistroFinanciero.EstadoRecuperacion.PENDIENTE
		)
		registro.save(update_fields=('estado_recuperacion', 'actualizado_en'))
	messages.success(request, f'Se registró la recuperación de Bs {monto:.2f}.')
	return redirect('gastos:index')


@solo_gestores_clientes
@require_POST
def eliminar(request, registro_id):
	registro = get_object_or_404(RegistroFinanciero, pk=registro_id)
	concepto = registro.concepto
	registro.delete()
	messages.success(request, f'Se eliminó el registro «{concepto}».')
	return redirect('gastos:index')