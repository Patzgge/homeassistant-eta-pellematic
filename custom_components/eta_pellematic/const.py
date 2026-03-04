"""Constants for the ETA Pellematic Integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "eta_pellematic"
NAME = "ETA Heating"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_PORT = 8080

# Interval in seconds to poll the values
UPDATE_INTERVAL = 60
