#!/usr/bin/env python3
# Copyright 2023 Canonical
# See LICENSE file for licensing details.

"""Charmed Kubernetes Operator for a Configurable Nginx."""

import logging

import ops
from charms.nginx_ingress_integrator.v0.nginx_route import require_nginx_route

logger = logging.getLogger(__name__)


class ConfigurableNginxCharm(ops.CharmBase):
    """Charmed Kubernetes Operator for a Configurable Nginx."""

    def __init__(self, *args):
        super().__init__(*args)
        self._nginx_service_name = "nginx"
        self._nginx_container = self.unit.get_container("nginx")

        self.framework.observe(self.on.nginx_pebble_ready, self._on_nginx_pebble_ready)

        self._setup_ingress()

    def _setup_ingress(self):
        require_nginx_route(
            charm=self,
            service_hostname=self.app.name,
            service_name=self.app.name,
            service_port=80,
        )

    def _on_nginx_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Handle Nginx pebble-ready event."""
        if self._nginx_container.can_connect():
            self._nginx_container.add_layer(
                self._nginx_service_name, self._nginx_layer, combine=True
            )
            self._nginx_container.replan()
            self.unit.status = ops.ActiveStatus()
        else:
            event.defer()

    @property
    def _nginx_layer(self) -> ops.pebble.Layer:
        """Return the Nginx layer."""
        return ops.pebble.Layer(
            {
                "summary": "nginx layer",
                "description": "pebble config layer for nginx",
                "services": {
                    self._nginx_service_name: {
                        "override": "replace",
                        "summary": "nginx",
                        "command": "/docker-entrypoint.sh nginx -g 'daemon off;'",
                        "startup": "enabled",
                    }
                },
            }
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main(ConfigurableNginxCharm)  # type: ignore
