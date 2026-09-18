from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class SocialLaunchPackagerModule(V2WrappedModule):
    name = "social_launch_packager"
    module_py = "social_launch_packager"
    class_name = "SocialLaunchPackager"
