from django.contrib import admin

from .models import EventoAgenda


@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
	list_display = ('fecha', 'hora_inicio', 'titulo', 'tipo', 'cliente', 'responsable', 'estado')
	list_filter = ('tipo', 'estado', 'fecha')
	search_fields = ('titulo', 'lugar', 'cliente__nombre', 'responsable__username')
	date_hierarchy = 'fecha'
