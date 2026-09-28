from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.backup_recovery import BackupRecovery


class BackupRecoverySaver(BaseSaver[BackupRecovery]):
    """Saves BackupRecovery objects."""

    model = BackupRecovery
    key_patterns = ("{app}.BackupRecovery", "{app}.Components.{component}.BackupRecovery")
