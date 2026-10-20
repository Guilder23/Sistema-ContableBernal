from datetime import time

from django.db import transaction

from apps.agenda.google_calendar import eliminar_evento_google, sincronizar_evento_google
from apps.agenda.models import EventoAgenda


class ErrorRecordatorioAgenda(Exception):
    pass


def sincronizar_recordatorio_vencimiento(cliente, usuario):
    evento = cliente.evento_vencimiento_facturacion
    fecha_vencimiento = cliente.fecha_vencimiento_facturacion

    if fecha_vencimiento is None:
        if evento is None:
            return
        if not eliminar_evento_google(evento):
            raise ErrorRecordatorioAgenda(
                'No se pudo quitar de Google Calendar el recordatorio anterior. '
                'El vencimiento no fue modificado.'
            )
        evento.delete()
        cliente.evento_vencimiento_facturacion = None
        cliente.save(update_fields=['evento_vencimiento_facturacion'])
        return

    nombre = cliente.razon_social or cliente.nombre
    titulo = f'Notificar vencimiento de facturación: {nombre}'[:160]
    observaciones = (
        f'Recordar notificar al cliente sobre el vencimiento de facturación '
        f'del {fecha_vencimiento:%d/%m/%Y}.'
    )
    if evento is None:
        evento = EventoAgenda(
            creado_por=usuario,
            cliente=cliente,
            tipo=EventoAgenda.Tipo.RECORDATORIO,
            estado=EventoAgenda.Estado.PROGRAMADO,
        )

    evento.titulo = titulo
    evento.tipo = EventoAgenda.Tipo.RECORDATORIO
    evento.fecha = fecha_vencimiento
    evento.hora_inicio = time(9, 0)
    evento.hora_fin = time(9, 30)
    evento.cliente = cliente
    evento.estado = EventoAgenda.Estado.PROGRAMADO
    evento.lugar = ''
    evento.observaciones = observaciones
    evento.save()

    if cliente.evento_vencimiento_facturacion_id != evento.pk:
        cliente.evento_vencimiento_facturacion = evento
        cliente.save(update_fields=['evento_vencimiento_facturacion'])

    transaction.on_commit(
        lambda evento_id=evento.pk: sincronizar_evento_google(evento_id),
        robust=True,
    )
