from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class PredictionTrackerModule(V2WrappedModule):
    name = "prediction_tracker"
    module_py = "prediction_tracker"
    class_name = "PredictionTracker"
