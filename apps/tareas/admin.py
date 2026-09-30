from django.contrib import admin

from .models import Tarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
	list_display = ('obligacion', 'responsable', 'prioridad', 'actualizada_en')
	list_filter = ('prioridad', 'obligacion__estado', 'obligacion__tipo__periodicidad')
	search_fields = ('obligacion__cliente__nombre', 'obligacion__tipo__nombre', 'responsable__username')
