from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import PerfilUsuario


class GestionUsuariosTests(TestCase):
	def setUp(self):
		self.modelo_usuario = get_user_model()
		self.administrador = self.modelo_usuario.objects.create_superuser(
			username='admin_pruebas',
			email='admin@example.test',
			password='S3gura!Admin-8492',
		)
		self.auxiliar = self.modelo_usuario.objects.create_user(
			username='auxiliar_pruebas',
			password='V7!mQ4-zX9pL2#b',
		)
		self.client.force_login(self.administrador)

	def test_listado_y_modales_tienen_assets_propios(self):
		response = self.client.get('/usuarios/')
		self.assertEqual(response.status_code, 200)
		for modal in ('crear', 'ver', 'editar', 'eliminar'):
			self.assertContains(response, f'id="modal-{modal}"')
			self.assertContains(response, f'css/usuarios/modals/{modal}.css')
			self.assertContains(response, f'js/usuarios/modals/{modal}.js')

	def test_solo_administradores_pueden_abrir_gestion(self):
		self.client.logout()
		response = self.client.get('/usuarios/')
		self.assertRedirects(response, '/usuarios/login/?next=/usuarios/')
		self.client.force_login(self.auxiliar)
		self.assertEqual(self.client.get('/usuarios/').status_code, 403)

	def test_crea_usuario_con_rol_y_credenciales_validas(self):
		response = self.client.post('/usuarios/crear/', {
			'username': 'secretaria_nueva',
			'first_name': 'Ana',
			'last_name': 'Prueba',
			'email': 'ana@example.test',
			'rol': PerfilUsuario.Rol.SECRETARIO,
			'is_active': 'on',
			'password': 'X9$vpL3-mQ7!tR2',
			'password_confirm': 'X9$vpL3-mQ7!tR2',
		})
		self.assertRedirects(response, '/usuarios/')
		cuenta = self.modelo_usuario.objects.get(username='secretaria_nueva')
		self.assertEqual(cuenta.perfil.rol, PerfilUsuario.Rol.SECRETARIO)
		self.assertTrue(cuenta.check_password('X9$vpL3-mQ7!tR2'))

	def test_edita_consulta_y_elimina_usuario(self):
		response = self.client.post(f'/usuarios/{self.auxiliar.pk}/editar/', {
			'username': 'auxiliar_actualizado',
			'first_name': 'Luis',
			'last_name': 'Auxiliar',
			'email': 'luis@example.test',
			'rol': PerfilUsuario.Rol.AUXILIAR,
			'is_active': 'on',
		})
		self.assertRedirects(response, '/usuarios/')
		self.auxiliar.refresh_from_db()
		self.assertEqual(self.auxiliar.username, 'auxiliar_actualizado')
		self.assertEqual(self.auxiliar.perfil.rol, PerfilUsuario.Rol.AUXILIAR)
		self.assertEqual(self.client.get(f'/usuarios/{self.auxiliar.pk}/').status_code, 404)
		response = self.client.post(f'/usuarios/{self.auxiliar.pk}/eliminar/')
		self.assertRedirects(response, '/usuarios/')
		self.assertFalse(self.modelo_usuario.objects.filter(pk=self.auxiliar.pk).exists())

	def test_modal_se_reabre_con_errores_y_no_hay_paginas_crud_separadas(self):
		response = self.client.post('/usuarios/crear/', {
			'username': self.auxiliar.username,
			'rol': PerfilUsuario.Rol.AUXILIAR,
			'is_active': 'on',
			'password': 'Q8!pL2-rT6#vM4x',
			'password_confirm': 'Q8!pL2-rT6#vM4x',
		})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id="modal-crear"')
		self.assertContains(response, 'Ya existe una cuenta con ese nombre de usuario.')
		self.assertEqual(response.context['modal_activo'], 'modal-crear')
		self.assertEqual(self.client.get('/usuarios/crear/').status_code, 405)
		self.assertEqual(self.client.get(f'/usuarios/{self.auxiliar.pk}/editar/').status_code, 405)
		self.assertEqual(self.client.get(f'/usuarios/{self.auxiliar.pk}/eliminar/').status_code, 405)

	def test_no_permite_quedarse_sin_administrador_activo(self):
		response = self.client.post(f'/usuarios/{self.administrador.pk}/editar/', {
			'username': self.administrador.username,
			'rol': PerfilUsuario.Rol.AUXILIAR,
			'is_active': 'on',
		})
		self.assertEqual(response.status_code, 200)
		self.administrador.refresh_from_db()
		self.assertEqual(self.administrador.perfil.rol, PerfilUsuario.Rol.ADMINISTRADOR)

	def test_paginacion_conserva_el_filtro_de_rol(self):
		for indice in range(12):
			self.modelo_usuario.objects.create_user(username=f'equipo_{indice}')
		response = self.client.get('/usuarios/?rol=auxiliar&page=2')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['page_obj'].number, 2)
		self.assertEqual(response.context['total_usuarios'], 13)
		self.assertContains(response, 'rol=auxiliar&amp;page=1')
