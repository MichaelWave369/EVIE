from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class CompetitorDissectorModule(V2WrappedModule):
    name = "competitor_dissector"
    module_py = "competitor_dissector"
    class_name = "CompetitorDissector"
