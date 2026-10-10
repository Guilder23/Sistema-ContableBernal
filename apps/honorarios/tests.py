from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente

from .models import CobroHonorario, DetalleCobroHonorario, PagoHonorario, TarifaCliente
from .services import generar_honorarios_mensuales, generar_seprec_anual


@override_settings(STORAGES={
	'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
	'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class AmortizacionCobrosTests(TestCase):
	def setUp(self):
		self.admin = get_user_model().objects.create_superuser(username='admin_ingresos', password='ClaveLocal123!')
		self.cliente = Cliente.objects.create(nombre='Cliente para cobros', nit='COBRO-01')
		self.cobro = CobroHonorario.objects.create(
			cliente=self.cliente,
			periodo_tipo=CobroHonorario.Periodicidad.EXTRA,
			anio=2026,
			periodo_numero=10,
			concepto='Trabajo extra de prueba',
			monto_base='100.00',
			monto_total='100.00',
			fecha_vencimiento=date(2026, 10, 31),
		)
		self.client.force_login(self.admin)

	def test_registra_abonos_y_actualiza_saldo_del_cobro(self):
		respuesta = self.client.post(reverse('honorarios:registrar_pago'), {
			'cobro_id': self.cobro.pk,
			'monto': '40.00',
			'fecha_pago': '2026-10-08',
			'metodo_pago': PagoHonorario.MetodoPago.EFECTIVO,
			'volver': reverse('ingresos:index'),
		})
		self.assertRedirects(respuesta, reverse('ingresos:index'))
		self.cobro.refresh_from_db()
		self.assertEqual(self.cobro.estado, CobroHonorario.Estado.PARCIAL)
		self.assertEqual(self.cobro.saldo_pendiente, 60)

	def test_rechaza_amortizacion_mayor_al_saldo_pendiente(self):
		respuesta = self.client.post(reverse('honorarios:registrar_pago'), {
			'cobro_id': self.cobro.pk,
			'monto': '100.01',
			'fecha_pago': '2026-10-08',
			'metodo_pago': PagoHonorario.MetodoPago.EFECTIVO,
			'volver': reverse('ingresos:index'),
		})
		self.assertRedirects(respuesta, reverse('ingresos:index'))
		self.assertFalse(PagoHonorario.objects.filter(cobro=self.cobro).exists())
		self.cobro.refresh_from_db()
		self.assertEqual(self.cobro.estado, CobroHonorario.Estado.PENDIENTE)

	def test_honorarios_crea_cobros_pero_deja_los_abonos_en_ingresos(self):
		respuesta = self.client.get(reverse('honorarios:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'Cobro extra')
		self.assertContains(respuesta, 'Generar mes')
		self.assertNotContains(respuesta, 'modal-registrar-pago')
		self.assertNotContains(respuesta, 'Cobrar</button>')

	def test_genera_honorarios_recurrentes_con_desglose_de_servicios(self):
		TarifaCliente.objects.create(
			cliente=self.cliente,
			monto_mensual='500.00',
			extra_gestora='20.00',
			extra_ministerio='30.00',
			extra_caja='10.00',
		)
		generar_honorarios_mensuales(2026, 11, usuario=self.admin, incluir_cero=False)
		cobro = CobroHonorario.objects.get(cliente=self.cliente, anio=2026, periodo_numero=11)
		self.assertEqual(cobro.tipo_ingreso, CobroHonorario.TipoIngreso.RECURRENTE)
		self.assertEqual(str(cobro.monto_total), '560.00')
		self.assertEqual(cobro.detalles.count(), 4)
		self.assertEqual(sum((detalle.monto for detalle in cobro.detalles.all())), cobro.monto_total)

	def test_genera_seprec_anual_solo_una_vez_y_como_ingreso_recurrente(self):
		TarifaCliente.objects.create(cliente=self.cliente, monto_anual='200.00', extra_seprec='150.00')
		primera = generar_seprec_anual(2026, usuario=self.admin)
		segunda = generar_seprec_anual(2026, usuario=self.admin)
		cobro = CobroHonorario.objects.get(cliente=self.cliente, periodo_tipo=CobroHonorario.Periodicidad.ANUAL)
		self.assertEqual(primera['creados'], 1)
		self.assertEqual(segunda['existentes'], 1)
		self.assertEqual(cobro.tipo_ingreso, CobroHonorario.TipoIngreso.RECURRENTE)
		self.assertEqual(str(cobro.monto_total), '350.00')
		self.assertTrue(cobro.detalles.filter(tipo_servicio=DetalleCobroHonorario.TipoServicio.SEPREC, monto='150.00').exists())

	def test_registra_tramite_como_ingreso_extraordinario(self):
		respuesta = self.client.post(reverse('honorarios:crear_cobro_manual'), {
			'cliente_id': self.cliente.pk,
			'periodo_tipo': CobroHonorario.Periodicidad.EXTRA,
			'tipo_ingreso': CobroHonorario.TipoIngreso.EXTRAORDINARIO,
			'tipo_servicio': DetalleCobroHonorario.TipoServicio.CERTIFICADO,
			'concepto': 'Certificado de impuestos',
			'monto_total': '80.00',
		})
		self.assertEqual(respuesta.status_code, 302)
		cobro = CobroHonorario.objects.get(concepto='Certificado de impuestos')
		self.assertEqual(cobro.tipo_ingreso, CobroHonorario.TipoIngreso.EXTRAORDINARIO)
		self.assertEqual(cobro.detalles.get().tipo_servicio, DetalleCobroHonorario.TipoServicio.CERTIFICADO)

	def test_guarda_tarifa_y_la_muestra_en_la_ficha_del_cliente(self):
		respuesta = self.client.post(reverse('honorarios:guardar_tarifa', args=[self.cliente.pk]), {
			'monto_mensual': '750.00',
			'monto_trimestral': '1200.00',
			'monto_anual': '1800.00',
			'extra_bancarizacion': '25.00',
			'extra_gestora': '30.00',
			'extra_ministerio': '0.00',
			'extra_caja': '0.00',
			'extra_otros': '0.00',
			'extra_seprec': '55.00',
			'observaciones': 'Acuerdo vigente',
		})
		self.assertRedirects(respuesta, f"{reverse('clientes:detalle', args=[self.cliente.pk])}#tab-honorarios", fetch_redirect_response=False)
		ficha = self.client.get(reverse('clientes:detalle', args=[self.cliente.pk]))
		self.assertContains(ficha, 'value="750.00"')
		self.assertContains(ficha, 'value="55.00"')
		self.assertContains(ficha, 'Acuerdo vigente')

	def test_crea_cobro_desde_la_ficha_y_lo_muestra_al_volver(self):
		url_ficha = reverse('clientes:detalle', args=[self.cliente.pk])
		self.assertContains(self.client.get(url_ficha), 'modal-crear-cobro')
		respuesta = self.client.post(reverse('honorarios:crear_cobro_manual'), {
			'cliente_id': self.cliente.pk,
			'periodo_tipo': CobroHonorario.Periodicidad.EXTRA,
			'tipo_ingreso': CobroHonorario.TipoIngreso.EXTRAORDINARIO,
			'tipo_servicio': DetalleCobroHonorario.TipoServicio.TRAMITE,
			'concepto': 'Trámite registrado desde ficha',
			'monto_total': '320.00',
			'volver': f'{url_ficha}#tab-honorarios',
		})
		self.assertRedirects(respuesta, f'{url_ficha}#tab-honorarios', fetch_redirect_response=False)
		ficha = self.client.get(url_ficha)
		self.assertContains(ficha, 'Trámite registrado desde ficha')
		self.assertContains(ficha, 'Bs 320.00')