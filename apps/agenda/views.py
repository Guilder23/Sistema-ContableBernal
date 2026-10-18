import calendar
import logging
import os
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .google_calendar import eliminar_evento_google, sincronizar_evento_google, sincronizar_eventos_pendientes
from .models import EventoAgenda, GoogleCalendarCredential


logger = logging.getLogger(__name__)


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
	transaction.on_commit(lambda evento_id=evento.pk: sincronizar_evento_google(evento_id), robust=True)
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
		fecha__gte=hoy,
		estado=EventoAgenda.Estado.PROGRAMADO,
	).order_by('fecha', 'hora_inicio')
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
		'google_conectado': GoogleCalendarCredential.objects.exists(),
		'eventos_google_pendientes': EventoAgenda.objects.filter(
			google_sync_status__in=('pending', 'error'),
		).count(),
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
		evento.refresh_from_db()
		if evento.google_sync_status == 'error':
			messages.warning(request, f'Se agregó «{evento.titulo}» a la agenda, pero no se pudo sincronizar con Google Calendar.')
		else:
			messages.success(request, f'Se agregó «{evento.titulo}» a la agenda.')
		return redirect('agenda:index')
	return render(request, 'agenda/agenda.html', _contexto_index(request, datos, errores, 'crear'), status=400)


@solo_gestores_clientes
@require_POST
def editar(request, evento_id):
	evento = get_object_or_404(EventoAgenda, pk=evento_id)
	evento_guardado, datos, errores = _validar_y_guardar(request, evento)
	if evento_guardado:
		evento_guardado.refresh_from_db()
		if evento_guardado.google_sync_status == 'error':
			messages.warning(request, f'Se actualizó «{evento_guardado.titulo}» en la agenda, pero no se pudo sincronizar con Google Calendar.')
		else:
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
	if not eliminar_evento_google(evento):
		messages.error(request, f'No se eliminó «{titulo}»: no se pudo borrar en Google Calendar. El evento permanece en la agenda.')
		return redirect('agenda:index')
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


@solo_gestores_clientes
@require_POST
def google_conectar(request):
	from google_auth_oauthlib.flow import Flow

	from .google_calendar import CALENDAR_SCOPES

	try:
		GoogleCalendarCredential._fernet()
		flow = _crear_flujo_google(request, Flow, CALENDAR_SCOPES)
		url_autorizacion, estado = flow.authorization_url(
			access_type='offline',
			include_granted_scopes='true',
			prompt='consent',
		)
	except Exception:
		messages.error(request, 'No se pudo iniciar la conexión. Revisa las credenciales y GOOGLE_TOKEN_ENCRYPTION_KEY.')
		return redirect('agenda:index')
	request.session['google_calendar_oauth_state'] = estado
	request.session['google_calendar_oauth_code_verifier'] = flow.code_verifier
	return redirect(url_autorizacion)


def _crear_flujo_google(request, flow_class, scopes, state=None):
	from django.conf import settings

	client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
	client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
	if not client_id or not client_secret:
		raise ValueError('Faltan las credenciales OAuth de Google.')
	flow = flow_class.from_client_config(
		{
			'web': {
				'client_id': client_id,
				'client_secret': client_secret,
				'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
				'token_uri': 'https://oauth2.googleapis.com/token',
			}
		},
		scopes=scopes,
		state=state,
	)
	flow.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', '') or request.build_absolute_uri(
		reverse('agenda:google_callback')
	)
	return flow


@solo_gestores_clientes
def google_callback(request):
	import hmac

	from django.conf import settings
	from google_auth_oauthlib.flow import Flow

	from .google_calendar import CALENDAR_SCOPES

	estado_sesion = request.session.pop('google_calendar_oauth_state', '')
	code_verifier = request.session.pop('google_calendar_oauth_code_verifier', '')
	estado_recibido = request.GET.get('state', '')
	if (
		not estado_sesion
		or not estado_recibido
		or not code_verifier
		or not hmac.compare_digest(estado_sesion, estado_recibido)
	):
		messages.error(request, 'La autorización de Google expiró o no pudo verificarse. Intenta conectar de nuevo.')
		return redirect('agenda:index')
	if request.GET.get('error'):
		messages.error(request, 'No se autorizó el acceso a Google Calendar.')
		return redirect('agenda:index')
	try:
		flow = _crear_flujo_google(request, Flow, CALENDAR_SCOPES, state=estado_recibido)
		flow.code_verifier = code_verifier
		callback_url = request.build_absolute_uri()
		parsed_callback = urlparse(callback_url)
		allow_local_http = settings.DEBUG and parsed_callback.scheme == 'http' and parsed_callback.hostname in {
			'localhost', '127.0.0.1',
		}
		previous_insecure_transport = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT')
		try:
			if allow_local_http:
				os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
			flow.fetch_token(authorization_response=callback_url)
		finally:
			if allow_local_http:
				if previous_insecure_transport is None:
					os.environ.pop('OAUTHLIB_INSECURE_TRANSPORT', None)
				else:
					os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = previous_insecure_transport
		refresh_token = flow.credentials.refresh_token
		cuenta = GoogleCalendarCredential.objects.filter(singleton=1).first()
		if not refresh_token and cuenta:
			refresh_token = cuenta.get_refresh_token()
		if not refresh_token:
			raise ValueError('Google no devolvió un refresh token.')
		cuenta = cuenta or GoogleCalendarCredential(singleton=1)
		cuenta.set_refresh_token(refresh_token)
		cuenta.save()
	except Exception as error:
		logger.exception('Error al completar el callback OAuth de Google Calendar (%s)', type(error).__name__)
		messages.error(request, 'No se pudo completar la conexión con Google Calendar. Verifica la URL de redirección y vuelve a intentarlo.')
		return redirect('agenda:index')
	exitosos, fallidos = sincronizar_eventos_pendientes()
	if fallidos:
		messages.warning(request, f'Google Calendar quedó conectado. Se sincronizaron {exitosos} eventos; {fallidos} requieren reintento.')
	else:
		messages.success(request, f'Google Calendar conectado. Se sincronizaron {exitosos} eventos pendientes.')
	return redirect('agenda:index')


@solo_gestores_clientes
@require_POST
def google_desconectar(request):
	GoogleCalendarCredential.objects.filter(singleton=1).delete()
	EventoAgenda.objects.exclude(google_event_id='').update(google_sync_status='pending')
	messages.success(request, 'Se desconectó Google Calendar. Los eventos existentes de Google no se borraron.')
	return redirect('agenda:index')


@solo_gestores_clientes
@require_POST
def google_reintentar(request):
	if not GoogleCalendarCredential.objects.exists():
		messages.error(request, 'Conecta Google Calendar antes de reintentar la sincronización.')
		return redirect('agenda:index')
	exitosos, fallidos = sincronizar_eventos_pendientes()
	if fallidos:
		messages.warning(request, f'Se sincronizaron {exitosos} eventos; {fallidos} todavía requieren reintento.')
	else:
		messages.success(request, f'Sincronización completada: {exitosos} eventos procesados.')
	return redirect('agenda:index')