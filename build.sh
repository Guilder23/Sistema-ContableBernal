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
python manage.py crear_admin

echo "==== Build completado exitosamente ===="