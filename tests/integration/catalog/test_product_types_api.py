from typing import Any

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.products import Category, ProductType
from tests.conftest import LoginAs, MakeCategory, MakeProduct, MakeProductType, MakeUser


@pytest.fixture
def hardware(make_category: MakeCategory) -> Category:
    return make_category("Hardware")


def stored_types(db_session: Session) -> list[tuple[str, int]]:
    db_session.expire_all()
    rows = db_session.execute(
        select(ProductType.name, ProductType.category_id).order_by(ProductType.id)
    )
    return [tuple(row) for row in rows]


def create_type(client: FlaskClient, **body: Any) -> Any:
    return client.post("/product-types", json=body)


def test_admin_creates_a_product_type(admin_client: FlaskClient, hardware: Category) -> None:
    """SPEC-PTY-03 · TC-PTY-03d"""
    response = create_type(admin_client, name="Notebook", category_id=hardware.id)

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "name": "Notebook", "category_id": hardware.id}


def test_create_product_type_in_unknown_category_is_not_found(
    admin_client: FlaskClient, db_session: Session
) -> None:
    """SPEC-PTY-04 · TC-PTY-04c"""
    response = create_type(admin_client, name="Notebook", category_id=9999)

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}
    assert stored_types(db_session) == []


def test_create_product_type_with_a_taken_name_in_the_category_is_a_conflict(
    admin_client: FlaskClient, hardware: Category, make_product_type: MakeProductType
) -> None:
    """SPEC-PTY-05 · TC-PTY-05e"""
    make_product_type(hardware, "Notebook")

    response = create_type(admin_client, name="nOTEBOOK", category_id=hardware.id)

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_product_type"}


def test_create_product_type_with_non_text_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, hardware: Category
) -> None:
    """SPEC-PTY-15 · TC-PTY-15h"""
    response = create_type(admin_client, name=123, category_id=hardware.id)

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "invalid"}
    assert stored_types(db_session) == []


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"category_id": "abc"}, "invalid"),
        ({"category_id": True}, "invalid"),
        ({}, "required"),
    ],
)
def test_create_product_type_with_malformed_or_missing_category_id_is_rejected(
    admin_client: FlaskClient,
    db_session: Session,
    hardware: Category,
    body: dict[str, Any],
    reason: str,
) -> None:
    """SPEC-PTY-20 · TC-PTY-20f"""
    response = create_type(admin_client, name="Notebook", **body)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"category_id": reason},
    }
    assert stored_types(db_session) == []


@pytest.fixture
def office(make_category: MakeCategory) -> Category:
    return make_category("Oficina")


@pytest.fixture
def notebook(hardware: Category, make_product_type: MakeProductType) -> ProductType:
    return make_product_type(hardware, "Notebook")


def test_admin_renames_and_moves_a_product_type(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, office: Category
) -> None:
    """SPEC-PTY-06 · TC-PTY-06e"""
    response = admin_client.patch(
        f"/product-types/{notebook.id}",
        json={"name": "Ultrabook", "category_id": office.id, "id": 99},
    )

    assert response.status_code == 200
    assert response.get_json() == {"id": notebook.id, "name": "Ultrabook", "category_id": office.id}
    assert stored_types(db_session) == [("Ultrabook", office.id)]


def test_update_unknown_product_type_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-06 · TC-PTY-06f"""
    response = admin_client.patch("/product-types/9999", json={"name": "X"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


def test_rename_product_type_to_an_empty_name_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-15 · TC-PTY-15i"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"name": ""})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"name": "required"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_move_product_type_to_unknown_category_is_not_found(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-16 · TC-PTY-16d"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"category_id": 9999})

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_move_product_type_onto_a_taken_name_is_a_conflict(
    admin_client: FlaskClient,
    db_session: Session,
    notebook: ProductType,
    hardware: Category,
    office: Category,
    make_product_type: MakeProductType,
) -> None:
    """SPEC-PTY-16 · TC-PTY-16e"""
    make_product_type(office, "notebook")

    response = admin_client.patch(f"/product-types/{notebook.id}", json={"category_id": office.id})

    assert response.status_code == 409
    assert response.get_json() == {"error": "duplicate_product_type"}
    assert stored_types(db_session) == [("Notebook", hardware.id), ("notebook", office.id)]


def test_rename_product_type_stores_the_name_without_surrounding_spaces(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-19 · TC-PTY-19d"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"name": "  Ultrabook "})

    assert response.status_code == 200
    assert response.get_json()["name"] == "Ultrabook"
    assert stored_types(db_session) == [("Ultrabook", hardware.id)]


def test_move_product_type_with_malformed_category_id_is_rejected(
    admin_client: FlaskClient, db_session: Session, notebook: ProductType, hardware: Category
) -> None:
    """SPEC-PTY-20 · TC-PTY-20g"""
    response = admin_client.patch(f"/product-types/{notebook.id}", json={"category_id": 0})

    assert response.status_code == 400
    assert response.get_json()["fields"] == {"category_id": "invalid"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_admin_deletes_a_product_type(admin_client: FlaskClient, notebook: ProductType) -> None:
    """SPEC-PTY-07 · TC-PTY-07d"""
    response = admin_client.delete(f"/product-types/{notebook.id}")

    assert response.status_code == 204
    assert response.get_data() == b""
    groups = admin_client.get("/product-types").get_json()
    assert [group["product_types"] for group in groups] == [[]]


def test_delete_unknown_product_type_is_not_found(admin_client: FlaskClient) -> None:
    """SPEC-PTY-07 · TC-PTY-07e"""
    response = admin_client.delete("/product-types/9999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "product_type_not_found"}


def test_delete_product_type_with_products_is_a_conflict(
    admin_client: FlaskClient,
    db_session: Session,
    notebook: ProductType,
    hardware: Category,
    make_product: MakeProduct,
) -> None:
    """SPEC-PTY-08 · TC-PTY-08c"""
    make_product(notebook, "XPS 13")

    response = admin_client.delete(f"/product-types/{notebook.id}")

    assert response.status_code == 409
    assert response.get_json() == {"error": "product_type_in_use"}
    assert stored_types(db_session) == [("Notebook", hardware.id)]


def test_any_user_lists_product_types_grouped_by_category(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    make_category: MakeCategory,
    make_product_type: MakeProductType,
) -> None:
    """SPEC-PTY-22 · TC-PTY-22d"""
    redes, audio, hardware = (make_category(n) for n in ["Redes", "audio", "Hardware"])
    router = make_product_type(redes, "Router")
    access_point = make_product_type(redes, "Access point")
    notebook = make_product_type(hardware, "Notebook")
    login_as(client, make_user(role="Client"))

    response = client.get("/product-types")

    def type_json(product_type: ProductType, category: Category) -> dict[str, Any]:
        return {"id": product_type.id, "name": product_type.name, "category_id": category.id}

    assert response.status_code == 200
    assert response.get_json() == [
        {"id": audio.id, "name": "audio", "product_types": []},
        {"id": hardware.id, "name": "Hardware", "product_types": [type_json(notebook, hardware)]},
        {
            "id": redes.id,
            "name": "Redes",
            "product_types": [type_json(access_point, redes), type_json(router, redes)],
        },
    ]


def test_listing_product_types_of_one_category_returns_only_its_group(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    hardware: Category,
    office: Category,
    make_product_type: MakeProductType,
) -> None:
    """SPEC-PTY-10 · TC-PTY-10b"""
    notebook = make_product_type(hardware, "Notebook")
    make_product_type(office, "Silla")
    login_as(client, make_user(role="Representative"))

    response = client.get(f"/product-types?category_id={hardware.id}")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "id": hardware.id,
            "name": "Hardware",
            "product_types": [{"id": notebook.id, "name": "Notebook", "category_id": hardware.id}],
        }
    ]


def test_listing_product_types_of_unknown_category_is_not_found(
    admin_client: FlaskClient,
) -> None:
    """SPEC-PTY-18 · TC-PTY-18c"""
    response = admin_client.get("/product-types?category_id=9999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}


def test_listing_product_types_of_a_category_beyond_sqlite_integers_is_not_found(
    admin_client: FlaskClient,
) -> None:
    """SPEC-PTY-18 · TC-PTY-18e"""
    response = admin_client.get("/product-types?category_id=99999999999999999999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "category_not_found"}


@pytest.mark.parametrize("query", ["category_id=abc", "category_id="])
def test_listing_product_types_with_malformed_category_id_is_rejected(
    admin_client: FlaskClient, query: str
) -> None:
    """SPEC-PTY-20 · TC-PTY-20h"""
    response = admin_client.get(f"/product-types?{query}")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"category_id": "invalid"},
    }


@pytest.fixture
def reference_types(
    make_category: MakeCategory, make_product_type: MakeProductType
) -> dict[str, Category]:
    categories = {n: make_category(n) for n in ["Redes", "audio", "Hardware", "Electrónica"]}
    for category, names in [
        ("Redes", ["Router", "Access point"]),
        ("Hardware", ["Notebook", "Ruteador USB"]),
        ("Electrónica", ["Cámara"]),
    ]:
        for name in names:
            make_product_type(categories[category], name)
    return categories


def group_names(response: Any) -> list[tuple[str, list[str]]]:
    return [
        (group["name"], [item["name"] for item in group["product_types"]])
        for group in response.get_json()
    ]


def test_listing_product_types_filters_by_q(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    reference_types: dict[str, Category],
) -> None:
    """SPEC-PTY-23 · TC-PTY-23f"""
    login_as(client, make_user(role="Representative"))

    everywhere = client.get("/product-types?q=UTE")
    in_redes = client.get(f"/product-types?category_id={reference_types['Redes'].id}&q=UTE")

    assert everywhere.status_code == 200
    assert group_names(everywhere) == [("Hardware", ["Ruteador USB"]), ("Redes", ["Router"])]
    assert in_redes.status_code == 200
    assert group_names(in_redes) == [("Redes", ["Router"])]


def test_listing_product_types_with_empty_q_equals_no_q(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    reference_types: dict[str, Category],
) -> None:
    """SPEC-PTY-23 · TC-PTY-23g"""
    login_as(client, make_user(role="Representative"))

    response = client.get("/product-types?q=")

    assert response.status_code == 200
    assert response.get_json() == client.get("/product-types").get_json()
    assert "audio" in [name for name, _ in group_names(response)]


def test_listing_product_types_with_malformed_category_id_and_q_is_rejected(
    admin_client: FlaskClient,
) -> None:
    """SPEC-PTY-23 · TC-PTY-23g"""
    response = admin_client.get("/product-types?category_id=abc&q=UTE")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "validation_error",
        "fields": {"category_id": "invalid"},
    }


@pytest.mark.parametrize("query", ["page=abc", "page=1&page_size=1"])
def test_listing_product_types_ignores_page_and_page_size(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    reference_types: dict[str, Category],
    query: str,
) -> None:
    """SPEC-PTY-24 · TC-PTY-24b"""
    login_as(client, make_user(role="Representative"))

    response = client.get(f"/product-types?{query}")

    assert response.status_code == 200
    assert response.get_json() == client.get("/product-types").get_json()


def test_listing_product_types_keeps_q_when_page_is_sent(
    client: FlaskClient,
    login_as: LoginAs,
    make_user: MakeUser,
    reference_types: dict[str, Category],
) -> None:
    """SPEC-PTY-24 · TC-PTY-24b"""
    login_as(client, make_user(role="Representative"))

    response = client.get("/product-types?q=UTE&page=2")

    assert response.status_code == 200
    assert group_names(response) == [("Hardware", ["Ruteador USB"]), ("Redes", ["Router"])]
