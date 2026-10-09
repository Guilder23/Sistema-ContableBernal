from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.historial.models import EntradaHistorial

from .models import ClienteOcasional, PagoServicioTramite, ServicioTramite


class ServiciosOcasionalesTests(TestCase):
	def setUp(self):
		self.admin = get_user_model().objects.create_superuser(
			username='admin_servicios_ocasionales',
			password='ClaveLocal123!',
		)
		self.client.force_login(self.admin)

	def test_registra_cliente_ocasional_tramite_anticipo_y_saldo(self):
		respuesta = self.client.post(reverse('servicios:crear'), {
			'cliente_id': 'nuevo',
			'nombre_cliente': 'María Ocasional',
			'documento_cliente': '1234567',
			'telefono_cliente': '70123456',
			'tipo': ServicioTramite.Tipo.LICENCIA,
			'concepto': 'Licencia de funcionamiento',
			'descripcion': 'Trámite por única vez.',
			'prioridad': ServicioTramite.Prioridad.NORMAL,
			'fecha_limite': '2026-11-15',
			'monto_total': '500.00',
			'pago_inicial': '150.00',
			'metodo_pago': PagoServicioTramite.MetodoPago.EFECTIVO,
		})
		self.assertRedirects(respuesta, reverse('servicios:index'))
		cliente = ClienteOcasional.objects.get(nombre='María Ocasional')
		servicio = ServicioTramite.objects.get(cliente=cliente)
		self.assertEqual(Cliente.objects.count(), 0)
		self.assertEqual(servicio.estado, ServicioTramite.Estado.NUEVO)
		self.assertEqual(str(servicio.total_pagado), '150.00')
		self.assertEqual(str(servicio.saldo_pendiente), '350.00')
		self.assertEqual(servicio.estado_cobro, ServicioTramite.EstadoCobro.PARCIAL)
		evento = EntradaHistorial.objects.get(seccion=EntradaHistorial.Seccion.SERVICIOS)
		self.assertIsNone(evento.cliente)
		self.assertEqual(evento.usuario, self.admin)
		self.assertIn('María Ocasional', evento.referencia)

	def test_registra_saldo_final_y_este_aparece_en_ingresos(self):
		cliente = ClienteOcasional.objects.create(nombre='Cliente de licencia')
		servicio = ServicioTramite.objects.create(
			cliente=cliente,
			tipo=ServicioTramite.Tipo.LICENCIA,
			concepto='Licencia municipal',
			monto_total='300.00',
		)
		self.client.post(reverse('servicios:registrar_pago', args=[servicio.pk]), {
			'monto': '50.00',
			'fecha_pago': '2026-10-09',
			'metodo_pago': PagoServicioTramite.MetodoPago.TRANSFERENCIA,
		})
		self.client.post(reverse('servicios:registrar_pago', args=[servicio.pk]), {
			'monto': '250.00',
			'fecha_pago': '2026-10-09',
			'metodo_pago': PagoServicioTramite.MetodoPago.EFECTIVO,
			'numero_recibo': 'R-002',
		})
		servicio.refresh_from_db()
		self.assertEqual(servicio.estado_cobro, ServicioTramite.EstadoCobro.PAGADO)
		self.assertEqual(str(servicio.saldo_pendiente), '0.00')
		respuesta = self.client.get(reverse('ingresos:index'), {'anio': '2026'})
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'Pagos de trámites ocasionales')
		self.assertContains(respuesta, 'Licencia municipal')
		self.assertEqual(respuesta.context['total_ingresos_anio'], Decimal('300.00'))
		self.assertEqual(respuesta.context['total_pagos_servicios'], 2)

	def test_rechaza_abono_mayor_al_saldo_y_no_permite_borrar_con_pagos(self):
		cliente = ClienteOcasional.objects.create(nombre='Cliente con saldo')
		servicio = ServicioTramite.objects.create(
			cliente=cliente,
			concepto='Certificado',
			monto_total='100.00',
		)
		self.client.post(reverse('servicios:registrar_pago', args=[servicio.pk]), {
			'monto': '100.01',
			'fecha_pago': '2026-10-09',
		})
		self.assertFalse(PagoServicioTramite.objects.filter(servicio=servicio).exists())
		self.client.post(reverse('servicios:registrar_pago', args=[servicio.pk]), {
			'monto': '20.00',
			'fecha_pago': '2026-10-09',
		})
		self.client.post(reverse('servicios:eliminar', args=[servicio.pk]))
		self.assertTrue(ServicioTramite.objects.filter(pk=servicio.pk).exists())

	def test_edita_estado_de_entrega_sin_exigir_pago_total(self):
		cliente = ClienteOcasional.objects.create(nombre='Cliente de trámite')
		servicio = ServicioTramite.objects.create(
			cliente=cliente,
			concepto='Certificado tributario',
			monto_total='200.00',
		)
		respuesta = self.client.post(reverse('servicios:actualizar', args=[servicio.pk]), {
			'concepto': servicio.concepto,
			'descripcion': 'Terminado para entregar.',
			'tipo': servicio.tipo,
			'estado': ServicioTramite.Estado.ENTREGADO,
			'prioridad': servicio.prioridad,
			'fecha_limite': '',
			'monto_total': '200.00',
			'responsable': '',
		})
		self.assertRedirects(respuesta, reverse('servicios:index'))
		servicio.refresh_from_db()
		self.assertEqual(servicio.estado, ServicioTramite.Estado.ENTREGADO)
		self.assertEqual(str(servicio.saldo_pendiente), '200.00')

	def test_pantalla_muestra_los_assets_de_cada_modal(self):
		respuesta = self.client.get(reverse('servicios:index'))
		self.assertEqual(respuesta.status_code, 200)
		for modal in ('crear', 'editar', 'ver', 'pago', 'eliminar'):
			self.assertContains(respuesta, f'css/servicios/modals/{modal}.css')
			self.assertContains(respuesta, f'js/servicios/modals/{modal}.js')

	def test_editar_entrega_el_precio_en_formato_numerico(self):
		cliente = ClienteOcasional.objects.create(nombre='Cliente para edición')
		ServicioTramite.objects.create(
			cliente=cliente,
			concepto='Licencia comercial',
			monto_total='200.00',
		)
		respuesta = self.client.get(reverse('servicios:index'))
		self.assertContains(respuesta, 'data-edit-monto="200.00"')
