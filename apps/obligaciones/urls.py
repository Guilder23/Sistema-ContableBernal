from django.urls import path

from . import views

app_name = 'obligaciones'

urlpatterns = [
	path('', views.index, name='index'),
	path('configurar-cliente/', views.configurar_cliente, name='configurar_cliente'),
	path('generar/', views.generar, name='generar'),
	path('catalogo/crear/', views.crear_tipo, name='crear_tipo'),
	path('catalogo/<int:tipo_id>/editar/', views.editar_tipo, name='editar_tipo'),
	path('feriados/crear/', views.crear_dia_no_laborable, name='crear_dia_no_laborable'),
	path('feriados/<int:dia_id>/eliminar/', views.eliminar_dia_no_laborable, name='eliminar_dia_no_laborable'),
	path('<int:obligacion_id>/estado/', views.actualizar_estado, name='actualizar_estado'),
	path('<int:obligacion_id>/vencimiento/', views.actualizar_vencimiento, name='actualizar_vencimiento'),
]