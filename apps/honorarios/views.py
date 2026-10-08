from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import CobroHonorario, PagoHonorario, TarifaCliente
from .services import MESES_NOMBRES, generar_honorarios_mensuales


def _volver(request, default_url='honorarios:index', cliente_id=None):
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
	puede_gestionar = puede_gestionar_clientes(request.user)
	hoy = timezone.localdate()

	busqueda = request.GET.get('q', '').strip()
	estado_filtro = request.GET.get('estado', '').strip()
	cliente_filtro = request.GET.get('cliente', '').strip()
	anio_filtro = request.GET.get('anio', str(hoy.year)).strip()

	cobros = (
		CobroHonorario.objects.select_related('cliente', 'generado_por')
		.prefetch_related('pagos')
		.all()
	)

	if busqueda:
		cobros = cobros.filter(
			Q(cliente__nombre__icontains=busqueda)
			| Q(cliente__nit__icontains=busqueda)
			| Q(concepto__icontains=busqueda)
			| Q(observaciones__icontains=busqueda)
		)
	if estado_filtro in {valor for valor, _ in CobroHonorario.Estado.choices}:
		cobros = cobros.filter(estado=estado_filtro)
	if cliente_filtro.isdigit():
		cobros = cobros.filter(cliente_id=int(cliente_filtro))
	if anio_filtro.isdigit():
		cobros = cobros.filter(anio=int(anio_filtro))

	# Totales para KPI resumen
	total_facturado = sum((c.monto_total for c in cobros), Decimal('0.00'))
	total_cobrado = sum((c.monto_pagado for c in cobros), Decimal('0.00'))
	total_pendiente = sum((c.saldo_pendiente for c in cobros), Decimal('0.00'))

	paginador = Paginator(cobros, 25)
	query_params = request.GET.copy()
	query_params.pop('page', None)
	page_obj = paginador.get_page(request.GET.get('page'))

	clientes_activos = Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre')

	meses_opciones = [(i + 1, nombre) for i, nombre in enumerate(MESES_NOMBRES)]

	return render(request, 'honorarios/honorarios.html', {
		'cobros': page_obj.object_list,
		'page_obj': page_obj,
		'total_cobros': paginador.count,
		'total_facturado': total_facturado,
		'total_cobrado': total_cobrado,
		'total_pendiente': total_pendiente,
		'query_string': query_params.urlencode(),
		'busqueda': busqueda,
		'estado_filtro': estado_filtro,
		'cliente_filtro': cliente_filtro,
		'anio_filtro': anio_filtro,
		'estados': CobroHonorario.Estado.choices,
		'clientes': clientes_activos,
		'meses_opciones': meses_opciones,
		'puede_gestionar': puede_gestionar,
		'hoy': hoy,
		'volver': request.get_full_path(),
	})


@solo_gestores_clientes
@require_POST
def guardar_tarifa(request, cliente_id):
	cliente = get_object_or_404(Cliente, pk=cliente_id)
	tarifa, _ = TarifaCliente.objects.get_or_create(cliente=cliente)

	try:
		tarifa.monto_mensual = Decimal(request.POST.get('monto_mensual', '0') or '0')
		tarifa.monto_trimestral = Decimal(request.POST.get('monto_trimestral', '0') or '0')
		tarifa.monto_anual = Decimal(request.POST.get('monto_anual', '0') or '0')
		tarifa.extra_bancarizacion = Decimal(request.POST.get('extra_bancarizacion', '0') or '0')
		tarifa.extra_gestora = Decimal(request.POST.get('extra_gestora', '0') or '0')
		tarifa.extra_ministerio = Decimal(request.POST.get('extra_ministerio', '0') or '0')
		tarifa.extra_caja = Decimal(request.POST.get('extra_caja', '0') or '0')
		tarifa.extra_otros = Decimal(request.POST.get('extra_otros', '0') or '0')
		tarifa.observaciones = request.POST.get('observaciones', '').strip()
		tarifa.save()

		registrar_historial(
			cliente=cliente,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.PAGO,
			titulo='Tarifa de honorarios actualizada',
			descripcion=f'Mensual: Bs {tarifa.monto_mensual} · Total recurrente sugerido: Bs {tarifa.total_mensual_sugerido}',
		)
		messages.success(request, f'Tarifa de honorarios de {cliente.nombre} guardada exitosamente.')
	except Exception as e:
		messages.error(request, f'Error al guardar la tarifa: {e}')

	return _volver(request, cliente_id=cliente.pk)


@solo_gestores_clientes
@require_POST
def generar_mensual(request):
	try:
		anio = int(request.POST.get('anio', timezone.localdate().year))
		mes = int(request.POST.get('mes', timezone.localdate().month))
		cliente_id = request.POST.get('cliente_id')
		cliente_id = int(cliente_id) if cliente_id and cliente_id.isdigit() else None
		monto_defecto = Decimal(request.POST.get('monto_defecto', '0') or '0')
	except (TypeError, ValueError):
		messages.error(request, 'Mes o año no válidos.')
		return _volver(request)

	resultado = generar_honorarios_mensuales(
		anio, mes,
		usuario=request.user,
		cliente_id=cliente_id,
		incluir_cero=True,
		monto_sugerido_defecto=monto_defecto,
	)
	msg = f"Se generaron {resultado['creados']} cuentas por cobrar para {MESES_NOMBRES[mes - 1]} {anio}. ({resultado['existentes']} ya existían)."
	messages.success(request, msg)
	return _volver(request)



@solo_gestores_clientes
@require_POST
def registrar_pago(request):
	cobro_id = request.POST.get('cobro_id')
	cobro = get_object_or_404(CobroHonorario, pk=cobro_id)

	try:
		monto = Decimal(request.POST.get('monto', '0') or '0')
		if monto <= Decimal('0.00'):
			messages.error(request, 'El monto del pago debe ser mayor a 0.')
			return _volver(request, cliente_id=cobro.cliente.pk)

		fecha_pago = parse_date(request.POST.get('fecha_pago', '')) or timezone.localdate()
		numero_recibo = request.POST.get('numero_recibo', '').strip()
		metodo_pago = request.POST.get('metodo_pago', PagoHonorario.MetodoPago.EFECTIVO)
		comprobante = request.FILES.get('comprobante')
		observaciones = request.POST.get('observaciones', '').strip()

		with transaction.atomic():
			cobro = CobroHonorario.objects.select_for_update().select_related('cliente').get(pk=cobro.pk)
			if cobro.estado == CobroHonorario.Estado.CANCELADO:
				messages.error(request, 'No se pueden registrar pagos en una cuenta anulada.')
				return _volver(request, cliente_id=cobro.cliente.pk)
			if monto > cobro.saldo_pendiente:
				messages.error(request, f'El abono no puede superar el saldo pendiente de Bs {cobro.saldo_pendiente}.')
				return _volver(request, cliente_id=cobro.cliente.pk)
			pago = PagoHonorario.objects.create(
				cobro=cobro,
				monto=monto,
				fecha_pago=fecha_pago,
				numero_recibo=numero_recibo,
				metodo_pago=metodo_pago,
				comprobante=comprobante,
				observaciones=observaciones,
				registrado_por=request.user,
			)

			registrar_historial(
				cliente=cobro.cliente,
				usuario=request.user,
				tipo_accion=EntradaHistorial.TipoAccion.PAGO,
				titulo=f'Pago registrado: Bs {monto}',
				descripcion=f'Recibo: {numero_recibo or "S/N"} · Concepto: {cobro.concepto} · Método: {pago.get_metodo_pago_display()}',
			)

		messages.success(request, f'Pago de Bs {monto} registrado exitosamente para {cobro.cliente.nombre}.')
	except Exception as e:
		messages.error(request, f'Error al registrar el pago: {e}')

	return _volver(request, cliente_id=cobro.cliente.pk)


@solo_gestores_clientes
@require_POST
def crear_cobro_manual(request):
	cliente_id = request.POST.get('cliente_id')
	cliente = get_object_or_404(Cliente, pk=cliente_id)

	try:
		concepto = request.POST.get('concepto', '').strip()
		monto_total = Decimal(request.POST.get('monto_total', '0') or '0')
		fecha_vencimiento = parse_date(request.POST.get('fecha_vencimiento', ''))
		periodo_tipo = request.POST.get('periodo_tipo', CobroHonorario.Periodicidad.EXTRA)
		observaciones = request.POST.get('observaciones', '').strip()

		if not concepto or monto_total <= Decimal('0.00'):
			messages.error(request, 'El concepto y un monto válido son obligatorios.')
			return _volver(request, cliente_id=cliente.pk)

		hoy = timezone.localdate()
		cobro = CobroHonorario.objects.create(
			cliente=cliente,
			periodo_tipo=periodo_tipo,
			anio=hoy.year,
			periodo_numero=hoy.month,
			concepto=concepto,
			monto_base=monto_total,
			monto_extras=Decimal('0.00'),
			monto_total=monto_total,
			fecha_vencimiento=fecha_vencimiento or hoy,
			observaciones=observaciones,
			generado_por=request.user,
		)

		registrar_historial(
			cliente=cliente,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.PAGO,
			titulo=f'Cobro extraordinario generado: Bs {monto_total}',
			descripcion=f'Concepto: {concepto}',
		)

		messages.success(request, f'Cobro generado correctamente para {cliente.nombre}.')
	except Exception as e:
		messages.error(request, f'Error al generar cobro: {e}')

	return _volver(request, cliente_id=cliente.pk)
