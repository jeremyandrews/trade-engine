#!/usr/bin/env bash

python ./manage.py migrate
/etc/init.d/nginx start
cron
gunicorn web.wsgi --config=/etc/gunicorn/config.py
