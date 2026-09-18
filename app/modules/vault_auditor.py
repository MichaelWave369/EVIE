from __future__ import annotations

from app.modules.v2_wrapper import V2WrappedModule


class VaultAuditorModule(V2WrappedModule):
    name = "vault_auditor"
    module_py = "vault_auditor"
    class_name = "VaultAuditor"
