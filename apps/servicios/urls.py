from django.urls import path

from . import views

app_name = 'servicios'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:servicio_id>/actualizar/', views.actualizar, name='actualizar'),
	path('<int:servicio_id>/registrar-pago/', views.registrar_pago, name='registrar_pago'),
	path('<int:servicio_id>/eliminar/', views.eliminar, name='eliminar'),
]