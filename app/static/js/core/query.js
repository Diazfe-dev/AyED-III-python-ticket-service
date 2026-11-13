export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50]);
export const PAGE_SIZE = DEFAULT_PAGE_SIZE;

function isEmpty(value) {
  return value === undefined || value === null || value === '';
}

export function normalizePageSize(value) {
  const size = Number(value);
  return PAGE_SIZE_OPTIONS.includes(size) ? size : DEFAULT_PAGE_SIZE;
}

export function listQuery(path, filters, page, pageSize = DEFAULT_PAGE_SIZE) {
  const params = new URLSearchParams();
  for (const [key, raw] of Object.entries(filters)) {
    const value = typeof raw === 'string' ? raw.trim() : raw;
    if (!isEmpty(value)) {
      params.set(key, String(value));
    }
  }
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return `${path}?${params.toString()}`;
}

export function listState(filters = {}, page = 1, pageSize = DEFAULT_PAGE_SIZE) {
  return { filters: { ...filters }, page, pageSize };
}

export function applyFilter(state, changes) {
  return listState({ ...state.filters, ...changes }, 1, state.pageSize);
}

export function changePageSize(state, size) {
  return listState(state.filters, 1, normalizePageSize(size));
}

export function nextPage(state) {
  return listState(state.filters, state.page + 1, state.pageSize);
}

export function previousPage(state) {
  return listState(state.filters, Math.max(1, state.page - 1), state.pageSize);
}

export function hasPrevious(state) {
  return state.page > 1;
}

export function hasNext({ page, page_size: pageSize, total }) {
  return page * pageSize < total;
}

export function pageInfo({ page, total }) {
  return { page, total };
}

export function lastValidPage(total, pageSize = DEFAULT_PAGE_SIZE) {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function reloadQuery(path, state) {
  return listQuery(path, state.filters, state.page, state.pageSize);
}

export function rangeText({ page, pageSize, total }) {
  if (total === 0) {
    return '0 de 0';
  }
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return `${first}–${last} de ${total}`;
}

export function memoryPage(items, page, pageSize) {
  const total = items.length;
  const shown = total === 0 ? 1 : Math.min(Math.max(1, page), lastValidPage(total, pageSize));
  const start = (shown - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), page: shown, pageSize, total };
}

export function flattenProductTypes(types, categories) {
  const names = new Map(categories.map((category) => [category.id, category.name]));
  return types.map((type) => ({
    id: type.id,
    name: type.name,
    category_id: type.category_id,
    category: names.get(type.category_id) ?? '',
  }));
}
