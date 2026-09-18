from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class PayhipPackagerModule(V2WrappedModule):
    name = "payhip_packager"
    module_py = "payhip_packager"
    class_name = "PayhipPackager"
