from django.urls import path

from . import views

app_name = 'gastos'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:registro_id>/editar/', views.editar, name='editar'),
	path('<int:registro_id>/recuperar/', views.registrar_recuperacion, name='registrar_recuperacion'),
	path('<int:registro_id>/eliminar/', views.eliminar, name='eliminar'),
]