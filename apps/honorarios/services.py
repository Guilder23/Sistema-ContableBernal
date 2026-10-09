from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.clientes.models import Cliente
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import CobroHonorario, DetalleCobroHonorario, TarifaCliente

MESES_NOMBRES = (
	'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
	'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)


def _guardar_detalles_recurrentes(cobro, tarifa, periodo_tipo):
	if periodo_tipo == CobroHonorario.Periodicidad.MENSUAL:
		monto_base = tarifa.monto_mensual
		servicios = (
			(DetalleCobroHonorario.TipoServicio.GESTORA, 'Gestora', tarifa.extra_gestora),
			(DetalleCobroHonorario.TipoServicio.MINISTERIO, 'Ministerio', tarifa.extra_ministerio),
			(DetalleCobroHonorario.TipoServicio.CAJA, 'Caja', tarifa.extra_caja),
			(DetalleCobroHonorario.TipoServicio.OTRO, 'Bancarización', tarifa.extra_bancarizacion),
			(DetalleCobroHonorario.TipoServicio.OTRO, 'Otros servicios recurrentes', tarifa.extra_otros),
		)
	elif periodo_tipo == CobroHonorario.Periodicidad.ANUAL:
		monto_base = tarifa.monto_anual
		servicios = ((DetalleCobroHonorario.TipoServicio.SEPREC, 'SEPREC anual', tarifa.extra_seprec),)
	else:
		monto_base = tarifa.monto_trimestral
		servicios = ()
	if monto_base > Decimal('0.00'):
		DetalleCobroHonorario.objects.create(
			cobro=cobro,
			tipo_servicio=DetalleCobroHonorario.TipoServicio.HONORARIO,
			concepto='Honorario contable',
			monto=monto_base,
		)
	for tipo_servicio, concepto, monto in servicios:
		if monto > Decimal('0.00'):
			DetalleCobroHonorario.objects.create(
				cobro=cobro,
				tipo_servicio=tipo_servicio,
				concepto=concepto,
				monto=monto,
			)


def generar_cobro_periodo(cliente, periodo_tipo, anio, periodo_numero, usuario=None):
	tarifa = TarifaCliente.objects.filter(cliente=cliente).first()
	if tarifa is None:
		return None, False

	if periodo_tipo == CobroHonorario.Periodicidad.MENSUAL:
		if not 1 <= periodo_numero <= 12:
			return None, False
		monto_base = tarifa.monto_mensual
		monto_extras = (
			tarifa.extra_bancarizacion
			+ tarifa.extra_gestora
			+ tarifa.extra_ministerio
			+ tarifa.extra_caja
			+ tarifa.extra_otros
		)
		periodo = f'{MESES_NOMBRES[periodo_numero - 1]} {anio}'
		fecha_vencimiento = date(anio, periodo_numero, 28)
	elif periodo_tipo == CobroHonorario.Periodicidad.TRIMESTRAL:
		if not 1 <= periodo_numero <= 4:
			return None, False
		monto_base = tarifa.monto_trimestral
		monto_extras = Decimal('0.00')
		periodo = f'{periodo_numero}.er trimestre {anio}'
		fecha_vencimiento = None
	elif periodo_tipo == CobroHonorario.Periodicidad.ANUAL:
		monto_base = tarifa.monto_anual
		monto_extras = tarifa.extra_seprec
		periodo = f'Ejercicio fiscal {anio}'
		fecha_vencimiento = None
	else:
		return None, False

	monto_total = monto_base + monto_extras
	if monto_total <= Decimal('0.00'):
		return None, False

	cobro, creado = CobroHonorario.objects.get_or_create(
		cliente=cliente,
		periodo_tipo=periodo_tipo,
		anio=anio,
		periodo_numero=periodo_numero,
		defaults={
			'concepto': f'Honorarios contables - {periodo}',
			'monto_base': monto_base,
			'monto_extras': monto_extras,
			'monto_total': monto_total,
			'fecha_vencimiento': fecha_vencimiento,
			'generado_por': usuario if getattr(usuario, 'is_authenticated', False) else None,
		},
	)
	if creado:
		cobro.tipo_ingreso = CobroHonorario.TipoIngreso.RECURRENTE
		cobro.save(update_fields=('tipo_ingreso', 'actualizado_en'))
		_guardar_detalles_recurrentes(cobro, tarifa, periodo_tipo)
		registrar_historial(
			cliente=cliente,
			usuario=usuario,
			tipo_accion=EntradaHistorial.TipoAccion.PAGO,
			titulo=f'Cobro de honorarios generado: {periodo}',
			descripcion=f'Monto total a cobrar: Bs {monto_total}',
		)
	return cobro, creado


@transaction.atomic
def generar_honorarios_mensuales(anio, mes, usuario=None, cliente_id=None, incluir_cero=True, monto_sugerido_defecto=Decimal('0.00')):
	clientes_consulta = Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).select_related('tarifa')
	if cliente_id:
		clientes_consulta = clientes_consulta.filter(pk=cliente_id)

	nombre_mes = MESES_NOMBRES[mes - 1]
	concepto_base = f'Honorarios Contables - {nombre_mes} {anio}'
	fecha_vencimiento = date(anio, mes, 28)

	creados = 0
	existentes = 0
	omitidos_cero = 0

	for cliente in clientes_consulta:
		tarifa = getattr(cliente, 'tarifa', None)
		if not tarifa:
			tarifa = TarifaCliente.objects.create(cliente=cliente)

		total = tarifa.total_mensual_sugerido
		if total <= Decimal('0.00'):
			if monto_sugerido_defecto > Decimal('0.00'):
				total = monto_sugerido_defecto
			elif not incluir_cero:
				omitidos_cero += 1
				continue

		cobro, creado = CobroHonorario.objects.get_or_create(
			cliente=cliente,
			periodo_tipo=CobroHonorario.Periodicidad.MENSUAL,
			anio=anio,
			periodo_numero=mes,
			defaults={
				'concepto': concepto_base,
				'monto_base': tarifa.monto_mensual if tarifa.monto_mensual > 0 else total,
				'monto_extras': (
					tarifa.extra_bancarizacion
					+ tarifa.extra_gestora
					+ tarifa.extra_ministerio
					+ tarifa.extra_caja
					+ tarifa.extra_otros
				),
				'monto_total': total,
				'fecha_vencimiento': fecha_vencimiento,
				'generado_por': usuario if getattr(usuario, 'is_authenticated', False) else None,
			}
		)


		if creado:
			cobro.tipo_ingreso = CobroHonorario.TipoIngreso.RECURRENTE
			cobro.save(update_fields=('tipo_ingreso', 'actualizado_en'))
			_guardar_detalles_recurrentes(cobro, tarifa, CobroHonorario.Periodicidad.MENSUAL)
			creados += 1
			registrar_historial(
				cliente=cliente,
				usuario=usuario,
				tipo_accion=EntradaHistorial.TipoAccion.PAGO,
				titulo=f'Honorario mensual generado: {nombre_mes} {anio}',
				descripcion=f'Monto total a cobrar: Bs {total}',
			)
		else:
			existentes += 1

	return {
		'creados': creados,
		'existentes': existentes,
		'omitidos_cero': omitidos_cero,
	}


@transaction.atomic
def generar_seprec_anual(anio, usuario=None, cliente_id=None):
	clientes = Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).select_related('tarifa')
	if cliente_id:
		clientes = clientes.filter(pk=cliente_id)
	creados = 0
	existentes = 0
	omitidos = 0
	for cliente in clientes:
		tarifa = getattr(cliente, 'tarifa', None)
		if not tarifa or tarifa.extra_seprec <= Decimal('0.00'):
			omitidos += 1
			continue
		cobro, creado = generar_cobro_periodo(
			cliente,
			CobroHonorario.Periodicidad.ANUAL,
			anio,
			0,
			usuario=usuario,
		)
		if creado:
			creados += 1
		else:
			existentes += 1
	return {'creados': creados, 'existentes': existentes, 'omitidos': omitidos}
