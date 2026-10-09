import mimetypes
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.clientes.permissions import puede_gestionar_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial
from apps.notificaciones.models import Notificacion
from apps.obligaciones.models import Obligacion, TipoObligacion
from apps.usuarios.models import PerfilUsuario

from .models import Tarea


def _tareas_visibles(usuario):
    tareas = Tarea.objects.select_related(
        'obligacion__cliente', 'obligacion__tipo', 'obligacion__completada_por',
        'responsable', 'asignada_por', 'evidencia_subida_por',
    )
    if not puede_gestionar_clientes(usuario):
        tareas = tareas.filter(responsable=usuario)
    return tareas


def _volver(request):
    destino = request.POST.get('volver', '')
    if url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect('tareas:index')


@login_required
def index(request):
    puede_gestionar = puede_gestionar_clientes(request.user)
    tareas = _tareas_visibles(request.user)
    busqueda = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    frecuencia = request.GET.get('frecuencia', '')
    responsable = request.GET.get('responsable', '')

    if busqueda:
        tareas = tareas.filter(
            Q(obligacion__cliente__nombre__icontains=busqueda)
            | Q(obligacion__tipo__nombre__icontains=busqueda)
            | Q(obligacion__cliente__nit__icontains=busqueda)
            | Q(observaciones__icontains=busqueda)
        )
    if estado in {valor for valor, _ in Obligacion.Estado.choices}:
        tareas = tareas.filter(obligacion__estado=estado)
    if prioridad in {valor for valor, _ in Tarea.Prioridad.choices}:
        tareas = tareas.filter(prioridad=prioridad)
    if frecuencia in {valor for valor, _ in TipoObligacion.Periodicidad.choices}:
        tareas = tareas.filter(obligacion__tipo__periodicidad=frecuencia)
    if puede_gestionar and responsable == 'mine':
        tareas = tareas.filter(responsable=request.user)
    elif puede_gestionar and responsable == 'sin_asignar':
        tareas = tareas.filter(responsable__isnull=True)
    elif puede_gestionar and responsable.isdigit():
        tareas = tareas.filter(responsable_id=int(responsable))

    query_params = request.GET.copy()
    query_params.pop('pagina', None)
    pagina = Paginator(tareas, 30).get_page(request.GET.get('pagina'))
    hoy = timezone.localdate()
    usuarios = get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username') if puede_gestionar else ()

    return render(request, 'tareas/tareas.html', {
        'tareas': pagina.object_list,
        'page_obj': pagina,
        'query_string': query_params.urlencode(),
        'busqueda': busqueda,
        'estado_filtro': estado,
        'prioridad_filtro': prioridad,
        'frecuencia_filtro': frecuencia,
        'responsable_filtro': responsable,
        'estados': Obligacion.Estado.choices,
        'prioridades': Tarea.Prioridad.choices,
        'frecuencias': TipoObligacion.Periodicidad.choices,
        'usuarios': usuarios,
        'puede_gestionar': puede_gestionar,
        'total_tareas': tareas.count(),
        'pendientes': tareas.filter(obligacion__estado=Obligacion.Estado.PENDIENTE).count(),
        'vencidas': tareas.filter(
            obligacion__estado__in=(Obligacion.Estado.PENDIENTE, Obligacion.Estado.EN_PROCESO),
            obligacion__fecha_vencimiento__lt=hoy,
        ).count(),
        'hoy': hoy,
        'volver': request.get_full_path(),
    })


@login_required
@require_POST
def asignar(request, tarea_id):
    if not puede_gestionar_clientes(request.user):
        return HttpResponseForbidden('Solo administradores y secretarios pueden asignar tareas.')
    tarea = get_object_or_404(Tarea.objects.select_related('obligacion'), pk=tarea_id)
    responsable_id = request.POST.get('responsable_id', '').strip()
    responsable = None
    if responsable_id:
        responsable = get_object_or_404(get_user_model().objects.filter(is_active=True), pk=responsable_id)

    prioridad = request.POST.get('prioridad', Tarea.Prioridad.NORMAL)
    prioridades_validas = {valor for valor, _ in Tarea.Prioridad.choices}
    observaciones = request.POST.get('observaciones', '').strip()
    if prioridad not in prioridades_validas or len(observaciones) > 2000:
        messages.error(request, 'Revisa la prioridad y las observaciones de la tarea.')
        return _volver(request)

    responsable_anterior_id = tarea.responsable_id
    tarea.responsable = responsable
    tarea.asignada_por = request.user
    tarea.prioridad = prioridad
    tarea.observaciones = observaciones
    tarea.save(update_fields=('responsable', 'asignada_por', 'prioridad', 'observaciones', 'actualizada_en'))
    registrar_historial(
        cliente=tarea.cliente,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.TAREA,
        seccion=EntradaHistorial.Seccion.TAREAS,
        referencia=tarea.titulo,
        titulo=f'Tarea asignada o actualizada: {tarea.titulo}',
        descripcion=f"Responsable: {responsable.get_full_name() or responsable.username if responsable else 'Sin asignar'} · Prioridad: {tarea.get_prioridad_display()}",
    )
    if responsable and responsable.pk != request.user.pk and responsable.pk != responsable_anterior_id:
        Notificacion.objects.create(
            destinatario=responsable,
            actor=request.user,
            tipo=Notificacion.Tipo.TAREA_ASIGNADA,
            titulo='Te asignaron una tarea',
            mensaje=f'{tarea.titulo} · {tarea.cliente.nombre}',
            url=f"{reverse('tareas:index')}?{urlencode({'q': tarea.cliente.nombre})}",
        )
    messages.success(request, f'Tarea guardada: {tarea.titulo}.')
    return _volver(request)


@login_required
@require_POST
@transaction.atomic
def actualizar_estado(request, tarea_id):
    tarea = get_object_or_404(_tareas_visibles(request.user), pk=tarea_id)
    estado = request.POST.get('estado', '')
    estados_validos = {valor for valor, _ in Obligacion.Estado.choices}
    if estado not in estados_validos:
        messages.error(request, 'Selecciona un estado válido.')
        return _volver(request)

    obligacion = tarea.obligacion
    estado_anterior = obligacion.estado
    obligacion.estado = estado
    if estado == Obligacion.Estado.COMPLETADA:
        obligacion.completada_por = request.user
        obligacion.completada_en = timezone.now()
    else:
        obligacion.completada_por = None
        obligacion.completada_en = None
    obligacion.save(update_fields=('estado', 'completada_por', 'completada_en', 'actualizada_en'))
    registrar_historial(
        cliente=tarea.cliente,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.TAREA,
        seccion=EntradaHistorial.Seccion.TAREAS,
        referencia=tarea.titulo,
        titulo=f'Estado de tarea actualizado: {tarea.titulo}',
        descripcion=f'Estado: {obligacion.get_estado_display()}',
    )
    if estado == Obligacion.Estado.COMPLETADA and estado_anterior != Obligacion.Estado.COMPLETADA:
        responsables = get_user_model().objects.filter(is_active=True).filter(
            Q(is_superuser=True)
            | Q(perfil__rol__in=(PerfilUsuario.Rol.ADMINISTRADOR, PerfilUsuario.Rol.SECRETARIO))
        ).exclude(pk=request.user.pk).distinct()
        url = f"{reverse('tareas:index')}?{urlencode({'q': tarea.cliente.nombre})}"
        Notificacion.objects.bulk_create([
            Notificacion(
                destinatario=destinatario,
                actor=request.user,
                tipo=Notificacion.Tipo.TAREA_COMPLETADA,
                titulo='Tarea completada',
                mensaje=f'{tarea.titulo} · {tarea.cliente.nombre}',
                url=url,
            )
            for destinatario in responsables
        ])
    messages.success(request, f'Se actualizó el estado de {tarea.titulo}.')
    return _volver(request)


@login_required
@require_POST
def subir_evidencia(request, tarea_id):
    tarea = get_object_or_404(_tareas_visibles(request.user), pk=tarea_id)
    archivo = request.FILES.get('evidencia')
    if not archivo:
        messages.error(request, 'Selecciona un archivo de evidencia.')
        return _volver(request)

    archivo_anterior = tarea.evidencia.name if tarea.evidencia else ''
    usuario_anterior = tarea.evidencia_subida_por
    tarea.evidencia = archivo
    tarea.evidencia_subida_por = request.user
    try:
        tarea.full_clean()
    except ValidationError as error:
        tarea.evidencia = archivo_anterior
        tarea.evidencia_subida_por = usuario_anterior
        messages.error(request, ' '.join(error.messages))
        return _volver(request)

    tarea.save(update_fields=('evidencia', 'evidencia_subida_por', 'actualizada_en'))
    registrar_historial(
        cliente=tarea.cliente,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.DOCUMENTO,
        seccion=EntradaHistorial.Seccion.DOCUMENTOS,
        referencia=tarea.titulo,
        titulo=f'Evidencia agregada a tarea: {tarea.titulo}',
        descripcion=tarea.evidencia_nombre,
    )
    if archivo_anterior and archivo_anterior != tarea.evidencia.name:
        tarea.evidencia.storage.delete(archivo_anterior)
    messages.success(request, 'Se guardó la evidencia de la tarea.')
    return _volver(request)


@login_required
def descargar_evidencia(request, tarea_id):
    tarea = get_object_or_404(_tareas_visibles(request.user), pk=tarea_id)
    if not tarea.evidencia:
        messages.error(request, 'Esta tarea todavía no tiene evidencia.')
        return redirect('tareas:index')
    archivo = tarea.evidencia.open('rb')
    content_type, _ = mimetypes.guess_type(tarea.evidencia.name)
    return FileResponse(
        archivo,
        as_attachment=True,
        filename=tarea.evidencia_nombre,
        content_type=content_type or 'application/octet-stream',
    )


@login_required
@require_POST
def eliminar_evidencia(request, tarea_id):
    tarea = get_object_or_404(_tareas_visibles(request.user), pk=tarea_id)
    if tarea.evidencia:
        nombre_evidencia = tarea.evidencia_nombre
        tarea.evidencia.delete(save=False)
        tarea.evidencia_subida_por = None
        tarea.save(update_fields=('evidencia', 'evidencia_subida_por', 'actualizada_en'))
        registrar_historial(
            cliente=tarea.cliente,
            usuario=request.user,
            tipo_accion=EntradaHistorial.TipoAccion.DOCUMENTO,
            seccion=EntradaHistorial.Seccion.DOCUMENTOS,
            referencia=tarea.titulo,
            titulo=f'Evidencia eliminada de tarea: {tarea.titulo}',
            descripcion=nombre_evidencia,
        )
        messages.success(request, 'Se eliminó la evidencia de la tarea.')
    return _volver(request)
