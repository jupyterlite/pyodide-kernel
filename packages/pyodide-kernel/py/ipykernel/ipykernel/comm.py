from comm import get_comm_manager

from pyodide_kernel.comm import Comm  # noqa

# Backward compat, in case someone was relying on importing CommManager?
CommManager = get_comm_manager  # noqa
