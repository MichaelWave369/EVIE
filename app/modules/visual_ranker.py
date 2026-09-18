from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class VisualRankerModule(V2WrappedModule):
    name = "visual_ranker"
    module_py = "visual_ranker"
    class_name = "VisualRanker"
