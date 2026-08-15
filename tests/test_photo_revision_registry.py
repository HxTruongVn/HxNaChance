from workshops.photo.preview_controller import PhotoRevisionRegistry


def test_same_state_reuses_revision_even_after_returning_from_other_state():
    registry = PhotoRevisionRegistry()
    state_a = {"stick1": False, "preset": "portrait"}
    state_b = {"stick1": True, "preset": "portrait"}

    revision_a, fingerprint_a, is_new_a = registry.resolve(state_a)
    revision_b, fingerprint_b, is_new_b = registry.resolve(state_b)
    revision_again, fingerprint_again, is_new_again = registry.resolve(state_a)

    assert is_new_a is True
    assert is_new_b is True
    assert is_new_again is False
    assert revision_a != revision_b
    assert revision_again == revision_a
    assert fingerprint_again == fingerprint_a
    assert fingerprint_a != fingerprint_b


def test_state_fingerprint_is_independent_of_mapping_order_and_tuple_representation():
    registry = PhotoRevisionRegistry()
    first = {"options": {"stick1": False, "strength": 0.5}, "background": (255, 255, 255)}
    equivalent = {"background": [255, 255, 255], "options": {"strength": 0.5000001, "stick1": False}}

    assert registry.fingerprint(first) == registry.fingerprint(equivalent)


def test_distinct_state_gets_new_revision_only_once():
    registry = PhotoRevisionRegistry()
    state = {"stick1": True}

    first = registry.resolve(state)
    second = registry.resolve(dict(state))

    assert first[0] == second[0]
    assert first[1] == second[1]
    assert first[2] is True
    assert second[2] is False
