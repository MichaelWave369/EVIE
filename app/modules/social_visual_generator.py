from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class SocialVisualGeneratorModule(V2WrappedModule):
    name = "social_visual_generator"
    module_py = "social_visual_generator"
    class_name = "SocialVisualGenerator"
