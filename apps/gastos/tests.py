from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clientes.models import Cliente
from apps.usuarios.models import PerfilUsuario

from .models import RegistroFinanciero


class GestionGastosTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_superuser(username='admin_gastos', password='ClaveLocal123!')
		self.auxiliar = user_model.objects.create_user(username='auxiliar_gastos', password='ClaveLocal123!')
		self.secretario = user_model.objects.create_user(username='secretario_gastos', password='ClaveLocal123!')
		self.secretario.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.secretario.perfil.save(update_fields=['rol', 'actualizado_en'])
		self.cliente = Cliente.objects.create(nombre='Cliente de gastos', nit='GASTO-001')
		self.client.force_login(self.admin)

	def test_registra_una_salida_recuperable_de_cliente(self):
		response = self.client.post('/gastos/crear/', {
			'concepto': 'Pasanku cliente',
			'tipo': RegistroFinanciero.Tipo.EGRESO,
			'categoria': RegistroFinanciero.Categoria.PASANKU,
			'periodicidad': RegistroFinanciero.Periodicidad.UNICO,
			'monto': '350.50',
			'fecha': '2026-10-08',
			'cliente': str(self.cliente.pk),
			'recuperable': 'on',
			'estado_pago': RegistroFinanciero.EstadoPago.PAGADO,
			'estado_recuperacion': RegistroFinanciero.EstadoRecuperacion.PENDIENTE,
			'estado_activo': RegistroFinanciero.EstadoActivo.EN_USO,
		})
		self.assertRedirects(response, '/gastos/')
		registro = RegistroFinanciero.objects.get(concepto='Pasanku cliente')
		self.assertEqual(registro.cliente, self.cliente)
		self.assertEqual(str(registro.monto), '350.50')
		self.assertEqual(registro.tipo, RegistroFinanciero.Tipo.EGRESO)

	def test_registra_recuperaciones_parciales_y_calcula_el_saldo(self):
		registro = RegistroFinanciero.objects.create(
			concepto='Trámite cliente',
			tipo=RegistroFinanciero.Tipo.EGRESO,
			categoria=RegistroFinanciero.Categoria.OTRO,
			monto='100.00',
			fecha='2026-10-08',
			recuperable=True,
			cliente=self.cliente,
		)
		url = f'/gastos/{registro.pk}/recuperar/'
		primera = self.client.post(url, {'monto': '40.00', 'fecha': '2026-10-09'})
		self.assertRedirects(primera, '/gastos/')
		registro.refresh_from_db()
		self.assertEqual(str(registro.monto_recuperado), '40.00')
		self.assertEqual(str(registro.saldo_por_recuperar), '60.00')
		self.assertEqual(registro.estado_recuperacion, RegistroFinanciero.EstadoRecuperacion.PENDIENTE)
		self.client.post(url, {'monto': '60.00', 'fecha': '2026-10-10'})
		registro.refresh_from_db()
		self.assertEqual(registro.estado_recuperacion, RegistroFinanciero.EstadoRecuperacion.RECUPERADO)
		self.assertEqual(str(registro.saldo_por_recuperar), '0.00')

	def test_no_permite_recuperar_mas_que_el_saldo(self):
		registro = RegistroFinanciero.objects.create(
			concepto='Certificado',
			tipo=RegistroFinanciero.Tipo.EGRESO,
			categoria=RegistroFinanciero.Categoria.OTRO,
			monto='100.00',
			fecha='2026-10-08',
			recuperable=True,
			cliente=self.cliente,
		)
		self.client.post(f'/gastos/{registro.pk}/recuperar/', {'monto': '100.01', 'fecha': '2026-10-09'})
		self.assertFalse(registro.recuperaciones.exists())

	def test_registra_gasto_normal_sin_campos_de_activo_ni_recuperacion(self):
		response = self.client.post('/gastos/crear/', {
			'concepto': 'Alquiler oficina',
			'tipo': RegistroFinanciero.Tipo.GASTO,
			'categoria': RegistroFinanciero.Categoria.ALQUILER,
			'periodicidad': RegistroFinanciero.Periodicidad.MENSUAL,
			'monto': '2500.00',
			'fecha': '2026-10-08',
			'estado_pago': RegistroFinanciero.EstadoPago.PENDIENTE,
		})
		self.assertRedirects(response, '/gastos/')
		registro = RegistroFinanciero.objects.get(concepto='Alquiler oficina')
		self.assertFalse(registro.recuperable)
		self.assertEqual(registro.estado_activo, RegistroFinanciero.EstadoActivo.EN_USO)

	def test_registra_inversion_y_filtra_por_tipo(self):
		self.client.post('/gastos/crear/', {
			'concepto': 'Sillas oficina',
			'tipo': RegistroFinanciero.Tipo.INVERSION,
			'categoria': RegistroFinanciero.Categoria.MUEBLES,
			'periodicidad': RegistroFinanciero.Periodicidad.UNICO,
			'monto': '1200',
			'fecha': '2026-10-08',
			'vida_util_meses': '36',
			'estado_pago': RegistroFinanciero.EstadoPago.PENDIENTE,
			'estado_recuperacion': RegistroFinanciero.EstadoRecuperacion.PENDIENTE,
			'estado_activo': RegistroFinanciero.EstadoActivo.EN_USO,
		})
		response = self.client.get('/gastos/?tipo=inversion')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Sillas oficina')
		self.assertEqual(response.context['total_registros'], 1)

	def test_auxiliar_consulta_pero_no_puede_registrar(self):
		self.client.force_login(self.auxiliar)
		response = self.client.get('/gastos/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id="modal-ver"')
		self.assertContains(response, 'js/gastos/modals/ver.js')
		self.assertNotContains(response, 'id="modal-editar"')
		response = self.client.post('/gastos/crear/', {
			'concepto': 'Intento sin permisos',
			'tipo': RegistroFinanciero.Tipo.GASTO,
			'categoria': RegistroFinanciero.Categoria.INTERNET,
			'periodicidad': RegistroFinanciero.Periodicidad.MENSUAL,
			'monto': '100',
			'fecha': '2026-10-08',
		})
		self.assertEqual(response.status_code, 403)
		self.assertFalse(RegistroFinanciero.objects.exists())

	def test_edita_y_elimina_un_registro_financiero(self):
		registro = RegistroFinanciero.objects.create(
			concepto='Internet oficina',
			tipo=RegistroFinanciero.Tipo.GASTO,
			categoria=RegistroFinanciero.Categoria.INTERNET,
			periodicidad=RegistroFinanciero.Periodicidad.MENSUAL,
			monto='250.00',
			fecha='2026-10-01',
			creado_por=self.admin,
		)
		response = self.client.post(f'/gastos/{registro.pk}/editar/', {
			'concepto': 'Internet y telefonía',
			'tipo': RegistroFinanciero.Tipo.GASTO,
			'categoria': RegistroFinanciero.Categoria.INTERNET,
			'periodicidad': RegistroFinanciero.Periodicidad.MENSUAL,
			'monto': '300.00',
			'fecha': '2026-10-01',
			'estado_pago': RegistroFinanciero.EstadoPago.PAGADO,
			'estado_recuperacion': RegistroFinanciero.EstadoRecuperacion.PENDIENTE,
			'estado_activo': RegistroFinanciero.EstadoActivo.EN_USO,
		})
		self.assertRedirects(response, '/gastos/')
		registro.refresh_from_db()
		self.assertEqual(registro.concepto, 'Internet y telefonía')
		self.assertEqual(str(registro.monto), '300.00')
		response = self.client.post(f'/gastos/{registro.pk}/eliminar/')
		self.assertRedirects(response, '/gastos/')
		self.assertFalse(RegistroFinanciero.objects.filter(pk=registro.pk).exists())

	def test_rechaza_categoria_que_no_corresponde_al_tipo(self):
		response = self.client.post('/gastos/crear/', {
			'concepto': 'Categoría incorrecta',
			'tipo': RegistroFinanciero.Tipo.GASTO,
			'categoria': RegistroFinanciero.Categoria.IMPUESTOS,
			'periodicidad': RegistroFinanciero.Periodicidad.MENSUAL,
			'monto': '100.00',
			'fecha': '2026-10-08',
			'estado_pago': RegistroFinanciero.EstadoPago.PENDIENTE,
			'estado_recuperacion': RegistroFinanciero.EstadoRecuperacion.PENDIENTE,
			'estado_activo': RegistroFinanciero.EstadoActivo.EN_USO,
		})
		self.assertEqual(response.status_code, 400)
		self.assertContains(response, 'La categoría no corresponde', status_code=400)
		self.assertFalse(RegistroFinanciero.objects.exists())

	def test_pantalla_carga_assets_homonimos_y_modal_de_registro(self):
		response = self.client.get('/gastos/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'css/gastos/gastos.css')
		self.assertContains(response, 'js/gastos/gastos.js')
		self.assertContains(response, 'css/gastos/modals/registro.css')
		self.assertContains(response, 'js/gastos/modals/registro.js')
		self.assertContains(response, 'id="modal-registro"')
		self.assertContains(response, 'css/gastos/modals/ver.css')
		self.assertContains(response, 'js/gastos/modals/ver.js')
		self.assertContains(response, 'id="modal-ver"')
		self.assertContains(response, 'css/gastos/modals/editar.css')
		self.assertContains(response, 'js/gastos/modals/editar.js')
		self.assertContains(response, 'id="modal-editar"')
		self.assertContains(response, 'css/gastos/modals/eliminar.css')
		self.assertContains(response, 'js/gastos/modals/eliminar.js')
		self.assertContains(response, 'id="modal-eliminar"')
		self.assertContains(response, 'data-categoria-tipo="gasto"')
		self.assertContains(response, 'data-categoria-tipo="inversion"')
		self.assertContains(response, 'data-categoria-tipo="egreso"')
