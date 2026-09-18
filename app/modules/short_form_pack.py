from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ShortFormPackModule(V2WrappedModule):
    name = "short_form_pack"
    module_py = "short_form_pack"
    class_name = "ShortFormPack"
