from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from apps.clientes.permissions import puede_gestionar_clientes, solo_gestores_clientes
from apps.historial.models import EntradaHistorial
from apps.historial.services import registrar_historial

from .models import ClienteOcasional, PagoServicioTramite, ServicioTramite


def _leer_importe(valor, permitir_cero=False):
    try:
        importe = Decimal(valor or '0')
        if not importe.is_finite() or importe < 0 or (not permitir_cero and importe == 0):
            return None
        if importe.as_tuple().exponent < -2 or importe >= Decimal('10000000000'):
            return None
        return importe
    except (InvalidOperation, TypeError, ValueError):
        return None


@login_required
@require_GET
def index(request):
    hoy = timezone.localdate()
    busqueda = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()
    pago_filtro = request.GET.get('pago', '').strip()
    tipo_filtro = request.GET.get('tipo', '').strip()
    servicios = ServicioTramite.objects.select_related('cliente', 'responsable', 'registrado_por').prefetch_related(
        'pagos',
    ).annotate(monto_abonado=Sum('pagos__monto'))
    if busqueda:
        servicios = servicios.filter(
            Q(concepto__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__documento__icontains=busqueda)
            | Q(cliente__telefono__icontains=busqueda)
        )
    if estado_filtro in {value for value, _ in ServicioTramite.Estado.choices}:
        servicios = servicios.filter(estado=estado_filtro)
    if tipo_filtro in {value for value, _ in ServicioTramite.Tipo.choices}:
        servicios = servicios.filter(tipo=tipo_filtro)
    if pago_filtro == ServicioTramite.EstadoCobro.PENDIENTE:
        servicios = servicios.filter(Q(monto_abonado__isnull=True) | Q(monto_abonado=0))
    elif pago_filtro == ServicioTramite.EstadoCobro.PARCIAL:
        servicios = servicios.filter(monto_abonado__gt=0, monto_abonado__lt=F('monto_total'))
    elif pago_filtro == ServicioTramite.EstadoCobro.PAGADO:
        servicios = servicios.filter(monto_abonado__gte=F('monto_total'))
    servicios = servicios.order_by('-fecha_solicitud', '-pk')
    servicios_page = Paginator(servicios, 20).get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)

    servicios_activos = ServicioTramite.objects.exclude(estado=ServicioTramite.Estado.ENTREGADO)
    pendientes = ServicioTramite.objects.prefetch_related('pagos').all()
    total_pendiente = sum((item.saldo_pendiente for item in pendientes), Decimal('0.00'))
    total_cobrado = PagoServicioTramite.objects.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    cobrado_mes = PagoServicioTramite.objects.filter(
        fecha_pago__year=hoy.year,
        fecha_pago__month=hoy.month,
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    User = get_user_model()
    return render(request, 'servicios/servicios.html', {
        'titulo_modulo': 'Servicios y trámites',
        'descripcion_modulo': 'Trabajos puntuales para clientes ocasionales, anticipos y saldos por cobrar.',
        'modulo_activo': 'servicios',
        'hoy': hoy,
        'servicios': servicios_page.object_list,
        'page_obj': servicios_page,
        'query_string': query_params.urlencode(),
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'pago_filtro': pago_filtro,
        'tipo_filtro': tipo_filtro,
        'estados': ServicioTramite.Estado.choices,
        'estados_cobro': ServicioTramite.EstadoCobro.choices,
        'tipos': ServicioTramite.Tipo.choices,
        'prioridades': ServicioTramite.Prioridad.choices,
        'metodos_pago': PagoServicioTramite.MetodoPago.choices,
        'clientes_ocasionales': ClienteOcasional.objects.order_by('nombre', 'pk'),
        'usuarios': User.objects.filter(is_active=True).order_by('username'),
        'puede_gestionar': puede_gestionar_clientes(request.user),
        'usuario_id': request.user.pk,
        'total_servicios': servicios_page.paginator.count,
        'total_activos': servicios_activos.count(),
        'total_pendiente': total_pendiente,
        'total_cobrado': total_cobrado,
        'cobrado_mes': cobrado_mes,
    })


@solo_gestores_clientes
@require_POST
def crear(request):
    cliente_id = request.POST.get('cliente_id', '').strip()
    tipo = request.POST.get('tipo', ServicioTramite.Tipo.TRAMITE)
    concepto = request.POST.get('concepto', '').strip()
    descripcion = request.POST.get('descripcion', '').strip()
    prioridad = request.POST.get('prioridad', ServicioTramite.Prioridad.NORMAL)
    fecha_limite = parse_date(request.POST.get('fecha_limite', '').strip())
    monto_total = _leer_importe(request.POST.get('monto_total'))
    pago_inicial = _leer_importe(request.POST.get('pago_inicial'), permitir_cero=True)
    metodo_pago = request.POST.get('metodo_pago', PagoServicioTramite.MetodoPago.EFECTIVO)
    responsable_id = request.POST.get('responsable', '').strip()
    nombre = request.POST.get('nombre_cliente', '').strip()
    if tipo not in {value for value, _ in ServicioTramite.Tipo.choices}:
        messages.error(request, 'Selecciona un tipo de servicio válido.')
        return redirect('servicios:index')
    if prioridad not in {value for value, _ in ServicioTramite.Prioridad.choices}:
        messages.error(request, 'Selecciona una prioridad válida.')
        return redirect('servicios:index')
    if not concepto or len(concepto) > 180 or monto_total is None or pago_inicial is None:
        messages.error(request, 'Completa el concepto e ingresa montos válidos.')
        return redirect('servicios:index')
    if pago_inicial > monto_total:
        messages.error(request, 'El anticipo no puede superar el precio total del trabajo.')
        return redirect('servicios:index')
    if request.POST.get('fecha_limite') and fecha_limite is None:
        messages.error(request, 'La fecha límite no es válida.')
        return redirect('servicios:index')
    if pago_inicial > 0 and metodo_pago not in {value for value, _ in PagoServicioTramite.MetodoPago.choices}:
        messages.error(request, 'Selecciona una forma de pago válida para el anticipo.')
        return redirect('servicios:index')
    User = get_user_model()
    responsable = User.objects.filter(pk=responsable_id, is_active=True).first() if responsable_id.isdigit() else None
    if responsable_id and responsable is None:
        messages.error(request, 'El responsable seleccionado no es válido.')
        return redirect('servicios:index')
    with transaction.atomic():
        if cliente_id == 'nuevo':
            if not nombre or len(nombre) > 180:
                messages.error(request, 'Ingresa el nombre del cliente ocasional.')
                return redirect('servicios:index')
            cliente = ClienteOcasional(
                nombre=nombre,
                documento=request.POST.get('documento_cliente', '').strip()[:30],
                telefono=request.POST.get('telefono_cliente', '').strip()[:30],
                correo=request.POST.get('correo_cliente', '').strip(),
                direccion=request.POST.get('direccion_cliente', '').strip()[:240],
                creado_por=request.user,
            )
            try:
                cliente.full_clean()
            except ValidationError:
                messages.error(request, 'Revisa el correo y los datos del cliente ocasional.')
                return redirect('servicios:index')
            cliente.save()
        else:
            cliente = ClienteOcasional.objects.filter(pk=cliente_id).first() if cliente_id.isdigit() else None
            if cliente is None:
                messages.error(request, 'Selecciona un cliente ocasional válido.')
                return redirect('servicios:index')
        servicio = ServicioTramite.objects.create(
            cliente=cliente,
            tipo=tipo,
            concepto=concepto,
            descripcion=descripcion,
            prioridad=prioridad,
            fecha_limite=fecha_limite,
            monto_total=monto_total,
            responsable=responsable,
            observaciones=request.POST.get('observaciones', '').strip(),
            registrado_por=request.user,
        )
        if pago_inicial > 0:
            PagoServicioTramite.objects.create(
                servicio=servicio,
                monto=pago_inicial,
                fecha_pago=timezone.localdate(),
                metodo_pago=metodo_pago,
                numero_recibo=request.POST.get('recibo_inicial', '').strip()[:60],
                observaciones='Anticipo recibido al registrar el servicio.',
                registrado_por=request.user,
            )
    registrar_historial(
        cliente=None,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.CREACION,
        seccion=EntradaHistorial.Seccion.SERVICIOS,
        referencia=f'{cliente.nombre} · {servicio.concepto}',
        titulo=f'Servicio ocasional registrado: {servicio.concepto}',
        descripcion=(
            f'Cliente: {cliente.nombre} · Precio: Bs {monto_total:.2f} · '
            f'Anticipo: Bs {pago_inicial:.2f} · Saldo: Bs {servicio.saldo_pendiente:.2f}'
        ),
    )
    messages.success(request, f'Se registró «{concepto}» para {cliente.nombre}.')
    return redirect('servicios:index')


@login_required
@require_POST
def actualizar(request, servicio_id):
    servicio = get_object_or_404(ServicioTramite, pk=servicio_id)
    puede_gestionar = puede_gestionar_clientes(request.user)
    if not puede_gestionar and servicio.responsable_id != request.user.pk:
        return redirect('servicios:index')
    concepto = request.POST.get('concepto', servicio.concepto).strip()
    descripcion = request.POST.get('descripcion', servicio.descripcion).strip()
    tipo = request.POST.get('tipo', servicio.tipo)
    estado = request.POST.get('estado', servicio.estado)
    prioridad = request.POST.get('prioridad', servicio.prioridad)
    fecha_texto = request.POST.get('fecha_limite', '').strip()
    fecha_limite = parse_date(fecha_texto) if fecha_texto else None
    if not concepto or len(concepto) > 180 or tipo not in {value for value, _ in ServicioTramite.Tipo.choices}:
        messages.error(request, 'El concepto o tipo de trabajo no es válido.')
        return redirect('servicios:index')
    if estado not in {value for value, _ in ServicioTramite.Estado.choices}:
        messages.error(request, 'Selecciona un estado válido.')
        return redirect('servicios:index')
    if prioridad not in {value for value, _ in ServicioTramite.Prioridad.choices}:
        messages.error(request, 'Selecciona una prioridad válida.')
        return redirect('servicios:index')
    if fecha_texto and fecha_limite is None:
        messages.error(request, 'La fecha límite no es válida.')
        return redirect('servicios:index')
    if puede_gestionar:
        monto_total = _leer_importe(request.POST.get('monto_total'))
        if monto_total is None or monto_total < servicio.total_pagado:
            messages.error(request, 'El precio no puede ser menor a los pagos ya recibidos.')
            return redirect('servicios:index')
        servicio.monto_total = monto_total
        responsable_id = request.POST.get('responsable', '').strip()
        if responsable_id:
            User = get_user_model()
            responsable = User.objects.filter(pk=responsable_id, is_active=True).first()
            if responsable is None:
                messages.error(request, 'El responsable seleccionado no es válido.')
                return redirect('servicios:index')
            servicio.responsable = responsable
        else:
            servicio.responsable = None
    servicio.concepto = concepto
    servicio.descripcion = descripcion
    servicio.tipo = tipo
    servicio.estado = estado
    servicio.prioridad = prioridad
    servicio.fecha_limite = fecha_limite
    servicio.fecha_entrega = timezone.localdate() if estado == ServicioTramite.Estado.ENTREGADO else None
    servicio.observaciones = request.POST.get('observaciones', servicio.observaciones).strip()
    servicio.save()
    registrar_historial(
        cliente=None,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
        seccion=EntradaHistorial.Seccion.SERVICIOS,
        referencia=f'{servicio.cliente.nombre} · {servicio.concepto}',
        titulo=f'Servicio ocasional actualizado: {servicio.concepto}',
        descripcion=f'Estado: {servicio.get_estado_display()} · Saldo: Bs {servicio.saldo_pendiente:.2f}',
    )
    messages.success(request, f'Se actualizaron los datos de «{servicio.concepto}».')
    return redirect('servicios:index')


@solo_gestores_clientes
@require_POST
def registrar_pago(request, servicio_id):
    importe = _leer_importe(request.POST.get('monto'))
    fecha = parse_date(request.POST.get('fecha_pago', '').strip())
    metodo = request.POST.get('metodo_pago', PagoServicioTramite.MetodoPago.EFECTIVO)
    if importe is None or fecha is None or metodo not in {value for value, _ in PagoServicioTramite.MetodoPago.choices}:
        messages.error(request, 'Ingresa un monto, fecha y forma de pago válidos.')
        return redirect('servicios:index')
    with transaction.atomic():
        servicio = get_object_or_404(ServicioTramite.objects.select_for_update(), pk=servicio_id)
        saldo = servicio.saldo_pendiente
        if saldo <= 0:
            messages.error(request, 'Este trabajo ya está completamente pagado.')
            return redirect('servicios:index')
        if importe > saldo:
            messages.error(request, f'El pago supera el saldo pendiente de Bs {saldo:.2f}.')
            return redirect('servicios:index')
        pago = PagoServicioTramite.objects.create(
            servicio=servicio,
            monto=importe,
            fecha_pago=fecha,
            metodo_pago=metodo,
            numero_recibo=request.POST.get('numero_recibo', '').strip()[:60],
            observaciones=request.POST.get('observaciones', '').strip(),
            registrado_por=request.user,
        )
        registrar_historial(
            cliente=None,
            usuario=request.user,
            tipo_accion=EntradaHistorial.TipoAccion.PAGO,
            seccion=EntradaHistorial.Seccion.SERVICIOS,
            referencia=f'{servicio.cliente.nombre} · {servicio.concepto}',
            titulo=f'Pago de trámite recibido: Bs {pago.monto:.2f}',
            descripcion=f'Cliente: {servicio.cliente.nombre} · Saldo pendiente: Bs {servicio.saldo_pendiente:.2f}',
        )
    messages.success(request, f'Se registró un pago de Bs {importe:.2f}.')
    return redirect('servicios:index')


@solo_gestores_clientes
@require_POST
def eliminar(request, servicio_id):
    servicio = get_object_or_404(ServicioTramite, pk=servicio_id)
    if servicio.pagos.exists():
        messages.error(request, 'No se puede eliminar un servicio con pagos registrados; conserva su historial financiero.')
        return redirect('servicios:index')
    concepto = servicio.concepto
    registrar_historial(
        cliente=None,
        usuario=request.user,
        tipo_accion=EntradaHistorial.TipoAccion.OTRO,
        seccion=EntradaHistorial.Seccion.SERVICIOS,
        referencia=f'{servicio.cliente.nombre} · {concepto}',
        titulo=f'Servicio ocasional eliminado: {concepto}',
    )
    servicio.delete()
    messages.success(request, f'Se eliminó el servicio «{concepto}».')
    return redirect('servicios:index')
