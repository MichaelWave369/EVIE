from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ComfyUIDirectorModule(V2WrappedModule):
    name = "comfyui_director"
    module_py = "comfyui_director"
    class_name = "ComfyUIDirector"
