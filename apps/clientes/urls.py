from django.urls import path

from . import views

app_name = 'clientes'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:cliente_id>/', views.detalle, name='detalle'),
	path('<int:cliente_id>/editar/', views.editar, name='editar'),
	path('<int:cliente_id>/eliminar/', views.eliminar, name='eliminar'),
]