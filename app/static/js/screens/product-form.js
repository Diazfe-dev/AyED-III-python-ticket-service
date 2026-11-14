export function typeOptions(productTypes) {
  return productTypes.map((type) => ({ value: type.id, label: type.name }));
}

export function productFields(productTypes, product) {
  return [
    { name: "name", label: "Nombre", value: product?.name ?? "" },
    {
      name: "product_type_id",
      label: "Tipo",
      options: typeOptions(productTypes).map((option) => ({ ...option, value: String(option.value) })),
      placeholder: "Seleccione un tipo",
      value: product === undefined ? "" : String(product.product_type.id),
    },
  ];
}

export function writeBody(values) {
  return { name: values.name, product_type_id: Number(values.product_type_id) };
}
