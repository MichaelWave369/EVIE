from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ThumbnailGeneratorModule(V2WrappedModule):
    name = "thumbnail_generator"
    module_py = "thumbnail_generator"
    class_name = "ThumbnailGenerator"
