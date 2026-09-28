from django.urls import path

from . import views

app_name = 'historial'

urlpatterns = [path('', views.index, name='index')]