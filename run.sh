#!/bin/sh

nginx -g 'pid /tmp/nginx.pid;'

uwsgi --socket 0.0.0.0:3000 \
  --plugins python3 \
  --protocol uwsgi \
  --module "wsgi"
