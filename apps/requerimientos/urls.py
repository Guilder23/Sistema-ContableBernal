from django.urls import path

from . import views

app_name = 'requerimientos'

urlpatterns = [path('', views.index, name='index')]