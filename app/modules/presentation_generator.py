from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class PresentationGeneratorModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.presentation_generator.PresentationGenerator
    """

    name = "presentation_generator"
    module_py = "presentation_generator"
    class_name = "PresentationGenerator"
