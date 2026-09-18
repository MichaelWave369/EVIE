from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ImageGeneratorV2Module(V2WrappedModule):
    name = "image_generator_v2"
    module_py = "image_generator_v2"
    class_name = "ImageGeneratorV2"
