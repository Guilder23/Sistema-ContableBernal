from django.contrib import admin

from .models import AbonoDeudaAnterior, CobroAnterior


class AbonoDeudaAnteriorInline(admin.TabularInline):
	model = AbonoDeudaAnterior
	extra = 0
	readonly_fields = ('registrado_por', 'creado_en')


@admin.register(CobroAnterior)
class CobroAnteriorAdmin(admin.ModelAdmin):
	list_display = ('cliente', 'detalle', 'fecha_cobro', 'monto_total', 'monto_pagado', 'saldo_pendiente', 'estado')
	list_filter = ('fecha_cobro',)
	search_fields = ('cliente__nombre', 'cliente__nit', 'detalle')
	inlines = (AbonoDeudaAnteriorInline,)


@admin.register(AbonoDeudaAnterior)
class AbonoDeudaAnteriorAdmin(admin.ModelAdmin):
	list_display = ('deuda', 'fecha_cobro', 'detalle', 'numero_recibo', 'tipo_pago', 'monto', 'registrado_por')
	list_filter = ('tipo_pago', 'fecha_cobro')
	search_fields = ('deuda__cliente__nombre', 'detalle', 'numero_recibo')
	readonly_fields = ('registrado_por', 'creado_en')
