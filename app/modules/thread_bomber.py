from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ThreadBomberModule(V2WrappedModule):
    name = "thread_bomber"
    module_py = "thread_bomber"
    class_name = "ThreadBomber"
