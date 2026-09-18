from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class GumroadPublisherModule(V2WrappedModule):
    name = "gumroad_publisher"
    module_py = "gumroad_publisher"
    class_name = "GumroadPublisher"
