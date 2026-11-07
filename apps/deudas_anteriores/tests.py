from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.usuarios.models import PerfilUsuario

from .models import AbonoDeudaAnterior, CobroAnterior


@override_settings(STORAGES={
	'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
	'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class DeudasAnterioresTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_superuser(username='admin_deudas', password='ClaveLocal123!')
		self.gestor = user_model.objects.create_user(username='gestor_deudas', password='ClaveLocal123!')
		self.gestor.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.gestor.perfil.save()
		self.auxiliar = user_model.objects.create_user(username='auxiliar_deudas', password='ClaveLocal123!')
		self.cliente = Cliente.objects.create(nombre='Cliente deuda anterior', nit='DEUDA-01')
		self.deuda = CobroAnterior.objects.create(
			cliente=self.cliente,
			fecha_cobro=date(2025, 1, 15),
			detalle='Saldo de servicios anteriores',
			monto_total='100.00',
			registrado_por=self.admin,
		)
		self.client.force_login(self.gestor)

	def test_crea_deuda_asignada_a_cliente_y_muestra_el_modal_de_detalle(self):
		respuesta = self.client.post(reverse('deudas_anteriores:crear'), {
			'cliente': self.cliente.pk,
			'fecha_cobro': '2025-02-01',
			'detalle': 'Saldo de enero',
			'monto_total': '240.00',
		})
		deuda = CobroAnterior.objects.get(detalle='Saldo de enero')
		self.assertRedirects(respuesta, reverse('deudas_anteriores:index'))
		self.assertEqual(deuda.cliente, self.cliente)
		self.assertEqual(deuda.registrado_por, self.gestor)
		detalle = self.client.get(reverse('deudas_anteriores:detalle', args=[deuda.pk]))
		self.assertContains(detalle, f'data-deuda-modal="ver-{deuda.pk}"')
		self.assertContains(detalle, 'Amortizar deuda')
		self.assertContains(detalle, 'Historial de cobros')
		self.assertContains(detalle, 'css/deudas_anteriores/modals/ver.css')
		self.assertContains(detalle, 'js/deudas_anteriores/modals/ver.js')

	def test_muestra_errores_html_y_conserva_datos_si_la_deuda_es_invalida(self):
		respuesta = self.client.post(reverse('deudas_anteriores:crear'), {
			'cliente': self.cliente.pk,
			'fecha_cobro': '2025-02-01',
			'detalle': 'Saldo de enero',
			'monto_total': 'monto inválido',
		})
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'data-deuda-modal="crear"')
		self.assertContains(respuesta, 'Ingresa un monto válido.')
		self.assertContains(respuesta, 'value="monto inválido"')
		self.assertFalse(CobroAnterior.objects.filter(detalle='Saldo de enero').exists())

	def test_estructura_principal_y_modales_carga_css_y_javascript_propios(self):
		respuesta = self.client.get(reverse('deudas_anteriores:index'))
		self.assertEqual(respuesta.status_code, 200)
		for modal in ('crear', 'ver', 'editar', 'amortizar', 'eliminar'):
			with self.subTest(modal=modal):
				self.assertContains(respuesta, f'deudas_anteriores/modals/{modal}.css')
				self.assertContains(respuesta, f'deudas_anteriores/modals/{modal}.js')
		self.assertContains(respuesta, 'deudas_anteriores/deudas_anteriores.css')
		self.assertContains(respuesta, 'deudas_anteriores/deudas_anteriores.js')
		self.assertContains(respuesta, 'Registrar deuda')

	def test_registra_abono_parcial_y_refleja_historial_y_saldo(self):
		respuesta = self.client.post(reverse('deudas_anteriores:amortizar', args=[self.deuda.pk]), {
			'fecha_cobro': date.today().isoformat(),
			'detalle': 'Primer pago',
			'monto': '35.00',
			'numero_recibo': 'REC-100',
			'tipo_pago': AbonoDeudaAnterior.TipoPago.TRANSFERENCIA,
		})
		self.assertRedirects(respuesta, reverse('deudas_anteriores:index'))
		self.deuda.refresh_from_db()
		self.assertEqual(str(self.deuda.monto_pagado), '35.00')
		self.assertEqual(str(self.deuda.saldo_pendiente), '65.00')
		self.assertEqual(self.deuda.estado, 'parcial')
		self.assertContains(self.client.get(reverse('deudas_anteriores:detalle', args=[self.deuda.pk])), 'REC-100')

	def test_rechaza_abono_superior_al_saldo(self):
		respuesta = self.client.post(reverse('deudas_anteriores:amortizar', args=[self.deuda.pk]), {
			'fecha_cobro': date.today().isoformat(),
			'detalle': 'Pago excedido',
			'monto': '100.01',
			'numero_recibo': 'REC-101',
			'tipo_pago': AbonoDeudaAnterior.TipoPago.EFECTIVO,
		})
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, f'data-deuda-modal="amortizar-{self.deuda.pk}"')
		self.assertContains(respuesta, 'El abono no puede superar el saldo pendiente')
		self.assertFalse(AbonoDeudaAnterior.objects.filter(deuda=self.deuda).exists())
		self.deuda.refresh_from_db()
		self.assertEqual(self.deuda.saldo_pendiente, 100)

	def test_no_permite_reducir_el_total_por_debajo_de_abonos(self):
		AbonoDeudaAnterior.objects.create(
			deuda=self.deuda,
			fecha_cobro=date.today(),
			detalle='Abono existente',
			monto='40.00',
			tipo_pago=AbonoDeudaAnterior.TipoPago.EFECTIVO,
		)
		respuesta = self.client.post(reverse('deudas_anteriores:editar', args=[self.deuda.pk]), {
			'cliente': self.cliente.pk,
			'fecha_cobro': '2025-01-15',
			'detalle': self.deuda.detalle,
			'monto_total': '39.99',
		})
		self.assertEqual(respuesta.status_code, 200)
		self.deuda.refresh_from_db()
		self.assertEqual(str(self.deuda.monto_total), '100.00')
		self.assertContains(respuesta, 'El total no puede ser menor a los abonos ya registrados.')

	def test_eliminar_deuda_elimina_su_historial(self):
		AbonoDeudaAnterior.objects.create(
			deuda=self.deuda,
			fecha_cobro=date.today(),
			detalle='Abono que se eliminará',
			monto='10.00',
			tipo_pago=AbonoDeudaAnterior.TipoPago.EFECTIVO,
		)
		respuesta = self.client.post(reverse('deudas_anteriores:eliminar', args=[self.deuda.pk]))
		self.assertRedirects(respuesta, reverse('deudas_anteriores:index'))
		self.assertFalse(CobroAnterior.objects.filter(pk=self.deuda.pk).exists())
		self.assertFalse(AbonoDeudaAnterior.objects.exists())

	def test_auxiliar_no_puede_gestionar_deudas(self):
		self.client.force_login(self.auxiliar)
		self.assertEqual(self.client.post(reverse('deudas_anteriores:crear'), {}).status_code, 403)
		self.assertEqual(self.client.post(reverse('deudas_anteriores:amortizar', args=[self.deuda.pk])).status_code, 403)
