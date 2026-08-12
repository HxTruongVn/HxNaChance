from core.identity import WorkshopIdentity


def test_identity_is_canonical_folder_name():
    identity = WorkshopIdentity.from_directory("/tmp/photo", {"workshop_id": "photo", "version": "1.0.0"})
    assert identity.workshop_id == "photo"
    assert identity.version == "1.0.0"
    assert identity.warnings == ()


def test_manifest_mismatch_is_visible_warning_not_second_identity():
    identity = WorkshopIdentity.from_directory("/tmp/photo", {"workshop_id": "other"})
    assert identity.workshop_id == "photo"
    assert identity.warnings
