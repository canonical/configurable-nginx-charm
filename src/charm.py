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
        self.framework.observe(self.on.config_changed, self._on_config_changed)

        self._setup_ingress()

    def _setup_ingress(self):
        require_nginx_route(
            charm=self,
            service_hostname=self.app.name,
            service_name=self.app.name,
            service_port=80,
        )

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle config-changed event."""
        if not self._nginx_container.can_connect():
            event.defer()
            return

        nginx_config = self.config["nginx_config"]

        if not nginx_config:
            self.unit.status = ops.WaitingStatus("waiting for nginx config")
            return

        self._nginx_container.push("/etc/nginx/nginx.conf", nginx_config, make_dirs=True)

        process = self._nginx_container.exec(["nginx", "-s", "reload"])
        try:
            process.wait_output()
            self.unit.status = ops.ActiveStatus()
        except ops.pebble.ExecError as e:
            logger.error(e.stderr)
            self.unit.status = ops.BlockedStatus("nginx reload failed (invalid config?)")

    def _on_nginx_pebble_ready(self, event: ops.PebbleReadyEvent):
        """Handle Nginx pebble-ready event."""
        if not self._nginx_container.can_connect():
            event.defer()
            return

        self._nginx_container.add_layer(self._nginx_service_name, self._nginx_layer, combine=True)
        self._nginx_container.replan()
        self.unit.status = ops.ActiveStatus()

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
