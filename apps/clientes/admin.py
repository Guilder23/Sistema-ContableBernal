from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'tipo', 'nit', 'actividad', 'estado', 'creado_en', 'creado_por', 'actualizado_en')
	list_filter = ('tipo', 'actividad', 'estado')
	search_fields = ('nombre', 'nit', 'ci', 'correo', 'telefono')
