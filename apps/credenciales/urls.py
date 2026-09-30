from django.urls import path

from . import views

app_name = 'credenciales'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:credencial_id>/revelar/', views.revelar_password, name='revelar_password'),
	path('<int:credencial_id>/editar/', views.editar, name='editar'),
	path('<int:credencial_id>/eliminar/', views.eliminar, name='eliminar'),
]