from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class HooksGeneratorModule(V2WrappedModule):
    name = "hooks_generator"
    module_py = "hooks_generator"
    class_name = "HooksGenerator"
