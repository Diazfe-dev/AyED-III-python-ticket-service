from app.services.passwords import WerkzeugPasswordHasher


def test_werkzeug_hasher_stores_a_verifiable_hash_instead_of_the_password() -> None:
    """SPEC-USR-02 · TC-USR-02a"""
    hasher = WerkzeugPasswordHasher()

    password_hash = hasher.hash("password1")

    assert password_hash != "password1"
    assert "password1" not in password_hash
    assert hasher.verify(password_hash, "password1") is True
    assert hasher.verify(password_hash, "otra-clave") is False
