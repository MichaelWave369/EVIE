from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class ContentExporterModule(V2WrappedModule):
    name = "content_exporter"
    module_py = "content_exporter"
    class_name = "ContentExporter"
