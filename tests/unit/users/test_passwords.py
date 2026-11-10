from app.services.passwords import WerkzeugPasswordHasher


def test_werkzeug_hasher_stores_a_verifiable_hash_instead_of_the_password() -> None:
    """SPEC-USR-02 · TC-USR-02a"""
    hasher = WerkzeugPasswordHasher()

    password_hash = hasher.hash("password1")

    assert password_hash != "password1"
    assert "password1" not in password_hash
    assert hasher.verify(password_hash, "password1") is True
    assert hasher.verify(password_hash, "otra-clave") is False


def test_werkzeug_dummy_hash_is_a_real_hash_computed_once_per_process() -> None:
    """SPEC-USR-24 · TC-USR-24c"""
    first, second = WerkzeugPasswordHasher(), WerkzeugPasswordHasher()

    dummy_hash = first.dummy_hash()

    assert second.dummy_hash() is dummy_hash
    assert first.verify(dummy_hash, "password1") is False
    assert first.verify(dummy_hash, "") is False
    assert dummy_hash.split("$")[0] == first.hash("password1").split("$")[0]
