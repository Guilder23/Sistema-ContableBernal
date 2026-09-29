from django.contrib.auth import get_user_model
from django.test import TestCase


class ModulePageTests(TestCase):
	pages = [
		('/dashboard/', 'dashboard', 'dashboard'),
		('/usuarios/', 'usuarios', 'usuarios'),
		('/clientes/', 'clientes', 'clientes'),
		('/credenciales/', 'credenciales', 'credenciales'),
		('/obligaciones/', 'obligaciones', 'obligaciones'),
		('/tareas/', 'tareas', 'tareas'),
		('/honorarios/', 'honorarios', 'honorarios'),
		('/ingresos/', 'ingresos', 'ingresos'),
		('/gastos/', 'gastos', 'gastos'),
		('/servicios/', 'servicios', 'servicios'),
		('/requerimientos/', 'requerimientos', 'requerimientos'),
		('/agenda/', 'agenda', 'agenda'),
		('/documentos/', 'documentos', 'documentos'),
		('/historial/', 'historial', 'historial'),
		('/notificaciones/', 'notificaciones', 'notificaciones'),
		('/reportes/', 'reportes', 'reportes'),
		('/configuracion/', 'configuracion', 'configuracion'),
	]

	def setUp(self):
		user_model = get_user_model()
		self.user = user_model.objects.create_user(username='auxiliar', password='ClaveLocal123!')
		self.admin = user_model.objects.create_superuser(username='administrador', password='ClaveLocal123!')

	def test_login_is_manual_html_and_authenticates(self):
		response = self.client.get('/usuarios/login/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'name="username"')
		self.assertContains(response, 'name="password"')
		self.assertContains(response, 'css/usuarios/login.css')
		self.assertContains(response, 'js/usuarios/login.js')

		response = self.client.post(
			'/usuarios/login/',
			{'username': 'auxiliar', 'password': 'ClaveLocal123!'},
		)
		self.assertRedirects(response, '/dashboard/')

	def test_module_pages_require_authentication(self):
		response = self.client.get('/clientes/')
		self.assertRedirects(response, '/usuarios/login/?next=/clientes/')

	def test_each_module_renders_its_own_css_and_javascript(self):
		self.client.force_login(self.admin)
		for path, asset_folder, asset_name in self.pages:
			with self.subTest(path=path):
				response = self.client.get(path)
				self.assertEqual(response.status_code, 200)
				self.assertContains(response, f'css/{asset_folder}/{asset_name}.css')
				self.assertContains(response, f'js/{asset_folder}/{asset_name}.js')
