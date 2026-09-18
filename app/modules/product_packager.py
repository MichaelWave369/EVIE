from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ProductPackagerModule(V2WrappedModule):
    name = "product_packager"
    module_py = "product_packager"
    class_name = "ProductPackager"
