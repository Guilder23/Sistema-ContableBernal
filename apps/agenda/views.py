import calendar
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import EventoAgenda


MESES_AGENDA = (
	'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
	'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
)
DIAS_SEMANA = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


def _datos_post(request):
	return {
		'titulo': request.POST.get('titulo', '').strip(),
		'tipo': request.POST.get('tipo', '').strip(),
		'fecha': request.POST.get('fecha', '').strip(),
		'hora_inicio': request.POST.get('hora_inicio', '').strip(),
		'hora_fin': request.POST.get('hora_fin', '').strip(),
		'cliente': request.POST.get('cliente', '').strip(),
		'responsable': request.POST.get('responsable', '').strip(),
		'estado': request.POST.get('estado', EventoAgenda.Estado.PROGRAMADO).strip(),
		'lugar': request.POST.get('lugar', '').strip(),
		'observaciones': request.POST.get('observaciones', '').strip(),
	}


@transaction.atomic
def _validar_y_guardar(request, evento=None):
	es_nuevo = evento is None
	datos = _datos_post(request)
	errores = {}
	fecha = parse_date(datos['fecha'])
	hora_inicio = parse_time(datos['hora_inicio'])
	hora_fin = parse_time(datos['hora_fin'])
	cliente = None
	responsable = None
	if not datos['titulo'] or len(datos['titulo']) > 160:
		errores['titulo'] = 'Ingresa un título de hasta 160 caracteres.'
	if fecha is None:
		errores['fecha'] = 'Ingresa una fecha válida.'
	if hora_inicio is None:
		errores['hora_inicio'] = 'Ingresa una hora de inicio válida.'
	if hora_fin is None:
		errores['hora_fin'] = 'Ingresa una hora de fin válida.'
	if datos['tipo'] not in {value for value, _ in EventoAgenda.Tipo.choices}:
		errores['tipo'] = 'Selecciona un tipo de evento válido.'
	if datos['estado'] not in {value for value, _ in EventoAgenda.Estado.choices}:
		errores['estado'] = 'Selecciona un estado válido.'
	if len(datos['lugar']) > 160 or len(datos['observaciones']) > 2000:
		errores['general'] = 'El lugar o las observaciones exceden su longitud permitida.'
	if datos['cliente']:
		if not datos['cliente'].isdigit():
			errores['cliente'] = 'Selecciona un cliente válido.'
		else:
			cliente = Cliente.objects.filter(pk=int(datos['cliente'])).first()
			if cliente is None:
				errores['cliente'] = 'El cliente seleccionado no existe.'
	if datos['responsable']:
		if not datos['responsable'].isdigit():
			errores['responsable'] = 'Selecciona un responsable válido.'
		else:
			responsable = get_user_model().objects.select_for_update().filter(
				pk=int(datos['responsable']),
				is_active=True,
			).first()
			if responsable is None:
				errores['responsable'] = 'El responsable seleccionado no existe o está inactivo.'
	if fecha and hora_inicio and hora_fin and hora_fin <= hora_inicio:
		errores['hora_fin'] = 'La hora de fin debe ser posterior a la hora de inicio.'
	if errores:
		return None, datos, errores
	if evento is None:
		evento = EventoAgenda(creado_por=request.user)
	evento.titulo = datos['titulo']
	evento.tipo = datos['tipo']
	evento.fecha = fecha
	evento.hora_inicio = hora_inicio
	evento.hora_fin = hora_fin
	evento.cliente = cliente
	evento.responsable = responsable
	evento.estado = datos['estado']
	evento.lugar = datos['lugar']
	evento.observaciones = datos['observaciones']
	try:
		evento.full_clean()
	except ValidationError as error:
		for campo, mensajes in error.message_dict.items():
			errores[campo] = ' '.join(mensajes)
		return None, datos, errores
	evento.save()
	registrar_historial(
		cliente=evento.cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.CREACION if es_nuevo else EntradaHistorial.TipoAccion.MODIFICACION,
		seccion=EntradaHistorial.Seccion.AGENDA,
		referencia=evento.titulo,
		titulo=f"{'Evento creado' if es_nuevo else 'Evento actualizado'}: {evento.titulo}",
		descripcion=f'{evento.fecha:%d/%m/%Y} · {evento.hora_inicio:%H:%M}–{evento.hora_fin:%H:%M}',
	)
	return evento, datos, {}


def _contexto_index(request, datos=None, errores=None, modal_activo='', evento_edicion=None):
	hoy = timezone.localdate()
	try:
		anio = int(request.GET.get('anio', hoy.year))
		mes = int(request.GET.get('mes', hoy.month))
		if not 2000 <= anio <= 2200 or not 1 <= mes <= 12:
			raise ValueError
	except (TypeError, ValueError):
		anio, mes = hoy.year, hoy.month
	busqueda = request.GET.get('q', '').strip()
	cliente_filtro = request.GET.get('cliente', '').strip()
	responsable_filtro = request.GET.get('responsable', '').strip()
	tipo_filtro = request.GET.get('tipo', '').strip()
	estado_filtro = request.GET.get('estado', '').strip()

	primer_dia = date(anio, mes, 1)
	ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
	eventos = EventoAgenda.objects.select_related('cliente', 'responsable', 'creado_por').filter(
		fecha__range=(primer_dia, ultimo_dia),
	)
	if busqueda:
		eventos = eventos.filter(
			Q(titulo__icontains=busqueda)
			| Q(lugar__icontains=busqueda)
			| Q(observaciones__icontains=busqueda)
			| Q(cliente__nombre__icontains=busqueda)
			| Q(cliente__razon_social__icontains=busqueda)
			| Q(responsable__first_name__icontains=busqueda)
			| Q(responsable__last_name__icontains=busqueda)
			| Q(responsable__username__icontains=busqueda)
		)
	if cliente_filtro.isdigit():
		eventos = eventos.filter(cliente_id=int(cliente_filtro))
	if responsable_filtro.isdigit():
		eventos = eventos.filter(responsable_id=int(responsable_filtro))
	if tipo_filtro in {value for value, _ in EventoAgenda.Tipo.choices}:
		eventos = eventos.filter(tipo=tipo_filtro)
	if estado_filtro in {value for value, _ in EventoAgenda.Estado.choices}:
		eventos = eventos.filter(estado=estado_filtro)
	eventos_mes = list(eventos.order_by('fecha', 'hora_inicio', 'titulo'))
	eventos_por_dia = {}
	for evento in eventos_mes:
		eventos_por_dia.setdefault(evento.fecha.day, []).append(evento)
	calendario = calendar.Calendar(firstweekday=0)
	semanas = []
	for semana in calendario.monthdayscalendar(anio, mes):
		celdas = []
		for numero in semana:
			fecha_celda = date(anio, mes, numero) if numero else None
			celdas.append({
				'numero': numero,
				'fecha': fecha_celda,
				'es_hoy': fecha_celda == hoy,
				'eventos': eventos_por_dia.get(numero, []) if numero else [],
			})
		semanas.append(celdas)
	prox_eventos = EventoAgenda.objects.select_related('cliente', 'responsable').filter(
		fecha__range=(hoy, hoy + timedelta(days=7)),
		estado=EventoAgenda.Estado.PROGRAMADO,
	).order_by('fecha', 'hora_inicio')[:8]
	previo = primer_dia - timedelta(days=1)
	siguiente = ultimo_dia + timedelta(days=1)
	return {
		'titulo_modulo': 'Agenda',
		'descripcion_modulo': 'Citas y recordatorios del equipo.',
		'hoy': hoy,
		'eventos': eventos_mes,
		'eventos_mes': len(eventos_mes),
		'eventos_hoy': EventoAgenda.objects.filter(fecha=hoy, estado=EventoAgenda.Estado.PROGRAMADO).count(),
		'proximos': prox_eventos,
		'semanas': semanas,
		'dias_semana': DIAS_SEMANA,
		'mes': mes,
		'anio': anio,
		'mes_nombre': MESES_AGENDA[mes - 1],
		'mes_anterior': previo.month,
		'anio_anterior': previo.year,
		'mes_siguiente': siguiente.month,
		'anio_siguiente': siguiente.year,
		'busqueda': busqueda,
		'cliente_filtro': cliente_filtro,
		'responsable_filtro': responsable_filtro,
		'tipo_filtro': tipo_filtro,
		'estado_filtro': estado_filtro,
		'tipos': EventoAgenda.Tipo.choices,
		'estados': EventoAgenda.Estado.choices,
		'clientes': Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre'),
		'usuarios': get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
		'puede_gestionar': puede_gestionar_clientes(request.user),
		'datos': datos or {},
		'errores': errores or {},
		'modal_activo': modal_activo,
		'evento_edicion': evento_edicion,
	}


@login_required
def index(request):
	return render(request, 'agenda/agenda.html', _contexto_index(request))


@solo_gestores_clientes
@require_POST
def crear(request):
	evento, datos, errores = _validar_y_guardar(request)
	if evento:
		messages.success(request, f'Se agregó «{evento.titulo}» a la agenda.')
		return redirect('agenda:index')
	return render(request, 'agenda/agenda.html', _contexto_index(request, datos, errores, 'crear'), status=400)


@solo_gestores_clientes
@require_POST
def editar(request, evento_id):
	evento = get_object_or_404(EventoAgenda, pk=evento_id)
	evento_guardado, datos, errores = _validar_y_guardar(request, evento)
	if evento_guardado:
		messages.success(request, f'Se actualizaron los datos de «{evento_guardado.titulo}».')
		return redirect('agenda:index')
	return render(
		request,
		'agenda/agenda.html',
		_contexto_index(request, datos, errores, 'editar', evento),
		status=400,
	)


@solo_gestores_clientes
@require_POST
def eliminar(request, evento_id):
	evento = get_object_or_404(EventoAgenda, pk=evento_id)
	titulo = evento.titulo
	registrar_historial(
		cliente=evento.cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.OTRO,
		seccion=EntradaHistorial.Seccion.AGENDA,
		referencia=titulo,
		titulo=f'Evento eliminado de agenda: {titulo}',
		descripcion=f'Fecha: {evento.fecha:%d/%m/%Y}',
	)
	evento.delete()
	messages.success(request, f'Se eliminó «{titulo}» de la agenda.')
	return redirect('agenda:index')