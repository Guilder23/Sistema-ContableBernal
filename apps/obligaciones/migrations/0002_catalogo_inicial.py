from django.db import migrations


def crear_catalogo(apps, schema_editor):
    TipoObligacion = apps.get_model('obligaciones', 'TipoObligacion')
    registros = (
        ('rcv', 'RCV', 'mensual', 'dia_fijo', 9),
        ('iva_200', 'IVA 200', 'mensual', 'digito_nit', None),
        ('it_400', 'IT 400', 'mensual', 'digito_nit', None),
        ('gestora', 'Gestora', 'mensual', 'ultimo_habil', None),
        ('ministerio', 'Ministerio', 'mensual', 'dia_fijo', 15),
        ('rc_iva_610', 'RC-IVA 610', 'trimestral', 'manual', None),
        ('anexo_110', 'Anexo 110', 'trimestral', 'manual', None),
        ('estados_financieros', 'Estados financieros', 'anual', 'cierre_fiscal_120', None),
        ('iue_500', 'IUE 500', 'anual', 'cierre_fiscal_120', None),
        ('formulario_605', 'Formulario 605', 'anual', 'cierre_fiscal_120', None),
    )
    for codigo, nombre, periodicidad, regla, dia in registros:
        TipoObligacion.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'periodicidad': periodicidad,
                'regla_vencimiento': regla,
                'dia_vencimiento': dia,
                'meses_despues_periodo': 1,
                'activa': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('obligaciones', '0001_initial')]
    operations = [migrations.RunPython(crear_catalogo, migrations.RunPython.noop)]
