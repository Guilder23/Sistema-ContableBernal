from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.usuarios.models import PerfilUsuario

from .models import EntradaHistorial


class VisibilidadHistorialTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_superuser(username='admin_historial', password='ClaveLocal123!')
		self.auxiliar = User.objects.create_user(username='auxiliar_historial', password='ClaveLocal123!')
		self.otro_auxiliar = User.objects.create_user(username='otro_auxiliar_historial', password='ClaveLocal123!')
		self.secretario = User.objects.create_user(username='secretario_historial', password='ClaveLocal123!')
		self.secretario.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.secretario.perfil.save(update_fields=('rol', 'actualizado_en'))
		self.cliente = Cliente.objects.create(nombre='Cliente de auditoría')

	def _crear_evento(self, titulo, usuario):
		return EntradaHistorial.objects.create(
			cliente=self.cliente,
			usuario=usuario,
			tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
			seccion=EntradaHistorial.Seccion.CLIENTES,
			titulo=titulo,
		)

	def test_auxiliar_solo_ve_sus_acciones_de_todo_el_sistema(self):
		self._crear_evento('Acción propia del auxiliar', self.auxiliar)
		self._crear_evento('Acción de otro auxiliar', self.otro_auxiliar)
		self._crear_evento('Acción del administrador', self.admin)
		self._crear_evento('Evento automático', None)
		self.client.force_login(self.auxiliar)

		respuesta = self.client.get(reverse('historial:index'))

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context['total_entradas'], 1)
		self.assertContains(respuesta, 'Acción propia del auxiliar')
		self.assertNotContains(respuesta, 'Acción de otro auxiliar')
		self.assertNotContains(respuesta, 'Acción del administrador')
		self.assertNotContains(respuesta, 'Evento automático')
		self.assertContains(respuesta, 'Mostrando las acciones registradas por tu usuario')

	def test_administrador_ve_todas_las_acciones(self):
		self._crear_evento('Acción del auxiliar', self.auxiliar)
		self._crear_evento('Acción de otro auxiliar', self.otro_auxiliar)
		self._crear_evento('Acción del administrador', self.admin)
		self._crear_evento('Evento automático', None)
		self.client.force_login(self.admin)

		respuesta = self.client.get(reverse('historial:index'))

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context['total_entradas'], 4)
		self.assertContains(respuesta, 'Acción del auxiliar')
		self.assertContains(respuesta, 'Acción de otro auxiliar')
		self.assertContains(respuesta, 'Acción del administrador')
		self.assertContains(respuesta, 'Evento automático')
		self.assertNotContains(respuesta, 'Mostrando las acciones registradas por tu usuario')

	def test_secretario_conserva_acceso_global(self):
		self._crear_evento('Acción del auxiliar', self.auxiliar)
		self._crear_evento('Acción del secretario', self.secretario)
		self.client.force_login(self.secretario)

		respuesta = self.client.get(reverse('historial:index'))

		self.assertEqual(respuesta.context['total_entradas'], 2)
		self.assertContains(respuesta, 'Acción del auxiliar')
		self.assertContains(respuesta, 'Acción del secretario')

	def test_auxiliar_ve_eventos_globales_sin_cliente_si_son_suyos(self):
		EntradaHistorial.objects.create(
			cliente=None,
			usuario=self.auxiliar,
			tipo_accion=EntradaHistorial.TipoAccion.MODIFICACION,
			seccion=EntradaHistorial.Seccion.USUARIOS,
			referencia='Cuenta de prueba',
			titulo='Cuenta de usuario actualizada',
		)
		self.client.force_login(self.auxiliar)

		respuesta = self.client.get(reverse('historial:index'), {'seccion': 'usuarios'})

		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context['total_entradas'], 1)
		self.assertContains(respuesta, 'Cuenta de prueba')
		self.assertContains(respuesta, 'Usuarios')
		for seccion in ('dashboard', 'clientes', 'obligaciones', 'tareas', 'requerimientos', 'agenda', 'honorarios', 'ingresos', 'gastos', 'reportes', 'servicios', 'historial'):
			self.assertContains(respuesta, f'value="{seccion}"')