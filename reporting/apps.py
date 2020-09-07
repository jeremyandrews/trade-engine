import logging
from logging.handlers import SysLogHandler
import socket

from django.apps import AppConfig


class ReportingConfig(AppConfig):
    name = 'reporting'
    verbose_name = "Exchange reporting"

    def ready(self):
        syslog_handler = SysLogHandler(
            address=('audit01', 514),
            socktype=socket.SOCK_STREAM,
        )

        format = logging.Formatter(
            '%(asctime)s|%(levelname)s|%(message)s'
        )
        syslog_handler.setFormatter(format)
        logger = logging.getLogger()
        logger.addHandler(syslog_handler)
        logger.setLevel(logging.INFO)
        logger.info("0|START|exchange started")
