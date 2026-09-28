from django.urls import path

from . import views

app_name = 'ingresos'

urlpatterns = [path('', views.index, name='index')]