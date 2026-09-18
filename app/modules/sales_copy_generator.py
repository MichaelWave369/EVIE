from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class SalesCopyGeneratorModule(V2WrappedModule):
    name = "sales_copy_generator"
    module_py = "sales_copy_generator"
    class_name = "SalesCopyGenerator"
