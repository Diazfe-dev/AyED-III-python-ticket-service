"""Catalog endpoints: categories and product types (the CatalogController of the diagrams)."""

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

from app.auth import admin_required, login_required
from app.controllers.serializers import (
    category_group_json,
    category_json,
    json_body,
    product_type_json,
)
from app.wiring import get_catalog_service

bp = Blueprint("catalog", __name__)

PRODUCT_TYPE_KEYS = ("name", "category_id")


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
