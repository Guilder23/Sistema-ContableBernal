from django.urls import path

from . import views

app_name = 'requerimientos'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:requerimiento_id>/actualizar/', views.actualizar, name='actualizar'),
	path('<int:requerimiento_id>/eliminar/', views.eliminar, name='eliminar'),
	path('<int:requerimiento_id>/comentar/', views.comentar, name='comentar'),
	path('<int:requerimiento_id>/adjuntar/', views.adjuntar, name='adjuntar'),
	path('archivo/<int:archivo_id>/', views.descargar_archivo, name='descargar_archivo'),
]