from app.models import UserDocument
from app.models.user_documents import UserDocument as LegacyUserDocument


def test_document_module_paths_share_one_mapping():
    # Both branch APIs must resolve to the same mapper/table registration.
    assert LegacyUserDocument is UserDocument
