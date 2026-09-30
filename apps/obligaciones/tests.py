from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente

from .models import ConfiguracionCliente, DiaNoLaborable, Obligacion, TipoObligacion
from .services import calcular_vencimiento, generar_obligaciones, periodo_de_obligacion


class VencimientosTests(TestCase):
	def setUp(self):
		self.cliente = Cliente.objects.create(
			nombre='Empresa de prueba',
			nit='102030405-6',
			actividad=Cliente.Actividad.COMERCIAL,
		)

	def crear_tipo(self, codigo, regla, periodicidad=TipoObligacion.Periodicidad.MENSUAL, dia=None):
		return TipoObligacion.objects.create(
			codigo=codigo,
			nombre=codigo.upper(),
			periodicidad=periodicidad,
			regla_vencimiento=regla,
			dia_vencimiento=dia,
		)

	def test_dia_fijo_mueve_vencimiento_al_siguiente_habil(self):
		tipo = self.crear_tipo('rcv_test', TipoObligacion.ReglaVencimiento.DIA_FIJO, dia=9)
		DiaNoLaborable.objects.create(fecha=date(2026, 9, 9), descripcion='Feriado de prueba')
		self.assertEqual(
			calcular_vencimiento(tipo, self.cliente, date(2026, 8, 31), {date(2026, 9, 9)}),
			date(2026, 9, 10),
		)

	def test_nit_define_dia_y_ajusta_fin_de_semana(self):
		tipo = self.crear_tipo('iva_test', TipoObligacion.ReglaVencimiento.DIGITO_NIT)
		self.assertEqual(calcular_vencimiento(tipo, self.cliente, date(2026, 8, 31)), date(2026, 9, 21))

	def test_ultimo_habil_considera_feriados_configurados(self):
		tipo = self.crear_tipo('gestora_test', TipoObligacion.ReglaVencimiento.ULTIMO_HABIL)
		DiaNoLaborable.objects.create(fecha=date(2026, 9, 30), descripcion='Feriado de prueba')
		self.assertEqual(
			calcular_vencimiento(tipo, self.cliente, date(2026, 8, 31), {date(2026, 9, 30)}),
			date(2026, 9, 29),
		)

	def test_cierre_fiscal_usa_actividad_del_cliente(self):
		self.cliente.actividad = Cliente.Actividad.INDUSTRIAL
		tipo = self.crear_tipo(
			'iue_test',
			TipoObligacion.ReglaVencimiento.CIERRE_FISCAL_120,
			TipoObligacion.Periodicidad.ANUAL,
		)
		periodo_inicio, periodo_fin = periodo_de_obligacion(tipo, self.cliente, 2026, 0)
		self.assertEqual(periodo_inicio, date(2025, 4, 1))
		self.assertEqual(periodo_fin, date(2026, 3, 31))
		self.assertEqual(calcular_vencimiento(tipo, self.cliente, periodo_fin), date(2026, 7, 29))


class ObligacionesIntegracionTests(TestCase):
	def setUp(self):
		self.usuario = get_user_model().objects.create_superuser(username='admin', password='ClaveSegura123!')
		self.cliente = Cliente.objects.create(
			nombre='Cliente integrado',
			nit='123456-1',
			actividad=Cliente.Actividad.COMERCIAL,
		)
		self.tipo = TipoObligacion.objects.get(codigo='rcv')

	def test_generacion_es_idempotente(self):
		ConfiguracionCliente.objects.create(cliente=self.cliente, tipo=self.tipo, fecha_inicio=date(2026, 1, 1))
		primera = generar_obligaciones(TipoObligacion.Periodicidad.MENSUAL, 2026, 8)
		segunda = generar_obligaciones(TipoObligacion.Periodicidad.MENSUAL, 2026, 8)
		self.assertEqual(primera['creadas'], 1)
		self.assertEqual(segunda['creadas'], 0)
		self.assertEqual(segunda['existentes'], 1)
		self.assertEqual(Obligacion.objects.count(), 1)

	def test_configuracion_y_pantalla_se_integran_con_clientes(self):
		otro_cliente = Cliente.objects.create(
			nombre='Otro cliente sin seleccionar',
			nit='654321-2',
			actividad=Cliente.Actividad.COMERCIAL,
		)
		ConfiguracionCliente.objects.create(
			cliente=otro_cliente,
			tipo=self.tipo,
			fecha_inicio=date(2026, 1, 1),
		)
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('obligaciones:configurar_cliente'), {
			'cliente_id': self.cliente.pk,
			'fecha_inicio': '2026-09-30',
			'tipos': [self.tipo.pk],
			'periodicidad': 'mensual',
			'anio': '2026',
			'periodo_numero': '9',
		})
		self.assertEqual(respuesta.status_code, 302)
		self.assertTrue(ConfiguracionCliente.objects.filter(cliente=self.cliente, tipo=self.tipo, activa=True).exists())
		self.assertTrue(Obligacion.objects.filter(
			cliente=self.cliente,
			tipo=self.tipo,
			anio=2026,
			periodo_numero=9,
		).exists())
		self.assertFalse(Obligacion.objects.filter(cliente=otro_cliente).exists())
		respuesta = self.client.get(reverse('obligaciones:index'), {
			'periodicidad': 'mensual', 'anio': 2026, 'periodo_numero': 9, 'config_cliente': self.cliente.pk,
		})
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'Obligaciones aplicables')

	def test_listado_inicia_con_filtros_todos_y_muestra_todos_los_periodos(self):
		Obligacion.objects.create(
			cliente=self.cliente,
			tipo=self.tipo,
			anio=2026,
			periodo_numero=9,
			periodo_inicio=date(2026, 9, 1),
			periodo_fin=date(2026, 9, 30),
		)
		tipo_anual = TipoObligacion.objects.get(codigo='iue_500')
		Obligacion.objects.create(
			cliente=self.cliente,
			tipo=tipo_anual,
			anio=2025,
			periodo_numero=0,
			periodo_inicio=date(2025, 1, 1),
			periodo_fin=date(2025, 12, 31),
		)
		self.client.force_login(self.usuario)
		respuesta = self.client.get(reverse('obligaciones:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertEqual(respuesta.context['periodicidad'], '')
		self.assertEqual(respuesta.context['anio'], '')
		self.assertEqual(respuesta.context['periodo_numero'], '')
		self.assertEqual(respuesta.context['total_periodo'], 2)

	def test_generar_view_crea_periodo_configurado(self):
		ConfiguracionCliente.objects.create(cliente=self.cliente, tipo=self.tipo, fecha_inicio=date(2026, 1, 1))
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('obligaciones:generar'), {
			'periodicidad': 'mensual', 'anio': '2026', 'periodo_numero': '8',
		})
		self.assertEqual(respuesta.status_code, 302)
		self.assertEqual(Obligacion.objects.filter(cliente=self.cliente, tipo=self.tipo).count(), 1)

	def test_modal_muestra_catalogo_y_feriados_sin_enlace_a_admin(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.get(reverse('obligaciones:index'))
		self.assertContains(respuesta, 'Reglas y feriados')
		self.assertContains(respuesta, 'Días no laborables')
		self.assertNotContains(respuesta, 'admin:obligaciones_tipoobligacion_changelist')

	def test_crea_y_edita_tipo_desde_la_interfaz(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('obligaciones:crear_tipo'), {
			'nombre': 'Formulario extra',
			'periodicidad': 'mensual',
			'regla_vencimiento': 'dia_fijo',
			'dia_vencimiento': '12',
			'meses_despues_periodo': '1',
			'activa': 'on',
		})
		self.assertEqual(respuesta.status_code, 302)
		tipo = TipoObligacion.objects.get(codigo='formulario-extra')
		self.assertEqual(tipo.dia_vencimiento, 12)

		respuesta = self.client.post(reverse('obligaciones:editar_tipo', args=(tipo.pk,)), {
			'codigo': tipo.codigo,
			'nombre': 'Formulario extra mensual',
			'periodicidad': 'mensual',
			'regla_vencimiento': 'dia_fijo',
			'dia_vencimiento': '14',
			'meses_despues_periodo': '1',
			'activa': 'on',
		})
		self.assertEqual(respuesta.status_code, 302)
		tipo.refresh_from_db()
		self.assertEqual(tipo.nombre, 'Formulario extra mensual')
		self.assertEqual(tipo.dia_vencimiento, 14)

	def test_gestiona_feriados_desde_la_interfaz(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('obligaciones:crear_dia_no_laborable'), {
			'fecha': '2026-12-25', 'descripcion': 'Navidad',
		})
		self.assertEqual(respuesta.status_code, 302)
		dia = DiaNoLaborable.objects.get(fecha=date(2026, 12, 25))
		respuesta = self.client.post(reverse('obligaciones:eliminar_dia_no_laborable', args=(dia.pk,)))
		self.assertEqual(respuesta.status_code, 302)
		self.assertFalse(DiaNoLaborable.objects.filter(pk=dia.pk).exists())
