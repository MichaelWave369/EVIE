from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ProductCoverGeneratorModule(V2WrappedModule):
    name = "product_cover_generator"
    module_py = "product_cover_generator"
    class_name = "ProductCoverGenerator"
