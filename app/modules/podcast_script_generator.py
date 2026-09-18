from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class PodcastScriptGeneratorModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.podcast_script_generator.PodcastScriptGenerator
    """

    name = "podcast_script_generator"
    module_py = "podcast_script_generator"
    class_name = "PodcastScriptGenerator"
