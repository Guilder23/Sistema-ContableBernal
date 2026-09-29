from django.contrib import admin

from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
	list_display = ('usuario', 'rol', 'creado_en', 'creado_por', 'actualizado_en')
	list_filter = ('rol',)
	search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'usuario__email')
