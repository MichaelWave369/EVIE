from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class TrendSurferModule(V2WrappedModule):
    name = "trend_surfer"
    module_py = "trend_surfer"
    class_name = "TrendSurfer"
