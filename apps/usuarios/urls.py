from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('crear/', views.crear, name='crear'),
    path('<int:usuario_id>/editar/', views.editar, name='editar'),
    path('<int:usuario_id>/eliminar/', views.eliminar, name='eliminar'),
    path('', views.index, name='index'),
]