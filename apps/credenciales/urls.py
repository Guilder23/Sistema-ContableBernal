from django.urls import path

from . import views

app_name = 'credenciales'

urlpatterns = [path('', views.index, name='index')]