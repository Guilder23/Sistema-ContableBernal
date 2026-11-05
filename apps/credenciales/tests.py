from django.contrib.auth import get_user_model
from django.test import TestCase

from .permissions import CREDENCIALES_REAUTH_SESSION_KEY


class CredencialesReautenticacionTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_superuser(
			username='admin_credenciales',
			password='ClaveSegura123!',
		)
		self.client.force_login(self.usuario)

	def test_pagina_de_credenciales_solicita_reautenticacion(self):
		response = self.client.get('/credenciales/')

		self.assertRedirects(
			response,
			'/usuarios/login/?next=/credenciales/&reauth=credenciales',
		)

		login_page = self.client.get(response.url)
		self.assertContains(
			login_page,
			'Confirma tu identidad para acceder a Credenciales y Accesos.',
		)

	def test_reautenticacion_habilita_la_pagina(self):
		response = self.client.post(
			'/usuarios/login/',
			{
				'username': 'admin_credenciales',
				'password': 'ClaveSegura123!',
				'next': '/credenciales/',
				'reauth': 'credenciales',
			},
		)

		self.assertRedirects(response, '/credenciales/')
		self.assertTrue(self.client.session[CREDENCIALES_REAUTH_SESSION_KEY])
		self.assertEqual(self.client.get('/credenciales/').status_code, 200)

	def test_reautenticacion_no_permite_otra_cuenta(self):
		otra_cuenta = get_user_model().objects.create_user(
			username='otro_usuario',
			password='OtraClave123!',
		)

		response = self.client.post(
			'/usuarios/login/',
			{
				'username': otra_cuenta.username,
				'password': 'OtraClave123!',
				'next': '/credenciales/',
				'reauth': 'credenciales',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ingresa las credenciales de tu cuenta actual.')
		self.assertNotIn(CREDENCIALES_REAUTH_SESSION_KEY, self.client.session)

	def test_salir_de_credenciales_limpia_la_reautenticacion(self):
		session = self.client.session
		session[CREDENCIALES_REAUTH_SESSION_KEY] = True
		session.save()

		response = self.client.post('/credenciales/salir/')

		self.assertEqual(response.status_code, 200)
		self.assertNotIn(CREDENCIALES_REAUTH_SESSION_KEY, self.client.session)
		self.assertRedirects(
			self.client.get('/credenciales/'),
			'/usuarios/login/?next=/credenciales/&reauth=credenciales',
		)
