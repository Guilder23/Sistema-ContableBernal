from django.contrib import admin

from .models import RegistroFinanciero


@admin.register(RegistroFinanciero)
class RegistroFinancieroAdmin(admin.ModelAdmin):
	list_display = ('fecha', 'concepto', 'tipo', 'categoria', 'monto', 'estado_pago', 'recuperable', 'cliente')
	list_filter = ('tipo', 'categoria', 'periodicidad', 'estado_pago', 'recuperable', 'estado_recuperacion')
	search_fields = ('concepto', 'proveedor', 'comprobante', 'cliente__nombre', 'cliente__razon_social')
	date_hierarchy = 'fecha'
