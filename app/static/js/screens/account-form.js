import { roleLabel } from "../core/labels.js";

const ROLE_OPTIONS = [
  { value: "Admin", label: roleLabel("Admin") },
  { value: "Representative", label: roleLabel("Representative") },
  { value: "Client", label: roleLabel("Client") },
];
const CHANNEL_OPTIONS = [
  { value: "mail", label: "Correo" },
  { value: "whatsapp", label: "WhatsApp" },
];

export function accountFields(creating, user, { withRole = true } = {}) {
  return [
    { name: "name", label: "Nombre", value: user?.name ?? "" },
    { name: "email", label: "Email", type: "email", value: user?.email ?? "" },
    ...(creating
      ? [
          ...(withRole
            ? [{ name: "role", label: "Rol", options: ROLE_OPTIONS, placeholder: "Seleccione un rol" }]
            : []),
          { name: "password", label: "Contraseña", type: "password", autocomplete: "new-password" },
        ]
      : []),
    {
      name: "preferred_channel",
      label: "Canal",
      options: CHANNEL_OPTIONS,
      placeholder: "Sin especificar",
      value: user?.preferred_channel ?? "",
    },
  ];
}
