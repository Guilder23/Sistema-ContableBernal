#!/usr/bin/env bash
set -o errexit

echo "==== Build de Sistema-ContableBernal ===="
echo "==== Actualizando pip ===="
pip install --upgrade pip

echo "==== Instalando dependencias ===="
pip install -r requirements.txt

echo "==== Recolectando archivos estáticos ===="
python manage.py collectstatic --no-input

echo "==== Ejecutando migraciones ===="
python manage.py migrate --noinput

echo "==== Configurando administrador inicial ===="
: "${DJANGO_SUPERUSER_PASSWORD:?Configura DJANGO_SUPERUSER_PASSWORD en Render}"
python manage.py shell -c '
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
user, created = User.objects.get_or_create(username=username)
if created:
	user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.save()
print(f"Administrador {username} listo")
'

echo "==== Build completado exitosamente ===="