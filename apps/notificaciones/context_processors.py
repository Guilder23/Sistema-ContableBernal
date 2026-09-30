from .models import Notificacion


def notificaciones_usuario(request):
    usuario = request.user
    if not usuario.is_authenticated:
        return {'notificaciones_no_leidas': 0, 'notificaciones_recientes': ()}

    pendientes = Notificacion.objects.filter(destinatario=usuario, leida_en__isnull=True)
    return {
        'notificaciones_no_leidas': pendientes.count(),
        'notificaciones_recientes': pendientes[:5],
    }
