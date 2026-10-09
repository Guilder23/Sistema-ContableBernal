from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.clientes.permissions import puede_gestionar_clientes
from apps.honorarios.models import CobroHonorario, PagoHonorario
from apps.servicios.models import PagoServicioTramite, ServicioTramite


@login_required
def index(request):
	hoy = timezone.localdate()
	try:
		anio = int(request.GET.get('anio', hoy.year))
		if not 2000 <= anio <= 2200:
			anio = hoy.year
	except (TypeError, ValueError):
		anio = hoy.year
	busqueda = request.GET.get('q', '').strip()
	estado_filtro = request.GET.get('estado', '').strip()
	origen_filtro = request.GET.get('origen', '').strip()

	cobros = CobroHonorario.objects.select_related('cliente').prefetch_related('pagos').filter(anio=anio)
	pagos = PagoHonorario.objects.select_related('cobro', 'cobro__cliente', 'registrado_por').filter(
		fecha_pago__year=anio,
	)
	pagos_servicios = PagoServicioTramite.objects.select_related(
		'servicio', 'servicio__cliente', 'registrado_por',
	).filter(fecha_pago__year=anio)
	servicios = ServicioTramite.objects.prefetch_related('pagos').filter(fecha_solicitud__year=anio)
	if busqueda:
		consulta = (
			Q(concepto__icontains=busqueda)
			| Q(cliente__nombre__icontains=busqueda)
			| Q(cliente__razon_social__icontains=busqueda)
		)
		cobros = cobros.filter(consulta)
		pagos = pagos.filter(
			Q(cobro__concepto__icontains=busqueda)
			| Q(cobro__cliente__nombre__icontains=busqueda)
			| Q(cobro__cliente__razon_social__icontains=busqueda)
			| Q(numero_recibo__icontains=busqueda)
		)
		pagos_servicios = pagos_servicios.filter(
			Q(servicio__concepto__icontains=busqueda)
			| Q(servicio__cliente__nombre__icontains=busqueda)
			| Q(servicio__cliente__documento__icontains=busqueda)
			| Q(numero_recibo__icontains=busqueda)
		)
	if estado_filtro in {value for value, _ in CobroHonorario.Estado.choices}:
		cobros = cobros.filter(estado=estado_filtro)
		pagos = pagos.filter(cobro__estado=estado_filtro)
	if origen_filtro in {value for value, _ in CobroHonorario.Periodicidad.choices}:
		cobros = cobros.filter(periodo_tipo=origen_filtro)
		pagos = pagos.filter(cobro__periodo_tipo=origen_filtro)
	servicios = servicios.order_by('-fecha_solicitud', '-pk')

	total_ingresos_anio = (
		(pagos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'))
		+ (pagos_servicios.aggregate(total=Sum('monto'))['total'] or Decimal('0.00'))
	)
	total_ingresos_mes = PagoHonorario.objects.filter(
		fecha_pago__year=hoy.year,
		fecha_pago__month=hoy.month,
	).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
	total_ingresos_mes += PagoServicioTramite.objects.filter(
		fecha_pago__year=hoy.year,
		fecha_pago__month=hoy.month,
	).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
	total_cargos = (
		(cobros.exclude(estado=CobroHonorario.Estado.CANCELADO).aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00'))
		+ (servicios.aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00'))
	)
	total_pendiente = sum((
		cobro.saldo_pendiente for cobro in cobros
		if cobro.estado != CobroHonorario.Estado.CANCELADO
	), Decimal('0.00'))
	total_pendiente += sum((servicio.saldo_pendiente for servicio in servicios), Decimal('0.00'))

	pagos_page = Paginator(pagos.order_by('-fecha_pago', '-creado_en'), 20).get_page(request.GET.get('page_pagos'))
	pagos_servicios_page = Paginator(pagos_servicios.order_by('-fecha_pago', '-creado_en'), 20).get_page(request.GET.get('page_pagos_servicios'))
	cobros_page = Paginator(cobros.order_by('fecha_vencimiento', 'cliente__nombre'), 20).get_page(request.GET.get('page_cobros'))
	query_params = request.GET.copy()
	query_params.pop('page_pagos', None)
	query_params.pop('page_pagos_servicios', None)
	query_params.pop('page_cobros', None)

	return render(request, 'ingresos/ingresos.html', {
		'titulo_modulo': 'Ingresos',
		'descripcion_modulo': 'Cobros recibidos, trabajos extras y cuentas pendientes de clientes.',
		'modulo_activo': 'ingresos',
		'hoy': hoy,
		'anio': anio,
		'busqueda': busqueda,
		'estado_filtro': estado_filtro,
		'origen_filtro': origen_filtro,
		'estados': CobroHonorario.Estado.choices,
		'origenes': CobroHonorario.Periodicidad.choices,
		'metodos_pago': PagoHonorario.MetodoPago.choices,
		'pagos': pagos_page.object_list,
		'pagos_page': pagos_page,
		'pagos_servicios': pagos_servicios_page.object_list,
		'pagos_servicios_page': pagos_servicios_page,
		'cobros': cobros_page.object_list,
		'cobros_page': cobros_page,
		'query_string': query_params.urlencode(),
		'total_pagos': pagos.count(),
		'total_pagos_servicios': pagos_servicios.count(),
		'total_cobros': cobros.count(),
		'total_ingresos_anio': total_ingresos_anio,
		'total_ingresos_mes': total_ingresos_mes,
		'total_cargos': total_cargos,
		'total_pendiente': total_pendiente,
		'puede_gestionar': puede_gestionar_clientes(request.user),
	})