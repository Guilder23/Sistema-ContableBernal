from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from urllib.parse import urlencode
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes
from apps.tareas.models import Tarea

from .models import ConfiguracionCliente, DiaNoLaborable, Obligacion, TipoObligacion
from .services import generar_obligaciones


MESES = (
    (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
)


def _redirigir_cliente(cliente_id, volver=''):
    if volver:
        return redirect(volver)
    if cliente_id:
        return redirect(f'{reverse("obligaciones:index")}?config_cliente={cliente_id}')
    return redirect('obligaciones:index')


def _url_periodo_cliente(cliente_id, periodicidad, anio, numero, volver=''):
    if volver:
        return redirect(volver)
    return f'{reverse("obligaciones:index")}?{urlencode({"config_cliente": cliente_id})}'



@login_required
def index(request):
    hoy = timezone.localdate()
    periodicidad = request.GET.get('periodicidad', '')
    periodicidades_validas = {valor for valor, _ in TipoObligacion.Periodicidad.choices}
    if periodicidad not in periodicidades_validas:
        periodicidad = ''

    anio = ''
    try:
        if request.GET.get('anio', '').strip():
            anio = int(request.GET['anio'])
        if anio and not 2000 <= anio <= 2200:
            raise ValueError
    except (TypeError, ValueError):
        anio = ''

    numero = ''
    try:
        numero_raw = request.GET.get('periodo_numero', '').strip()
        if numero_raw:
            numero = int(numero_raw)
    except (TypeError, ValueError):
        numero = ''
    maximo = 12 if periodicidad == TipoObligacion.Periodicidad.MENSUAL else (
        4 if periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL else 0
    )
    if periodicidad in (TipoObligacion.Periodicidad.MENSUAL, TipoObligacion.Periodicidad.TRIMESTRAL):
        if numero != '' and not 1 <= numero <= maximo:
            numero = ''
    else:
        numero = ''

    obligaciones = Obligacion.objects.select_related('cliente', 'tipo', 'completada_por').all()
    if periodicidad:
        obligaciones = obligaciones.filter(tipo__periodicidad=periodicidad)
    if anio:
        obligaciones = obligaciones.filter(anio=anio)
    if numero != '':
        obligaciones = obligaciones.filter(periodo_numero=numero)
    cliente_filtro = request.GET.get('cliente', '')
    if cliente_filtro.isdigit():
        obligaciones = obligaciones.filter(cliente_id=int(cliente_filtro))
    estado_filtro = request.GET.get('estado', '')
    estados_validos = {valor for valor, _ in Obligacion.Estado.choices}
    if estado_filtro in estados_validos:
        obligaciones = obligaciones.filter(estado=estado_filtro)

    query_params = request.GET.copy()
    query_params.pop('pagina', None)
    pagina = Paginator(obligaciones, 40).get_page(request.GET.get('pagina'))

    config_cliente_id = request.GET.get('config_cliente', '')
    cliente_config = Cliente.objects.filter(pk=config_cliente_id, estado=Cliente.Estado.ACTIVO).first() if config_cliente_id.isdigit() else None
    configuraciones_ids = set()
    if cliente_config:
        configuraciones_ids = set(
            ConfiguracionCliente.objects.filter(cliente=cliente_config, activa=True).values_list('tipo_id', flat=True)
        )

    return render(request, 'obligaciones/obligaciones.html', {
        'titulo_modulo': 'Obligaciones',
        'descripcion_modulo': 'Configura, genera y controla los vencimientos de cada cliente.',
        'modulo_activo': 'obligaciones',
        'obligaciones': pagina.object_list,
        'page_obj': pagina,
        'query_string': query_params.urlencode(),
        'clientes': Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre'),
        'tipos': TipoObligacion.objects.filter(activa=True),
        'tipos_catalogo': TipoObligacion.objects.all(),
        'reglas_vencimiento': TipoObligacion.ReglaVencimiento.choices,
        'dias_no_laborables': DiaNoLaborable.objects.order_by('-fecha')[:30],
        'periodicidades': TipoObligacion.Periodicidad.choices,
        'estados': Obligacion.Estado.choices,
        'meses': MESES,
        'periodo_options': ((('', 'Todos'),) + MESES) if periodicidad == TipoObligacion.Periodicidad.MENSUAL else (
            (('', 'Todos'), (1, 'Primer trimestre'), (2, 'Segundo trimestre'), (3, 'Tercer trimestre'), (4, 'Cuarto trimestre'))
            if periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL else (('', 'Todos'),)
        ),
        'periodicidad': periodicidad,
        'anio': anio,
        'periodo_numero': numero,
        'generacion_periodicidad': TipoObligacion.Periodicidad.MENSUAL,
        'generacion_anio': hoy.year,
        'generacion_numero': hoy.month,
        'generacion_periodos': MESES,
        'cliente_filtro': cliente_filtro,
        'estado_filtro': estado_filtro,
        'cliente_config': cliente_config,
        'configuraciones_ids': configuraciones_ids,
        'puede_gestionar': puede_gestionar_clientes(request.user),
        'hoy': hoy,
        'total_periodo': obligaciones.count(),
        'pendientes_periodo': obligaciones.filter(estado=Obligacion.Estado.PENDIENTE).count(),
        'vencidas_periodo': obligaciones.filter(
            estado__in=(Obligacion.Estado.PENDIENTE, Obligacion.Estado.EN_PROCESO),
            fecha_vencimiento__lt=hoy,
        ).count(),
    })


@solo_gestores_clientes
@require_POST
def configurar_cliente(request):
    cliente_id = request.POST.get('cliente_id', '')
    volver = request.POST.get('volver', '')
    cliente = get_object_or_404(Cliente, pk=cliente_id, estado=Cliente.Estado.ACTIVO)
    tipo_ids = set(request.POST.getlist('tipos'))
    tipos = list(TipoObligacion.objects.filter(pk__in=tipo_ids, activa=True))
    if len(tipos) != len(tipo_ids):
        messages.error(request, 'La selección contiene tipos de obligación no válidos.')
        return _redirigir_cliente(cliente.pk, volver)

    fecha_inicio = parse_date(request.POST.get('fecha_inicio', ''))
    with transaction.atomic():
        ConfiguracionCliente.objects.filter(cliente=cliente).update(activa=False)
        for tipo in tipos:
            configuracion, creada = ConfiguracionCliente.objects.get_or_create(
                cliente=cliente,
                tipo=tipo,
                defaults={'fecha_inicio': fecha_inicio or cliente.fecha_inicio or timezone.localdate(), 'activa': True},
            )
            if not creada:
                configuracion.activa = True
                if fecha_inicio:
                    configuracion.fecha_inicio = fecha_inicio
                configuracion.save(update_fields=('activa', 'fecha_inicio'))

    periodicidad = request.POST.get('periodicidad', TipoObligacion.Periodicidad.MENSUAL)
    hoy = timezone.localdate()
    try:
        anio = int(request.POST.get('anio', hoy.year))
        numero = int(request.POST.get(
            'periodo_numero',
            hoy.month if periodicidad == TipoObligacion.Periodicidad.MENSUAL else 0,
        ))
    except (TypeError, ValueError):
        messages.success(request, f'Se guardó la configuración de {cliente.nombre}.')
        messages.warning(request, 'La configuración se guardó, pero no se pudo generar el período seleccionado.')
        return _redirigir_cliente(cliente.pk, volver)

    maximo = 12 if periodicidad == TipoObligacion.Periodicidad.MENSUAL else (
        4 if periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL else 0
    )
    periodo_valido = (
        periodicidad in {valor for valor, _ in TipoObligacion.Periodicidad.choices}
        and 2000 <= anio <= 2200
        and ((1 <= numero <= maximo) if maximo else numero == 0)
    )
    if not periodo_valido:
        messages.success(request, f'Se guardó la configuración de {cliente.nombre}.')
        messages.warning(request, 'La configuración se guardó, pero el período seleccionado no es válido.')
        return _redirigir_cliente(cliente.pk, volver)

    resultado = generar_obligaciones(periodicidad, anio, numero, cliente_id=cliente.pk, usuario=request.user)
    mensaje = (
        f"Se guardó la configuración de {cliente.nombre}: "
        f"{resultado['creadas']} obligaciones generadas y "
        f"{resultado['cobros_creados']} cuentas por cobrar creadas para el período; "
        f"{resultado['existentes']} ya existían."
    )
    if resultado['sin_vigencia']:
        mensaje += f" {resultado['sin_vigencia']} se omitieron porque su fecha de inicio es posterior al período."
    if resultado['errores']:
        messages.warning(request, mensaje)
        for error in resultado['errores'][:3]:
            messages.error(request, error)
    else:
        messages.success(request, mensaje)
    return redirect(_url_periodo_cliente(cliente.pk, periodicidad, anio, numero, volver))



@solo_gestores_clientes
@require_POST
def generar(request):
    periodicidad = request.POST.get('periodicidad', '')
    periodicidades_validas = {valor for valor, _ in TipoObligacion.Periodicidad.choices}
    try:
        anio = int(request.POST.get('anio', ''))
        numero = int(request.POST.get('periodo_numero', '0'))
    except (TypeError, ValueError):
        messages.error(request, 'Ingresa un año y período válidos.')
        return redirect('obligaciones:index')

    maximo = 12 if periodicidad == TipoObligacion.Periodicidad.MENSUAL else (
        4 if periodicidad == TipoObligacion.Periodicidad.TRIMESTRAL else 0
    )
    if periodicidad not in periodicidades_validas or not 2000 <= anio <= 2200 or (maximo and not 1 <= numero <= maximo) or (not maximo and numero != 0):
        messages.error(request, 'Selecciona una periodicidad y un período válidos.')
        return redirect('obligaciones:index')

    resultado = generar_obligaciones(periodicidad, anio, numero, usuario=request.user)
    texto = (
        f"Se generaron {resultado['creadas']} obligaciones y "
        f"{resultado['cobros_creados']} cuentas por cobrar; {resultado['existentes']} obligaciones ya existían."
    )
    if resultado['sin_vigencia']:
        texto += f" {resultado['sin_vigencia']} se omitieron porque su fecha de inicio es posterior al período."
    if resultado['errores']:
        texto += f" No se generaron {len(resultado['errores'])} por falta de datos o configuración."
        messages.warning(request, texto)
        for error in resultado['errores'][:3]:
            messages.error(request, error)
    else:
        messages.success(request, texto)
    return redirect('obligaciones:index')


@login_required
@require_POST
def actualizar_estado(request, obligacion_id):
    obligacion = get_object_or_404(Obligacion, pk=obligacion_id)
    if not puede_gestionar_clientes(request.user) and not Tarea.objects.filter(
        obligacion=obligacion,
        responsable=request.user,
    ).exists():
        return HttpResponseForbidden('Solo el responsable asignado puede cambiar el estado de esta tarea.')
    estado = request.POST.get('estado', '')
    estados_validos = {valor for valor, _ in Obligacion.Estado.choices}
    if estado not in estados_validos:
        messages.error(request, 'Selecciona un estado válido.')
        return redirect('obligaciones:index')

    obligacion.estado = estado
    if estado == Obligacion.Estado.COMPLETADA:
        obligacion.completada_por = request.user
        obligacion.completada_en = timezone.now()
    else:
        obligacion.completada_por = None
        obligacion.completada_en = None
    obligacion.save(update_fields=('estado', 'completada_por', 'completada_en', 'actualizada_en'))
    messages.success(request, 'Se actualizó el estado de la obligación.')
    return redirect('obligaciones:index')


@solo_gestores_clientes
@require_POST
def actualizar_vencimiento(request, obligacion_id):
    obligacion = get_object_or_404(Obligacion, pk=obligacion_id)
    fecha_vencimiento = parse_date(request.POST.get('fecha_vencimiento', ''))
    if fecha_vencimiento is None:
        messages.error(request, 'Ingresa una fecha de vencimiento válida.')
    else:
        obligacion.fecha_vencimiento = fecha_vencimiento
        obligacion.save(update_fields=('fecha_vencimiento', 'actualizada_en'))
        messages.success(request, 'Se guardó la fecha de vencimiento.')
    return redirect('obligaciones:index')


def _guardar_tipo(request, tipo=None):
    nombre = request.POST.get('nombre', '').strip()
    periodicidad = request.POST.get('periodicidad', '')
    regla = request.POST.get('regla_vencimiento', TipoObligacion.ReglaVencimiento.MANUAL)
    codigo = request.POST.get('codigo', '').strip() or (tipo.codigo if tipo else slugify(nombre))
    codigo = slugify(codigo)[:40]
    periodicidades_validas = {valor for valor, _ in TipoObligacion.Periodicidad.choices}
    reglas_validas = {valor for valor, _ in TipoObligacion.ReglaVencimiento.choices}

    try:
        dia = int(request.POST.get('dia_vencimiento', '')) if request.POST.get('dia_vencimiento', '').strip() else None
        meses_despues = int(request.POST.get('meses_despues_periodo', '1'))
    except (TypeError, ValueError):
        messages.error(request, 'El día y los meses de desplazamiento deben ser números válidos.')
        return redirect('obligaciones:index')

    if not nombre or len(nombre) > 100 or not codigo:
        messages.error(request, 'El nombre del tipo es obligatorio y debe generar un código válido.')
        return redirect('obligaciones:index')
    if periodicidad not in periodicidades_validas or regla not in reglas_validas:
        messages.error(request, 'Selecciona una periodicidad y una regla válidas.')
        return redirect('obligaciones:index')
    if not 0 <= meses_despues <= 12:
        messages.error(request, 'El desplazamiento debe estar entre 0 y 12 meses.')
        return redirect('obligaciones:index')

    tipo = tipo or TipoObligacion()
    tipo.codigo = codigo
    tipo.nombre = nombre
    tipo.periodicidad = periodicidad
    tipo.regla_vencimiento = regla
    tipo.dia_vencimiento = dia if regla == TipoObligacion.ReglaVencimiento.DIA_FIJO else None
    tipo.meses_despues_periodo = meses_despues
    tipo.activa = request.POST.get('activa') == 'on'
    try:
        tipo.full_clean()
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect('obligaciones:index')
    tipo.save()
    messages.success(request, f'Se guardó el tipo de obligación {tipo.nombre}.')
    return redirect('obligaciones:index')


@solo_gestores_clientes
@require_POST
def crear_tipo(request):
    return _guardar_tipo(request)


@solo_gestores_clientes
@require_POST
def editar_tipo(request, tipo_id):
    tipo = get_object_or_404(TipoObligacion, pk=tipo_id)
    return _guardar_tipo(request, tipo)


@solo_gestores_clientes
@require_POST
def crear_dia_no_laborable(request):
    fecha = parse_date(request.POST.get('fecha', ''))
    descripcion = request.POST.get('descripcion', '').strip()
    if fecha is None or not descripcion or len(descripcion) > 120:
        messages.error(request, 'Ingresa una fecha válida y una descripción de hasta 120 caracteres.')
        return redirect('obligaciones:index')
    _, creado = DiaNoLaborable.objects.get_or_create(fecha=fecha, defaults={'descripcion': descripcion})
    if creado:
        messages.success(request, f'Se registró el día no laborable {fecha:%d/%m/%Y}.')
    else:
        messages.warning(request, 'Ya existe un día no laborable con esa fecha.')
    return redirect('obligaciones:index')


@solo_gestores_clientes
@require_POST
def eliminar_dia_no_laborable(request, dia_id):
    dia = get_object_or_404(DiaNoLaborable, pk=dia_id)
    dia.delete()
    messages.success(request, 'Se eliminó el día no laborable.')
    return redirect('obligaciones:index')
