from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class InfographicGeneratorModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.infographic_generator.InfographicGenerator
    """

    name = "infographic_generator"
    module_py = "infographic_generator"
    class_name = "InfographicGenerator"
