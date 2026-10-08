from django.urls import path

from . import views

app_name = 'agenda'

urlpatterns = [
	path('', views.index, name='index'),
	path('crear/', views.crear, name='crear'),
	path('<int:evento_id>/editar/', views.editar, name='editar'),
	path('<int:evento_id>/eliminar/', views.eliminar, name='eliminar'),
]