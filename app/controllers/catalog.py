"""Catalog endpoints: categories, product types and products (the CatalogController)."""

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app.auth import admin_required, login_required
from app.controllers.serializers import (
    category_group_json,
    category_json,
    json_body,
    product_json,
    product_type_json,
)
from app.wiring import get_catalog_service, get_product_service

bp = Blueprint("catalog", __name__)

PRODUCT_TYPE_KEYS = ("name", "category_id")
PRODUCT_KEYS = ("name", "product_type_id")


@bp.get("/categories")
@login_required
def list_categories() -> ResponseReturnValue:
    return [category_json(category) for category in get_catalog_service().list_categories()]


@bp.post("/categories")
@admin_required
def create_category() -> ResponseReturnValue:
    category = get_catalog_service().create_category(json_body().get("name"))
    return category_json(category), 201


@bp.patch("/categories/<int:category_id>")
@admin_required
def update_category(category_id: int) -> ResponseReturnValue:
    category = get_catalog_service().update_category(category_id, name=json_body().get("name"))
    return category_json(category)


@bp.delete("/categories/<int:category_id>")
@admin_required
def delete_category(category_id: int) -> ResponseReturnValue:
    get_catalog_service().delete_category(category_id)
    return "", 204


@bp.post("/product-types")
@admin_required
def create_product_type() -> ResponseReturnValue:
    body = json_body()
    product_type = get_catalog_service().create_product_type(
        name=body.get("name"), category_id=body.get("category_id")
    )
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
    groups = get_catalog_service().list_product_types(request.args.get("category_id"))
    return [category_group_json(category) for category in groups]


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
        category_id=request.args.get("category_id"),
        product_type_id=request.args.get("product_type_id"),
    )
    return [product_json(product) for product in products]


@bp.get("/products/available")
@login_required
def list_available_products() -> ResponseReturnValue:
    return [product_json(product) for product in get_product_service().list_available_products()]


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
