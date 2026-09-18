from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class EmailSequenceBuilderModule(V2WrappedModule):
    name = "email_sequence_builder"
    module_py = "email_sequence_builder"
    class_name = "EmailSequenceBuilder"
