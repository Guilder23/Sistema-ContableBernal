from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
	list_display = (
		'nombre', 'razon_social', 'tipo', 'nit', 'ci', 'cambio_contador', 'tiene_representante_legal',
		'actividad', 'estado', 'creado_en', 'creado_por', 'actualizado_en'
	)
	list_filter = ('tipo', 'actividad', 'estado', 'cambio_contador', 'tiene_representante_legal')
	search_fields = ('nombre', 'razon_social', 'nit', 'ci', 'correo', 'telefono', 'representante_legal_nombre', 'representante_legal_carnet')
