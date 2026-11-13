import { el } from "./render.js";

const CONTROLS = "input, select, textarea";

function optionList(options, placeholder) {
  const placeholders = placeholder === undefined ? [] : [{ value: "", label: placeholder }];
  return [...placeholders, ...options].map((option) =>
    el("option", { value: option.value }, [option.label]),
  );
}

function buildField(prefix, field) {
  const id = `${prefix}-${field.name}`;
  const control =
    field.options === undefined
      ? el("input", {
          type: field.type ?? "text",
          id,
          name: field.name,
          autocomplete: field.autocomplete ?? "off",
          value: field.value ?? "",
        })
      : el("select", { id, name: field.name }, optionList(field.options, field.placeholder));
  if (field.options !== undefined && field.value !== undefined) {
    control.value = field.value;
  }
  const mark = el("p", { id: `${id}-mark`, class: "field-mark" });
  mark.hidden = true;
  return {
    field,
    control,
    mark,
    element: el("div", { class: "field" }, [el("label", { for: id }, [field.label]), control, mark]),
  };
}

export function markControl(control, mark, text) {
  mark.textContent = text ?? "";
  mark.hidden = text === null || text === undefined;
  if (mark.hidden) {
    control.removeAttribute("aria-invalid");
    control.removeAttribute("aria-describedby");
  } else {
    control.setAttribute("aria-invalid", "true");
    control.setAttribute("aria-describedby", mark.id);
  }
}

export function createFields(prefix, fields) {
  const built = fields.map((field) => buildField(prefix, field));
  return {
    elements: built.map((entry) => entry.element),
    values: () => Object.fromEntries(built.map((entry) => [entry.field.name, entry.control.value])),
    clearPasswords() {
      for (const entry of built) {
        if (entry.field.type === "password") {
          entry.control.value = "";
        }
      }
    },
    setMarks(marks) {
      for (const entry of built) {
        markControl(entry.control, entry.mark, marks[entry.field.name] ?? null);
      }
    },
    controls: () => built.map((entry) => entry.control),
  };
}

export function firstControl(container) {
  return container.querySelector(CONTROLS);
}
