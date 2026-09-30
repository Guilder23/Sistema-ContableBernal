from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

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
    notificacion.marcar_leida()
    return redirect('notificaciones:index')


@login_required
@require_POST
def marcar_todas_leidas(request):
    Notificacion.objects.filter(destinatario=request.user, leida_en__isnull=True).update(leida_en=timezone.now())
    messages.success(request, 'Se marcaron tus notificaciones pendientes como leídas.')
    return redirect('notificaciones:index')
