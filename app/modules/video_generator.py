from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class VideoGeneratorModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.video_generator.VideoGenerator
    """

    name = "video_generator"
    module_py = "video_generator"
    class_name = "VideoGenerator"
