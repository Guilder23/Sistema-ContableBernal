from datetime import datetime

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import EventoAgenda, GoogleCalendarCredential


CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def _credenciales_google():
    cuenta = GoogleCalendarCredential.objects.filter(singleton=1).first()
    if cuenta is None:
        return None
    credenciales = Credentials(
        token=None,
        refresh_token=cuenta.get_refresh_token(),
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=CALENDAR_SCOPES,
    )
    credenciales.refresh(Request())
    return credenciales


def _servicio_calendar():
    credenciales = _credenciales_google()
    if credenciales is None:
        return None
    return build('calendar', 'v3', credentials=credenciales, cache_discovery=False)


def _fecha_hora_google(fecha, hora):
    valor = datetime.combine(fecha, hora)
    consciente = timezone.make_aware(valor, timezone.get_current_timezone())
    return consciente.isoformat()


def _cuerpo_evento(evento):
    detalles = []
    if evento.cliente:
        detalles.append(f'Cliente: {evento.cliente.nombre}')
    if evento.responsable:
        nombre = evento.responsable.get_full_name() or evento.responsable.username
        detalles.append(f'Responsable: {nombre}')
    if evento.observaciones:
        detalles.append(evento.observaciones)
    return {
        'summary': evento.titulo,
        'description': '\n'.join(detalles),
        'location': evento.lugar,
        'start': {
            'dateTime': _fecha_hora_google(evento.fecha, evento.hora_inicio),
            'timeZone': settings.TIME_ZONE,
        },
        'end': {
            'dateTime': _fecha_hora_google(evento.fecha, evento.hora_fin),
            'timeZone': settings.TIME_ZONE,
        },
    }


def _marcar_error(evento_id, mensaje='No se pudo sincronizar con Google Calendar.'):
    EventoAgenda.objects.filter(pk=evento_id).update(
        google_sync_status='error',
        google_sync_error=mensaje[:500],
    )


def sincronizar_evento_google(evento_id):
    evento = EventoAgenda.objects.select_related('cliente', 'responsable').filter(pk=evento_id).first()
    if evento is None:
        return False
    try:
        servicio = _servicio_calendar()
        if servicio is None:
            return False
        cuerpo = _cuerpo_evento(evento)
        if evento.google_event_id:
            try:
                resultado = servicio.events().update(
                    calendarId='primary',
                    eventId=evento.google_event_id,
                    body=cuerpo,
                ).execute()
            except HttpError as error:
                if error.resp.status != 404:
                    raise
                resultado = servicio.events().insert(calendarId='primary', body=cuerpo).execute()
        else:
            resultado = servicio.events().insert(calendarId='primary', body=cuerpo).execute()
        EventoAgenda.objects.filter(pk=evento_id).update(
            google_event_id=resultado['id'],
            google_sync_status='synced',
            google_sync_error='',
        )
        return True
    except Exception:
        _marcar_error(evento_id)
        return False


def sincronizar_eventos_pendientes():
    ids_pendientes = EventoAgenda.objects.filter(
        google_sync_status__in=('pending', 'error'),
    ).values_list('pk', flat=True)
    exitosos = 0
    fallidos = 0
    for evento_id in ids_pendientes.iterator():
        if sincronizar_evento_google(evento_id):
            exitosos += 1
        else:
            fallidos += 1
    return exitosos, fallidos


def eliminar_evento_google(evento):
    if not evento.google_event_id:
        return True
    try:
        servicio = _servicio_calendar()
        if servicio is None:
            _marcar_error(evento.pk, 'Conecta Google Calendar para eliminar este evento también de Google.')
            return False
        servicio.events().delete(calendarId='primary', eventId=evento.google_event_id).execute()
        return True
    except HttpError as error:
        if error.resp.status == 404:
            return True
        _marcar_error(evento.pk)
        return False
    except Exception:
        _marcar_error(evento.pk)
        return False
