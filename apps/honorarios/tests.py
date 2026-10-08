from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente

from .models import CobroHonorario, PagoHonorario


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