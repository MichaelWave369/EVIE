from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class StudyModuleModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.study_module.StudyModule
    """

    name = "study_module"
    module_py = "study_module"
    class_name = "StudyModule"
