import comm
from comm import BaseComm, get_comm_manager, CommManager  # noqa

from IPython.core.getipython import get_ipython


class Comm(BaseComm):
    def publish_msg(self, msg_type, data=None, metadata=None, buffers=None, **keys):
        """Helper for sending a comm message on IOPub"""
        data = {} if data is None else data
        metadata = {} if metadata is None else metadata
        content = dict(data=data, comm_id=self.comm_id, **keys)

        if buffers is not None:
            buffers = [(b.tobytes() if hasattr(b, "tobytes") else b) for b in buffers]

        get_ipython().send_comm(
            msg_type,
            content,
            metadata,
            self.topic,
            buffers,
        )


comm.create_comm = Comm
