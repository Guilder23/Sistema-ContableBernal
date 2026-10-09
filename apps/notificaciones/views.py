from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import Notificacion


@login_required
def index(request):
    notificaciones = Notificacion.objects.filter(destinatario=request.user)
    estado = request.GET.get('estado', '')
    if estado == 'pendientes':
        notificaciones = notificaciones.filter(leida_en__isnull=True)
    elif estado == 'leidas':
        notificaciones = notificaciones.filter(leida_en__isnull=False)
    return render(request, 'notificaciones/notificaciones.html', {
        'titulo_modulo': 'Notificaciones',
        'descripcion_modulo': 'Avisos sobre tareas asignadas y completadas.',
        'notificaciones': notificaciones,
        'estado_filtro': estado,
        'pendientes': Notificacion.objects.filter(destinatario=request.user, leida_en__isnull=True).count(),
    })


@login_required
@require_POST
def marcar_leida(request, notificacion_id):
    notificacion = get_object_or_404(Notificacion, pk=notificacion_id, destinatario=request.user)
    ya_leida = notificacion.leida_en is not None
    notificacion.marcar_leida()
    if not ya_leida:
        registrar_historial(
            cliente=None,
            usuario=request.user,
            tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
            seccion=EntradaHistorial.Seccion.NOTIFICACIONES,
            referencia=str(notificacion.pk),
            titulo='Notificación marcada como leída',
            descripcion=notificacion.titulo,
        )
    return redirect('notificaciones:index')


@login_required
@require_POST
def marcar_todas_leidas(request):
    pendientes = Notificacion.objects.filter(destinatario=request.user, leida_en__isnull=True)
    cantidad = pendientes.count()
    pendientes.update(leida_en=timezone.now())
    if cantidad:
        registrar_historial(
            cliente=None,
            usuario=request.user,
            tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
            seccion=EntradaHistorial.Seccion.NOTIFICACIONES,
            referencia=str(cantidad),
            titulo='Notificaciones marcadas como leídas',
            descripcion=f'{cantidad} notificación(es) actualizada(s).',
        )
    messages.success(request, 'Se marcaron tus notificaciones pendientes como leídas.')
    return redirect('notificaciones:index')
