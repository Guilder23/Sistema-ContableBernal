from django.contrib import admin

from .models import ConfiguracionCliente, DiaNoLaborable, Obligacion, TipoObligacion


@admin.register(TipoObligacion)
class TipoObligacionAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'periodicidad', 'regla_vencimiento', 'dia_vencimiento', 'activa')
	list_filter = ('periodicidad', 'regla_vencimiento', 'activa')
	search_fields = ('nombre', 'codigo')


@admin.register(ConfiguracionCliente)
class ConfiguracionClienteAdmin(admin.ModelAdmin):
	list_display = ('cliente', 'tipo', 'fecha_inicio', 'activa')
	list_filter = ('tipo__periodicidad', 'activa')
	search_fields = ('cliente__nombre', 'tipo__nombre')


@admin.register(Obligacion)
class ObligacionAdmin(admin.ModelAdmin):
	list_display = ('tipo', 'cliente', 'anio', 'periodo_numero', 'fecha_vencimiento', 'estado')
	list_filter = ('tipo__periodicidad', 'estado', 'anio')
	search_fields = ('cliente__nombre', 'tipo__nombre', 'cliente__nit')


@admin.register(DiaNoLaborable)
class DiaNoLaborableAdmin(admin.ModelAdmin):
	list_display = ('fecha', 'descripcion')
	search_fields = ('descripcion',)
	date_hierarchy = 'fecha'
