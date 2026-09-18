from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class DistributionGeneratorModule(V2WrappedModule):
    name = "distribution_generator"
    module_py = "distribution_generator"
    class_name = "DistributionGenerator"
