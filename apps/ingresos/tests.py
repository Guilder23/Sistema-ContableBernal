from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.honorarios.models import CobroHonorario, PagoHonorario


class IngresosTests(TestCase):
	def setUp(self):
		self.admin = get_user_model().objects.create_superuser(username='admin_ingresos_page', password='ClaveLocal123!')
		self.cliente = Cliente.objects.create(nombre='Empresa de ingresos', nit='ING-001')
		self.cobro = CobroHonorario.objects.create(
			cliente=self.cliente,
			periodo_tipo=CobroHonorario.Periodicidad.MENSUAL,
			anio=2026,
			periodo_numero=10,
			concepto='Honorarios octubre',
			monto_base=Decimal('300.00'),
			monto_total=Decimal('300.00'),
			fecha_vencimiento=date(2026, 10, 28),
		)
		PagoHonorario.objects.create(
			cobro=self.cobro,
			monto=Decimal('100.00'),
			fecha_pago=date(2026, 10, 8),
			numero_recibo='REC-ING-01',
			metodo_pago=PagoHonorario.MetodoPago.EFECTIVO,
		)
		self.client.force_login(self.admin)

	def test_muestra_ingresos_recibidos_y_saldo_pendiente_separados(self):
		respuesta = self.client.get(reverse('ingresos:index'), {'anio': 2026})
		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context['total_ingresos_anio'], 100)
		self.assertEqual(respuesta.context['total_pendiente'], 200)
		self.assertContains(respuesta, 'REC-ING-01')
		self.assertContains(respuesta, 'Honorarios octubre')

	def test_carga_assets_homonimos_y_modales(self):
		respuesta = self.client.get(reverse('ingresos:index'))
		self.assertContains(respuesta, 'css/ingresos/ingresos.css')
		self.assertContains(respuesta, 'js/ingresos/ingresos.js')
		self.assertContains(respuesta, 'css/ingresos/modals/registrar_pago.css')
		self.assertContains(respuesta, 'js/ingresos/modals/registrar_pago.js')
		self.assertContains(respuesta, 'id="modal-registrar-pago"')
		self.assertNotContains(respuesta, 'modal-cobro-extra')
		self.assertNotContains(respuesta, 'Crear cobro extra')