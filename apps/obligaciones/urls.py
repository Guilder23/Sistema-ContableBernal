from django.urls import path

from . import views

app_name = 'obligaciones'

urlpatterns = [path('', views.index, name='index')]