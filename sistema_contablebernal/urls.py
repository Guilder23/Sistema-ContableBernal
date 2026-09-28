"""
URL configuration for sistema_contablebernal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('credenciales/', include('apps.credenciales.urls')),
    path('obligaciones/', include('apps.obligaciones.urls')),
    path('tareas/', include('apps.tareas.urls')),
    path('honorarios/', include('apps.honorarios.urls')),
    path('ingresos/', include('apps.ingresos.urls')),
    path('gastos/', include('apps.gastos.urls')),
    path('servicios/', include('apps.servicios.urls')),
    path('requerimientos/', include('apps.requerimientos.urls')),
    path('agenda/', include('apps.agenda.urls')),
    path('documentos/', include('apps.documentos.urls')),
    path('historial/', include('apps.historial.urls')),
    path('notificaciones/', include('apps.notificaciones.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('configuracion/', include('apps.configuracion.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
