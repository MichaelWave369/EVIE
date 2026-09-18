from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class PublishControllerModule(V2WrappedModule):
    name = "publish_controller"
    module_py = "publish_controller"
    class_name = "PublishController"
