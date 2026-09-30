from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.clientes.models import Cliente
from apps.historial.models import EntradaHistorial


@login_required
def index(request):
	busqueda = request.GET.get('q', '').strip()
	tipo_accion = request.GET.get('tipo', '').strip()
	cliente_id = request.GET.get('cliente', '').strip()

	historial = EntradaHistorial.objects.select_related('cliente', 'usuario').all()

	if busqueda:
		historial = historial.filter(
			Q(cliente__nombre__icontains=busqueda)
			| Q(titulo__icontains=busqueda)
			| Q(descripcion__icontains=busqueda)
			| Q(usuario__username__icontains=busqueda)
		)
	if tipo_accion in {valor for valor, _ in EntradaHistorial.TipoAccion.choices}:
		historial = historial.filter(tipo_accion=tipo_accion)
	if cliente_id.isdigit():
		historial = historial.filter(cliente_id=int(cliente_id))

	paginador = Paginator(historial, 30)
	query_params = request.GET.copy()
	query_params.pop('page', None)
	page_obj = paginador.get_page(request.GET.get('page'))

	clientes = Cliente.objects.filter(estado=Cliente.Estado.ACTIVO).order_by('nombre')

	return render(request, 'historial/historial.html', {
		'historial': page_obj.object_list,
		'page_obj': page_obj,
		'total_entradas': paginador.count,
		'query_string': query_params.urlencode(),
		'busqueda': busqueda,
		'tipo_filtro': tipo_accion,
		'cliente_filtro': cliente_id,
		'tipos_accion': EntradaHistorial.TipoAccion.choices,
		'clientes': clientes,
	})
