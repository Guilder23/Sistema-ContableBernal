from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PanelAdministracionTests(TestCase):
	def test_panel_enlaza_a_gestion_de_obligaciones(self):
		usuario = get_user_model().objects.create_user(username='admin', password='ClaveSegura123!')
		self.client.force_login(usuario)
		respuesta = self.client.get(reverse('configuracion:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, reverse('obligaciones:index'))
		self.assertContains(respuesta, 'Gestionar obligaciones')
