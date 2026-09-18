from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class YoutubePublisherModule(V2WrappedModule):
    name = "youtube_publisher"
    module_py = "youtube_publisher"
    class_name = "YoutubePublisher"
