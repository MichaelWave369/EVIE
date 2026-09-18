from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class SalesPageBuilderModule(V2WrappedModule):
    name = "sales_page_builder"
    module_py = "sales_page_builder"
    class_name = "SalesPageBuilder"
