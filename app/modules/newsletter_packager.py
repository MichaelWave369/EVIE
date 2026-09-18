from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class NewsletterPackagerModule(V2WrappedModule):
    name = "newsletter_packager"
    module_py = "newsletter_packager"
    class_name = "NewsletterPackager"
