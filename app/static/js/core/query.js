export const PAGE_SIZE = 20;

function isEmpty(value) {
  return value === undefined || value === null || value === '';
}

export function listQuery(path, filters, page) {
  const params = new URLSearchParams();
  for (const [key, raw] of Object.entries(filters)) {
    const value = typeof raw === 'string' ? raw.trim() : raw;
    if (!isEmpty(value)) {
      params.set(key, String(value));
    }
  }
  params.set('page', String(page));
  params.set('page_size', String(PAGE_SIZE));
  return `${path}?${params.toString()}`;
}

export function listState(filters = {}, page = 1) {
  return { filters: { ...filters }, page };
}

export function applyFilter(state, changes) {
  return listState({ ...state.filters, ...changes }, 1);
}

export function nextPage(state) {
  return listState(state.filters, state.page + 1);
}

export function previousPage(state) {
  return listState(state.filters, Math.max(1, state.page - 1));
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

export function lastValidPage(total) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

export function reloadQuery(path, state) {
  return listQuery(path, state.filters, state.page);
}
