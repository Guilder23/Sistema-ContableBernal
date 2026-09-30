import calendar
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.clientes.models import Cliente
from apps.tareas.models import Tarea

from .models import ConfiguracionCliente, DiaNoLaborable, Obligacion, TipoObligacion


DIAS_POR_TERMINACION_NIT = {
	0: 13,
	1: 14,
	2: 15,
	3: 16,
	4: 17,
	5: 18,
	6: 19,
	7: 20,
	8: 21,
	9: 22,
}

CIERRES_FISCALES = {
	Cliente.Actividad.COMERCIAL: (12, 31),
	Cliente.Actividad.SERVICIOS: (12, 31),
	Cliente.Actividad.OTRA: (12, 31),
	Cliente.Actividad.INDUSTRIAL: (3, 31),
	Cliente.Actividad.CONSTRUCTORA: (3, 31),
	Cliente.Actividad.AGRICOLA: (6, 30),
	Cliente.Actividad.GANADERA: (6, 30),
	Cliente.Actividad.AGROINDUSTRIAL: (6, 30),
	Cliente.Actividad.MINERA: (9, 30),
}


def _sumar_meses(fecha, cantidad):
	indice = fecha.year * 12 + fecha.month - 1 + cantidad
	anio, mes_cero = divmod(indice, 12)
	mes = mes_cero + 1
	dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
	return date(anio, mes, dia)


def _es_habil(fecha, dias_no_laborables):
	return fecha.weekday() < 5 and fecha not in dias_no_laborables


def _siguiente_habil(fecha, dias_no_laborables):
	while not _es_habil(fecha, dias_no_laborables):
		fecha += timedelta(days=1)
	return fecha


def _ultimo_habil(anio, mes, dias_no_laborables):
	fecha = date(anio, mes, calendar.monthrange(anio, mes)[1])
	while not _es_habil(fecha, dias_no_laborables):
		fecha -= timedelta(days=1)
	return fecha


def periodo_de_obligacion(tipo, cliente, anio, numero):
	if tipo.periodicidad == TipoObligacion.Periodicidad.MENSUAL:
		if not 1 <= numero <= 12:
			raise ValidationError('Selecciona un mes válido.')
		return date(anio, numero, 1), date(anio, numero, calendar.monthrange(anio, numero)[1])

	if tipo.periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL:
		if not 1 <= numero <= 4:
			raise ValidationError('Selecciona un trimestre válido.')
		mes_inicio = (numero - 1) * 3 + 1
		mes_fin = mes_inicio + 2
		return date(anio, mes_inicio, 1), date(anio, mes_fin, calendar.monthrange(anio, mes_fin)[1])

	if tipo.periodicidad == TipoObligacion.Periodicidad.ANUAL:
		mes_cierre, dia_cierre = CIERRES_FISCALES.get(cliente.actividad, (12, 31))
		cierre = date(anio, mes_cierre, dia_cierre)
		cierre_anterior = date(anio - 1, mes_cierre, dia_cierre)
		return cierre_anterior + timedelta(days=1), cierre

	raise ValidationError('La periodicidad de la obligación no es válida.')


def calcular_vencimiento(tipo, cliente, periodo_fin, dias_no_laborables=()):
	regla = tipo.regla_vencimiento
	if regla == TipoObligacion.ReglaVencimiento.MANUAL:
		return None
	if regla == TipoObligacion.ReglaVencimiento.CIERRE_FISCAL_120:
		return _siguiente_habil(periodo_fin + timedelta(days=120), dias_no_laborables)

	mes_destino = _sumar_meses(date(periodo_fin.year, periodo_fin.month, 1), tipo.meses_despues_periodo)
	if regla == TipoObligacion.ReglaVencimiento.ULTIMO_HABIL:
		return _ultimo_habil(mes_destino.year, mes_destino.month, dias_no_laborables)

	dia = tipo.dia_vencimiento
	if regla == TipoObligacion.ReglaVencimiento.DIGITO_NIT:
		digitos = ''.join(caracter for caracter in (cliente.nit or '') if caracter.isdigit())
		if not digitos:
			raise ValidationError(f'{cliente.nombre} no tiene un NIT con terminación numérica.')
		dia = DIAS_POR_TERMINACION_NIT[int(digitos[-1])]
	elif regla != TipoObligacion.ReglaVencimiento.DIA_FIJO:
		raise ValidationError(f'La regla de vencimiento de {tipo.nombre} no es válida.')

	if dia is None:
		raise ValidationError(f'Configura el día de vencimiento de {tipo.nombre}.')
	dia = min(dia, calendar.monthrange(mes_destino.year, mes_destino.month)[1])
	return _siguiente_habil(date(mes_destino.year, mes_destino.month, dia), dias_no_laborables)


@transaction.atomic
def generar_obligaciones(periodicidad, anio, numero, cliente_id=None):
	configuraciones_consulta = (
		ConfiguracionCliente.objects.select_related('cliente', 'tipo')
		.filter(
			activa=True,
			cliente__estado=Cliente.Estado.ACTIVO,
		tipo__activa=True,
			tipo__periodicidad=periodicidad,
		)
		.order_by('cliente__nombre', 'tipo__nombre')
	)
	if cliente_id is not None:
		configuraciones_consulta = configuraciones_consulta.filter(cliente_id=cliente_id)
	configuraciones = configuraciones_consulta
	dias_no_laborables = set(
		DiaNoLaborable.objects.filter(fecha__year__in=(anio - 1, anio, anio + 1)).values_list('fecha', flat=True)
	)
	creadas = 0
	existentes = 0
	tareas_creadas = 0
	sin_vigencia = 0
	errores = []

	for configuracion in configuraciones:
		cliente = configuracion.cliente
		tipo = configuracion.tipo
		periodo_inicio, periodo_fin = periodo_de_obligacion(tipo, cliente, anio, numero)
		if configuracion.fecha_inicio > periodo_fin:
			sin_vigencia += 1
			continue
		try:
			vencimiento = calcular_vencimiento(tipo, cliente, periodo_fin, dias_no_laborables)
		except ValidationError as error:
			errores.append(str(error.message))
			continue

		obligacion, creada = Obligacion.objects.get_or_create(
			cliente=cliente,
			tipo=tipo,
			anio=anio,
			periodo_numero=numero,
			defaults={
				'periodo_inicio': periodo_inicio,
				'periodo_fin': periodo_fin,
				'fecha_vencimiento': vencimiento,
			},
		)
		_, tarea_creada = Tarea.objects.get_or_create(obligacion=obligacion)
		creadas += int(creada)
		existentes += int(not creada)
		tareas_creadas += int(tarea_creada)

	return {
		'creadas': creadas,
		'existentes': existentes,
		'tareas_creadas': tareas_creadas,
		'sin_vigencia': sin_vigencia,
		'errores': errores,
	}