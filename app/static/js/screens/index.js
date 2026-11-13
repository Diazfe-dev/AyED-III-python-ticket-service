import * as account from "./account.js";
import * as boot from "./boot.js";
import * as categories from "./categories.js";
import * as login from "./login.js";
import * as notFound from "./not-found.js";
import * as productTypes from "./product-types.js";
import * as products from "./products.js";
import * as ticketDetail from "./ticket-detail.js";
import * as ticketNew from "./ticket-new.js";
import * as ticketsList from "./tickets-list.js";
import * as users from "./users.js";

export const screens = {
  boot,
  login,
  "not-found": notFound,
  account,
  "tickets-list": ticketsList,
  "ticket-detail": ticketDetail,
  "ticket-new": ticketNew,
  users,
  categories,
  "product-types": productTypes,
  products,
};
