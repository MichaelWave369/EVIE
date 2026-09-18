from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class AudioGeneratorModule(V2WrappedModule):
    """v2 module adapter.

    Source implementation: app.modules_v2.audio_generator.AudioGenerator
    """

    name = "audio_generator"
    module_py = "audio_generator"
    class_name = "AudioGenerator"
