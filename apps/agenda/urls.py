from django.urls import path

from . import views

app_name = 'agenda'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:evento_id>/editar/', views.editar, name='editar'),
	path('<int:evento_id>/eliminar/', views.eliminar, name='eliminar'),
	path('google/conectar/', views.google_conectar, name='google_conectar'),
	path('google/callback/', views.google_callback, name='google_callback'),
	path('google/desconectar/', views.google_desconectar, name='google_desconectar'),
	path('google/reintentar/', views.google_reintentar, name='google_reintentar'),
]