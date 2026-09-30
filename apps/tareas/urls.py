from django.urls import path

from . import views

app_name = 'tareas'

urlpatterns = [
	path('', views.index, name='index'),
	path('<int:tarea_id>/asignar/', views.asignar, name='asignar'),
	path('<int:tarea_id>/estado/', views.actualizar_estado, name='actualizar_estado'),
	path('<int:tarea_id>/evidencia/', views.subir_evidencia, name='subir_evidencia'),
	path('<int:tarea_id>/evidencia/descargar/', views.descargar_evidencia, name='descargar_evidencia'),
	path('<int:tarea_id>/evidencia/eliminar/', views.eliminar_evidencia, name='eliminar_evidencia'),
]