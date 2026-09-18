from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class CrossPollinatorModule(V2WrappedModule):
    name = "cross_pollinator"
    module_py = "cross_pollinator"
    class_name = "CrossPollinator"
