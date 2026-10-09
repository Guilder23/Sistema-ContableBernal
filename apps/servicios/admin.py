from django.contrib import admin

from .models import ClienteOcasional, PagoServicioTramite, ServicioTramite


@admin.register(ClienteOcasional)
class ClienteOcasionalAdmin(admin.ModelAdmin):
	list_display = ('nombre', 'documento', 'telefono', 'correo', 'creado_en')
	search_fields = ('nombre', 'documento', 'telefono', 'correo')
	readonly_fields = ('creado_en', 'actualizado_en')


@admin.register(ServicioTramite)
class ServicioTramiteAdmin(admin.ModelAdmin):
	list_display = ('concepto', 'cliente', 'tipo', 'estado', 'monto_total', 'fecha_solicitud', 'fecha_limite', 'responsable')
	list_filter = ('tipo', 'estado', 'prioridad', 'fecha_solicitud')
	search_fields = ('concepto', 'cliente__nombre', 'cliente__documento')
	readonly_fields = ('creado_en', 'actualizado_en', 'fecha_entrega')


@admin.register(PagoServicioTramite)
class PagoServicioTramiteAdmin(admin.ModelAdmin):
	list_display = ('servicio', 'fecha_pago', 'monto', 'metodo_pago', 'numero_recibo', 'registrado_por')
	list_filter = ('metodo_pago', 'fecha_pago')
	search_fields = ('servicio__concepto', 'servicio__cliente__nombre', 'numero_recibo')
	readonly_fields = ('creado_en',)
