from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.usuarios.models import PerfilUsuario

from .models import Cliente


class GestionClientesTests(TestCase):
	def setUp(self):
		self.modelo_usuario = get_user_model()
		self.administrador = self.modelo_usuario.objects.create_superuser(
			username='admin_clientes',
			password='G7!pL2-rT6#vM4x',
		)
		self.secretario = self.modelo_usuario.objects.create_user(
			username='secretario_clientes',
			password='Q8!pL2-rT6#vM4x',
		)
		self.secretario.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.secretario.perfil.save(update_fields=['rol', 'actualizado_en'])
		self.auxiliar = self.modelo_usuario.objects.create_user(
			username='auxiliar_clientes',
			password='V7!mQ4-zX9pL2#b',
		)
		self.client.force_login(self.administrador)

	def datos_cliente(self, **cambios):
		return {
			'nombre': 'Comercial El Roble',
			'tipo': Cliente.Tipo.JURIDICA,
			'nit': '123456789',
			'ci': '',
			'actividad': Cliente.Actividad.COMERCIAL,
			'telefono': '2212345',
			'whatsapp': '70123456',
			'correo': 'roble@example.test',
			'direccion': 'La Paz',
			'estado': 'activo',
			'fecha_inicio': '2026-01-15',
			'observaciones': 'Cliente de prueba',
			**cambios,
		}

	def test_directorio_y_modales_tienen_assets_homonimos(self):
		response = self.client.get('/clientes/')
		self.assertEqual(response.status_code, 200)
		for modal in ('crear', 'ver', 'editar', 'eliminar'):
			self.assertContains(response, f'id="modal-{modal}"')
			self.assertContains(response, f'css/clientes/modals/{modal}.css')
			self.assertContains(response, f'js/clientes/modals/{modal}.js')

	def test_crea_cliente_con_datos_tributarios_y_contacto(self):
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		self.assertRedirects(response, '/clientes/')
		cliente = Cliente.objects.get(nit='123456789')
		self.assertEqual(cliente.nombre, 'Comercial El Roble')
		self.assertEqual(cliente.tipo, Cliente.Tipo.JURIDICA)
		self.assertEqual(cliente.fecha_inicio.isoformat(), '2026-01-15')

	def test_nit_duplicado_reabre_modal_con_error(self):
		Cliente.objects.create(nombre='Cliente existente', nit='123456789')
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['modal_activo'], 'modal-crear')
		self.assertContains(response, 'Ya existe un cliente con ese NIT.')

	def test_edita_consulta_y_elimina_desde_el_directorio(self):
		cliente = Cliente.objects.create(nombre='Cliente inicial', nit='987654321')
		response = self.client.post(f'/clientes/{cliente.pk}/editar/', self.datos_cliente(nit='987654321'))
		self.assertRedirects(response, '/clientes/')
		cliente.refresh_from_db()
		self.assertEqual(cliente.nombre, 'Comercial El Roble')
		self.assertContains(self.client.get('/clientes/'), 'Comercial El Roble')
		response = self.client.post(f'/clientes/{cliente.pk}/eliminar/')
		self.assertRedirects(response, '/clientes/')
		self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())

	def test_auxiliar_solo_consulta_y_secretario_gestiona(self):
		self.client.force_login(self.auxiliar)
		self.assertEqual(self.client.get('/clientes/').status_code, 200)
		self.assertEqual(self.client.post('/clientes/crear/', self.datos_cliente()).status_code, 403)
		self.client.force_login(self.secretario)
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		self.assertRedirects(response, '/clientes/')
		self.assertTrue(Cliente.objects.filter(nit='123456789').exists())

	def test_mutaciones_solo_aceptan_post(self):
		cliente = Cliente.objects.create(nombre='Cliente GET')
		self.assertEqual(self.client.get('/clientes/crear/').status_code, 405)
		self.assertEqual(self.client.get(f'/clientes/{cliente.pk}/editar/').status_code, 405)
		self.assertEqual(self.client.get(f'/clientes/{cliente.pk}/eliminar/').status_code, 405)

	def test_paginacion_conserva_busqueda_y_filtros(self):
		for indice in range(13):
			Cliente.objects.create(
				nombre=f'Cliente listado {indice}',
				nit=f'PAG-{indice:04}',
				tipo=Cliente.Tipo.JURIDICA,
			)
		response = self.client.get('/clientes/?tipo=juridica&estado=activo&page=2')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['page_obj'].number, 2)
		self.assertEqual(response.context['total_clientes'], 13)
		self.assertContains(response, 'tipo=juridica&amp;estado=activo&amp;page=1')
