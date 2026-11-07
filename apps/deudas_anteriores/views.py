from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes

from .models import AbonoDeudaAnterior, CobroAnterior


def _form_values(post_data, fields):
	return {field: post_data.get(field, '') for field in fields}


def _validate_date(value, label, errors):
	try:
		parsed_date = date.fromisoformat(value)
	except (TypeError, ValueError):
		errors['fecha_cobro'] = f'Ingresa una fecha válida para {label}.'
		return None
	if parsed_date > timezone.localdate():
		errors['fecha_cobro'] = f'La fecha de {label} no puede estar en el futuro.'
		return None
	return parsed_date


def _validate_amount(value, field, errors):
	try:
		amount = Decimal(value)
	except (InvalidOperation, TypeError, ValueError):
		errors[field] = 'Ingresa un monto válido.'
		return None
	if not amount.is_finite() or amount <= 0:
		errors[field] = 'El monto debe ser mayor a cero.'
		return None
	if amount.as_tuple().exponent < -2 or amount >= Decimal('100000000'):
		errors[field] = 'El monto debe tener hasta 8 dígitos enteros y 2 decimales.'
		return None
	return amount


def _validate_debt(values, errors, debt=None):
	client_id = values['cliente']
	client = Cliente.objects.filter(pk=client_id).first() if client_id.isdigit() else None
	if client is None:
		errors['cliente'] = 'Selecciona un cliente válido.'

	fecha_cobro = _validate_date(values['fecha_cobro'], 'cobro', errors)
	detalle = values['detalle'].strip()
	if not detalle:
		errors['detalle'] = 'Ingresa el detalle de la deuda.'
	elif len(detalle) > 200:
		errors['detalle'] = 'El detalle no puede superar 200 caracteres.'

	monto_total = _validate_amount(values['monto_total'], 'monto_total', errors)
	if monto_total is not None and debt is not None and monto_total < debt.monto_pagado:
		errors['monto_total'] = 'El total no puede ser menor a los abonos ya registrados.'

	if errors:
		return None
	return {
		'cliente': client,
		'fecha_cobro': fecha_cobro,
		'detalle': detalle,
		'monto_total': monto_total,
	}


def _validate_payment(values, debt, errors):
	fecha_cobro = _validate_date(values['fecha_cobro'], 'pago', errors)
	detalle = values['detalle'].strip()
	if not detalle:
		errors['detalle'] = 'Ingresa el detalle del pago.'
	elif len(detalle) > 200:
		errors['detalle'] = 'El detalle no puede superar 200 caracteres.'

	monto = _validate_amount(values['monto'], 'monto', errors)
	if monto is not None and monto > debt.saldo_pendiente:
		errors['monto'] = f'El abono no puede superar el saldo pendiente de Bs {debt.saldo_pendiente:.2f}.'

	numero_recibo = values['numero_recibo'].strip()
	if len(numero_recibo) > 60:
		errors['numero_recibo'] = 'El número de recibo no puede superar 60 caracteres.'

	tipo_pago = values['tipo_pago']
	if tipo_pago not in AbonoDeudaAnterior.TipoPago.values:
		errors['tipo_pago'] = 'Selecciona un tipo de pago válido.'

	if errors:
		return None
	return {
		'fecha_cobro': fecha_cobro,
		'detalle': detalle,
		'monto': monto,
		'numero_recibo': numero_recibo,
		'tipo_pago': tipo_pago,
	}


def _render_index(
	request,
	*,
	creation_values=None,
	creation_errors=None,
	edit_values=None,
	edit_errors=None,
	abono_values=None,
	abono_errors=None,
	open_modal=None,
	focus_deuda_id=None,
):
	busqueda = request.GET.get('q', '').strip()
	cliente_filtro = request.GET.get('cliente', '').strip()
	estado_filtro = request.GET.get('estado', '').strip()
	deudas = CobroAnterior.objects.select_related(
		'cliente', 'registrado_por',
	).prefetch_related('abonos__registrado_por')

	if focus_deuda_id is not None:
		deudas = deudas.filter(pk=focus_deuda_id)
	else:
		if busqueda:
			deudas = deudas.filter(
				Q(cliente__nombre__icontains=busqueda)
				| Q(cliente__nit__icontains=busqueda)
				| Q(detalle__icontains=busqueda)
			)
		if cliente_filtro.isdigit():
			deudas = deudas.filter(cliente_id=int(cliente_filtro))

	deudas_list = list(deudas)
	if estado_filtro in {'pendiente', 'parcial', 'pagado'} and focus_deuda_id is None:
		deudas_list = [deuda for deuda in deudas_list if deuda.estado == estado_filtro]

	pagina = Paginator(deudas_list, 30).get_page(request.GET.get('page'))
	deuda_items = []
	for deuda in pagina.object_list:
		is_editing = open_modal == f'editar-{deuda.pk}'
		is_amortizing = open_modal == f'amortizar-{deuda.pk}'
		deuda_items.append({
			'deuda': deuda,
			'edit_values': edit_values if is_editing else {
				'cliente': str(deuda.cliente_id),
				'fecha_cobro': deuda.fecha_cobro.isoformat(),
				'detalle': deuda.detalle,
				'monto_total': str(deuda.monto_total),
			},
			'edit_errors': edit_errors if is_editing else {},
			'abono_values': abono_values if is_amortizing else {
				'fecha_cobro': timezone.localdate().isoformat(),
				'detalle': '',
				'monto': '',
				'numero_recibo': '',
				'tipo_pago': '',
			},
			'abono_errors': abono_errors if is_amortizing else {},
		})

	return render(request, 'deudas_anteriores/deudas_anteriores.html', {
		'deuda_items': deuda_items,
		'page_obj': pagina,
		'clientes': Cliente.objects.order_by('nombre'),
		'creation_values': creation_values or {
			'cliente': '',
			'fecha_cobro': '',
			'detalle': '',
			'monto_total': '',
		},
		'creation_errors': creation_errors or {},
		'busqueda': busqueda,
		'cliente_filtro': cliente_filtro,
		'estado_filtro': estado_filtro,
		'puede_gestionar': puede_gestionar_clientes(request.user),
		'total_deudas': len(deudas_list),
		'total_registrado': sum((deuda.monto_total for deuda in deudas_list), Decimal('0.00')),
		'total_abonado': sum((deuda.monto_pagado for deuda in deudas_list), Decimal('0.00')),
		'open_modal': open_modal,
		'hoy': timezone.localdate(),
		'tipos_pago': AbonoDeudaAnterior.TipoPago.choices,
	})


@login_required
def index(request):
	return _render_index(request)


@solo_gestores_clientes
@require_POST
def crear(request):
	values = _form_values(request.POST, ('cliente', 'fecha_cobro', 'detalle', 'monto_total'))
	errors = {}
	debt_data = _validate_debt(values, errors)
	if debt_data is not None:
		CobroAnterior.objects.create(**debt_data, registrado_por=request.user)
		messages.success(request, 'Se registró la deuda anterior.')
		return redirect('deudas_anteriores:index')
	return _render_index(
		request,
		creation_values=values,
		creation_errors=errors,
		open_modal='crear',
	)


@login_required
def detalle(request, deuda_id):
	get_object_or_404(CobroAnterior, pk=deuda_id)
	return _render_index(
		request,
		focus_deuda_id=deuda_id,
		open_modal=f'ver-{deuda_id}',
	)


@solo_gestores_clientes
@require_POST
def editar(request, deuda_id):
	values = _form_values(request.POST, ('cliente', 'fecha_cobro', 'detalle', 'monto_total'))
	errors = {}
	with transaction.atomic():
		deuda = get_object_or_404(
			CobroAnterior.objects.select_for_update().select_related('cliente').prefetch_related('abonos'),
			pk=deuda_id,
		)
		debt_data = _validate_debt(values, errors, debt=deuda)
		if debt_data is not None:
			for field, value in debt_data.items():
				setattr(deuda, field, value)
			deuda.save()
			messages.success(request, 'Se actualizaron los datos de la deuda.')
			return redirect('deudas_anteriores:index')

	return _render_index(
		request,
		edit_values=values,
		edit_errors=errors,
		focus_deuda_id=deuda_id,
		open_modal=f'editar-{deuda_id}',
	)


@solo_gestores_clientes
@require_POST
def amortizar(request, deuda_id):
	values = _form_values(request.POST, ('fecha_cobro', 'detalle', 'monto', 'numero_recibo', 'tipo_pago'))
	errors = {}
	with transaction.atomic():
		deuda = get_object_or_404(
			CobroAnterior.objects.select_for_update().select_related('cliente').prefetch_related('abonos'),
			pk=deuda_id,
		)
		payment_data = _validate_payment(values, deuda, errors)
		if payment_data is not None:
			AbonoDeudaAnterior.objects.create(
				**payment_data,
				deuda=deuda,
				registrado_por=request.user,
			)
			messages.success(request, 'Se registró el abono de la deuda.')
			return redirect('deudas_anteriores:index')

	return _render_index(
		request,
		abono_values=values,
		abono_errors=errors,
		focus_deuda_id=deuda_id,
		open_modal=f'amortizar-{deuda_id}',
	)


@solo_gestores_clientes
def eliminar(request, deuda_id):
	deuda = get_object_or_404(CobroAnterior, pk=deuda_id)
	if request.method == 'POST':
		deuda.delete()
		messages.success(request, 'Se eliminó la deuda anterior y su historial de abonos.')
		return redirect('deudas_anteriores:index')

	return _render_index(
		request,
		focus_deuda_id=deuda_id,
		open_modal=f'eliminar-{deuda_id}',
	)
