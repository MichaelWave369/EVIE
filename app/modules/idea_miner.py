from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class IdeaMinerModule(V2WrappedModule):
    name = "idea_miner"
    module_py = "idea_miner"
    class_name = "IdeaMiner"
