from django.urls import path

from . import views

app_name = 'notificaciones'

urlpatterns = [
	path('', views.index, name='index'),
	path('<int:notificacion_id>/leida/', views.marcar_leida, name='marcar_leida'),
	path('leer-todas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
]