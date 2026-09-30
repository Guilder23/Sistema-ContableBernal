from django.urls import path

from . import views

app_name = 'honorarios'

urlpatterns = [
	path('', views.index, name='index'),
	path('generar-mensual/', views.generar_mensual, name='generar_mensual'),
	path('registrar-pago/', views.registrar_pago, name='registrar_pago'),
	path('crear-cobro/', views.crear_cobro_manual, name='crear_cobro_manual'),
	path('cliente/<int:cliente_id>/tarifa/', views.guardar_tarifa, name='guardar_tarifa'),
]