from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import ArchivoRequerimiento, ComentarioRequerimiento, Requerimiento


MAX_ARCHIVO_BYTES = 10 * 1024 * 1024
EXTENSIONES_PERMITIDAS = {'.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.xls', '.xlsx'}


def _archivos_validos(archivos):
	for archivo in archivos:
		if archivo.size > MAX_ARCHIVO_BYTES:
			return 'Cada archivo debe pesar como máximo 10 MB.'
		if Path(archivo.name).suffix.lower() not in EXTENSIONES_PERMITIDAS:
			return 'Tipo de archivo no permitido. Usa PDF, imágenes o documentos de Office.'
	return ''


def _adjuntar_archivos(requerimiento, archivos, usuario):
	for archivo in archivos:
		adjunto = ArchivoRequerimiento(
			requerimiento=requerimiento,
			archivo=archivo,
			nombre=Path(archivo.name).name[:255],
			subido_por=usuario,
		)
		adjunto.full_clean()
		adjunto.save()


@login_required
@require_GET
def index(request):
	query = request.GET.get('q', '').strip()
	estado = request.GET.get('estado', '').strip()
	prioridad = request.GET.get('prioridad', '').strip()
	responsable_id = request.GET.get('responsable', '').strip()
	items = Requerimiento.objects.select_related('cliente', 'responsable', 'creado_por').prefetch_related(
		'comentarios__autor', 'archivos',
	)
	if query:
		items = items.filter(
			Q(titulo__icontains=query)
			| Q(descripcion__icontains=query)
			| Q(cliente__nombre__icontains=query)
			| Q(cliente__razon_social__icontains=query)
		)
	if estado in {value for value, _ in Requerimiento.Estado.choices}:
		items = items.filter(estado=estado)
	if prioridad in {value for value, _ in Requerimiento.Prioridad.choices}:
		items = items.filter(prioridad=prioridad)
	if responsable_id.isdigit():
		items = items.filter(responsable_id=int(responsable_id))
	paginator = Paginator(items, 20)
	page_obj = paginator.get_page(request.GET.get('page'))
	query_params = request.GET.copy()
	query_params.pop('page', None)
	User = get_user_model()
	return render(request, 'requerimientos/requerimientos.html', {
		'titulo_modulo': 'Requerimientos',
		'descripcion_modulo': 'Solicitudes de clientes, responsables, prioridades y seguimiento.',
		'modulo_activo': 'requerimientos',
		'requerimientos': page_obj.object_list,
		'page_obj': page_obj,
		'query_string': query_params.urlencode(),
		'busqueda': query,
		'estado_filtro': estado,
		'prioridad_filtro': prioridad,
		'responsable_filtro': responsable_id,
		'estados': Requerimiento.Estado.choices,
		'prioridades': Requerimiento.Prioridad.choices,
		'clientes': Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre'),
		'usuarios': User.objects.filter(is_active=True).order_by('username'),
		'puede_gestionar': puede_gestionar_clientes(request.user),
		'usuario_id': request.user.pk,
		'hoy': timezone.localdate(),
		'total_requerimientos': paginator.count,
	})


@login_required
@require_POST
def crear(request):
	titulo = request.POST.get('titulo', '').strip()
	descripcion = request.POST.get('descripcion', '').strip()
	cliente_id = request.POST.get('cliente', '').strip()
	prioridad = request.POST.get('prioridad', Requerimiento.Prioridad.NORMAL)
	fecha_limite = parse_date(request.POST.get('fecha_limite', '').strip())
	archivos = request.FILES.getlist('archivos')
	cliente = Cliente.objects.filter(pk=cliente_id, estado=Cliente.Estado.ACTIVO).first() if cliente_id.isdigit() else None
	if not cliente or not titulo or len(titulo) > 180 or not descripcion:
		messages.error(request, 'Selecciona un cliente e ingresa un título y una descripción válidos.')
		return redirect('requerimientos:index')
	if prioridad not in {value for value, _ in Requerimiento.Prioridad.choices}:
		messages.error(request, 'Selecciona una prioridad válida.')
		return redirect('requerimientos:index')
	if request.POST.get('fecha_limite') and fecha_limite is None:
		messages.error(request, 'La fecha límite no es válida.')
		return redirect('requerimientos:index')
	error_archivos = _archivos_validos(archivos)
	if error_archivos:
		messages.error(request, error_archivos)
		return redirect('requerimientos:index')
	User = get_user_model()
	responsable = None
	if puede_gestionar_clientes(request.user):
		responsable_id = request.POST.get('responsable', '').strip()
		if responsable_id.isdigit():
			responsable = User.objects.filter(pk=int(responsable_id), is_active=True).first()
	else:
		responsable = request.user
	requerimiento = Requerimiento.objects.create(
		cliente=cliente,
		titulo=titulo,
		descripcion=descripcion,
		prioridad=prioridad,
		fecha_limite=fecha_limite,
		responsable=responsable,
		creado_por=request.user,
	)
	try:
		_adjuntar_archivos(requerimiento, archivos, request.user)
	except ValidationError:
		requerimiento.delete()
		messages.error(request, 'No se pudo guardar uno de los archivos adjuntos.')
		return redirect('requerimientos:index')
	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.TAREA,
		seccion=EntradaHistorial.Seccion.REQUERIMIENTOS,
		referencia=titulo,
		titulo=f'Requerimiento creado: {titulo}',
		descripcion=f'Prioridad: {requerimiento.get_prioridad_display()}',
	)
	messages.success(request, 'Requerimiento creado.')
	return redirect('requerimientos:index')


@login_required
@require_POST
def actualizar(request, requerimiento_id):
	requerimiento = get_object_or_404(Requerimiento, pk=requerimiento_id)
	puede_gestionar = puede_gestionar_clientes(request.user)
	if not puede_gestionar and requerimiento.responsable_id != request.user.pk:
		return HttpResponseForbidden('Solo el responsable asignado puede actualizar este requerimiento.')
	titulo = request.POST.get('titulo', requerimiento.titulo).strip()
	descripcion = request.POST.get('descripcion', requerimiento.descripcion).strip()
	if not titulo or len(titulo) > 180 or not descripcion:
		messages.error(request, 'El título y la descripción son obligatorios.')
		return redirect('requerimientos:index')
	estado_nuevo = request.POST.get('estado', requerimiento.estado)
	orden_estados = [Requerimiento.Estado.NUEVO, Requerimiento.Estado.EN_PROCESO, Requerimiento.Estado.TERMINADO]
	if (
		estado_nuevo not in orden_estados
		or orden_estados.index(estado_nuevo) < orden_estados.index(requerimiento.estado)
		or orden_estados.index(estado_nuevo) > orden_estados.index(requerimiento.estado) + 1
	):
		messages.error(request, 'El requerimiento debe avanzar en orden: Nuevo, En proceso y Terminado.')
		return redirect('requerimientos:index')
	prioridad = request.POST.get('prioridad', requerimiento.prioridad)
	if prioridad not in {value for value, _ in Requerimiento.Prioridad.choices}:
		messages.error(request, 'Selecciona una prioridad válida.')
		return redirect('requerimientos:index')
	fecha_texto = request.POST.get('fecha_limite', '').strip()
	fecha_limite = parse_date(fecha_texto) if fecha_texto else None
	if fecha_texto and fecha_limite is None:
		messages.error(request, 'La fecha límite no es válida.')
		return redirect('requerimientos:index')
	requerimiento.titulo = titulo
	requerimiento.descripcion = descripcion
	requerimiento.estado = estado_nuevo
	requerimiento.prioridad = prioridad
	requerimiento.fecha_limite = fecha_limite
	if puede_gestionar and 'responsable' in request.POST:
		responsable_id = request.POST.get('responsable', '').strip()
		if responsable_id:
			User = get_user_model()
			requerimiento.responsable = User.objects.filter(pk=responsable_id, is_active=True).first()
		else:
			requerimiento.responsable = None
	if estado_nuevo == Requerimiento.Estado.TERMINADO and requerimiento.terminado_en is None:
		requerimiento.terminado_en = timezone.now()
	requerimiento.save()
	registrar_historial(
		cliente=requerimiento.cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.TAREA,
		seccion=EntradaHistorial.Seccion.REQUERIMIENTOS,
		referencia=requerimiento.titulo,
		titulo=f'Requerimiento actualizado: {requerimiento.titulo}',
		descripcion=f'Estado: {requerimiento.get_estado_display()} · Prioridad: {requerimiento.get_prioridad_display()}',
	)
	messages.success(request, 'Se actualizaron los datos del requerimiento.')
	return redirect('requerimientos:index')


@login_required
@require_POST
def eliminar(request, requerimiento_id):
	if not puede_gestionar_clientes(request.user):
		return HttpResponseForbidden('No tienes permiso para eliminar requerimientos.')
	requerimiento = get_object_or_404(Requerimiento, pk=requerimiento_id)
	titulo = requerimiento.titulo
	cliente = requerimiento.cliente
	for adjunto in requerimiento.archivos.all():
		adjunto.archivo.delete(save=False)
	requerimiento.delete()
	registrar_historial(
		cliente=cliente,
		usuario=request.user,
		tipo_accion=EntradaHistorial.TipoAccion.OTRO,
		seccion=EntradaHistorial.Seccion.REQUERIMIENTOS,
		referencia=titulo,
		titulo=f'Requerimiento eliminado: {titulo}',
	)
	messages.success(request, f'Se eliminó el requerimiento «{titulo}».')
	return redirect('requerimientos:index')


@login_required
@require_POST
def comentar(request, requerimiento_id):
	requerimiento = get_object_or_404(Requerimiento, pk=requerimiento_id)
	texto = request.POST.get('texto', '').strip()
	if not texto or len(texto) > 5000:
		messages.error(request, 'El comentario es obligatorio y no puede superar 5000 caracteres.')
	else:
		ComentarioRequerimiento.objects.create(requerimiento=requerimiento, autor=request.user, texto=texto)
		registrar_historial(
			cliente=requerimiento.cliente,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.TAREA,
			seccion=EntradaHistorial.Seccion.REQUERIMIENTOS,
			referencia=requerimiento.titulo,
			titulo=f'Comentario agregado a requerimiento: {requerimiento.titulo}',
			descripcion=texto[:500],
		)
		messages.success(request, 'Comentario agregado.')
	return redirect('requerimientos:index')


@login_required
@require_POST
def adjuntar(request, requerimiento_id):
	requerimiento = get_object_or_404(Requerimiento, pk=requerimiento_id)
	archivos = request.FILES.getlist('archivos')
	if not archivos:
		messages.error(request, 'Selecciona al menos un archivo.')
		return redirect('requerimientos:index')
	error_archivos = _archivos_validos(archivos)
	if error_archivos:
		messages.error(request, error_archivos)
		return redirect('requerimientos:index')
	try:
		_adjuntar_archivos(requerimiento, archivos, request.user)
	except ValidationError:
		messages.error(request, 'No se pudo guardar uno de los archivos adjuntos.')
	else:
		registrar_historial(
			cliente=requerimiento.cliente,
			usuario=request.user,
			tipo_accion=EntradaHistorial.TipoAccion.DOCUMENTO,
			seccion=EntradaHistorial.Seccion.DOCUMENTOS,
			referencia=requerimiento.titulo,
			titulo=f'Archivo adjuntado a requerimiento: {requerimiento.titulo}',
			descripcion=', '.join(Path(archivo.name).name for archivo in archivos),
		)
		messages.success(request, 'Archivo(s) adjuntado(s).')
	return redirect('requerimientos:index')


@login_required
@require_GET
def descargar_archivo(request, archivo_id):
	adjunto = get_object_or_404(ArchivoRequerimiento, pk=archivo_id)
	return FileResponse(adjunto.archivo.open('rb'), as_attachment=True, filename=adjunto.nombre)