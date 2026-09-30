from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
	list_display = ('titulo', 'destinatario', 'tipo', 'creada_en', 'leida_en')
	list_filter = ('tipo', 'leida_en', 'creada_en')
	search_fields = ('titulo', 'mensaje', 'destinatario__username', 'actor__username')
	readonly_fields = ('creada_en',)
