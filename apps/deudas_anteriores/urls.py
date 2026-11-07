from django.urls import path

from . import views

app_name = 'deudas_anteriores'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:deuda_id>/', views.detalle, name='detalle'),
	path('<int:deuda_id>/editar/', views.editar, name='editar'),
	path('<int:deuda_id>/amortizar/', views.amortizar, name='amortizar'),
	path('<int:deuda_id>/eliminar/', views.eliminar, name='eliminar'),
]
