"""Catalog endpoints: product types and products (the CatalogController)."""

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app.auth import admin_required, login_required
from app.controllers.listing import listing_json
from app.controllers.serializers import (
    json_body,
    product_json,
    product_type_json,
)
from app.wiring import get_catalog_service, get_product_service

bp = Blueprint("catalog", __name__)

PRODUCT_TYPE_KEYS = ("name", "category_id")
PRODUCT_KEYS = ("name", "product_type_id")


@bp.post("/product-types")
@admin_required
def create_product_type() -> ResponseReturnValue:
    product_type = get_catalog_service().create_product_type(json_body().get("name"))
    return product_type_json(product_type), 201


@bp.patch("/product-types/<int:product_type_id>")
@admin_required
def update_product_type(product_type_id: int) -> ResponseReturnValue:
    body = json_body()
    changes = {key: body[key] for key in PRODUCT_TYPE_KEYS if key in body}
    product_type = get_catalog_service().update_product_type(product_type_id, **changes)
    return product_type_json(product_type)


@bp.delete("/product-types/<int:product_type_id>")
@admin_required
def delete_product_type(product_type_id: int) -> ResponseReturnValue:
    get_catalog_service().delete_product_type(product_type_id)
    return "", 204


@bp.get("/product-types")
@login_required
def list_product_types() -> ResponseReturnValue:
    product_types = get_catalog_service().list_product_types(q=request.args.get("q"))
    return [product_type_json(product_type) for product_type in product_types]


@bp.post("/products")
@admin_required
def create_product() -> ResponseReturnValue:
    body = json_body()
    product = get_product_service().create_product(
        name=body.get("name"), product_type_id=body.get("product_type_id")
    )
    return product_json(product), 201


@bp.get("/products")
@login_required
def list_products() -> ResponseReturnValue:
    products = get_product_service().list_products(
        product_type_id=request.args.get("product_type_id"),
        **_listing_args("q", "is_active", "page", "page_size"),
    )
    return listing_json(products, product_json)


@bp.get("/products/available")
@login_required
def list_available_products() -> ResponseReturnValue:
    products = get_product_service().list_available_products(
        **_listing_args("q", "page", "page_size")
    )
    return listing_json(products, product_json)


def _listing_args(*names: str) -> dict[str, str | None]:
    return {name: request.args.get(name) for name in names}


@bp.patch("/products/<int:product_id>")
@admin_required
def update_product(product_id: int) -> ResponseReturnValue:
    body = json_body()
    changes = {key: body[key] for key in PRODUCT_KEYS if key in body}
    product = get_product_service().update_product(product_id, **changes)
    return product_json(product)


@bp.post("/products/<int:product_id>/deactivate")
@admin_required
def deactivate_product(product_id: int) -> ResponseReturnValue:
    return product_json(get_product_service().deactivate_product(product_id))


@bp.post("/products/<int:product_id>/activate")
@admin_required
def activate_product(product_id: int) -> ResponseReturnValue:
    return product_json(get_product_service().activate_product(product_id))
