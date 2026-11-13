import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  applyFilter,
  changePageSize,
  flattenProductTypes,
  hasNext,
  hasPrevious,
  lastValidPage,
  listState,
  listQuery,
  nextPage,
  memoryPage,
  normalizePageSize,
  pageInfo,
  previousPage,
  rangeText,
  reloadQuery,
} from '../../../app/static/js/core/query.js';

test('SPEC-UI-23 builds the ticket list URL with the state filter (TC-UI-23a)', () => {
  assert.equal(
    listQuery('/tickets', { state: 'InProgress' }, 1),
    '/tickets?state=InProgress&page=1&page_size=20',
  );
});

test('SPEC-UI-107 trims q and omits it when empty (TC-UI-107a)', () => {
  assert.equal(listQuery('/tickets', { q: '  impresora ' }, 1), '/tickets?q=impresora&page=1&page_size=20');
  assert.equal(listQuery('/tickets', { q: '' }, 1), '/tickets?page=1&page_size=20');
  assert.equal(listQuery('/tickets', { q: '   ' }, 1), '/tickets?page=1&page_size=20');
});

test('SPEC-UI-108 sends the order asc and desc (TC-UI-108a)', () => {
  assert.equal(listQuery('/tickets', { order: 'asc' }, 1), '/tickets?order=asc&page=1&page_size=20');
  assert.equal(listQuery('/tickets', { order: 'desc' }, 1), '/tickets?order=desc&page=1&page_size=20');
});

test('SPEC-UI-24 sends the client_id filter (TC-UI-24a)', () => {
  assert.equal(listQuery('/tickets', { client_id: 7 }, 1), '/tickets?client_id=7&page=1&page_size=20');
});

test('SPEC-UI-25 sends the representative_id filter (TC-UI-25a)', () => {
  assert.equal(
    listQuery('/tickets', { representative_id: 3 }, 1),
    '/tickets?representative_id=3&page=1&page_size=20',
  );
});

test('SPEC-UI-26 always sends page and page_size on paginated lists (TC-UI-26a)', () => {
  assert.equal(PAGE_SIZE, 20);
  for (const path of ['/users', '/products', '/tickets']) {
    assert.equal(listQuery(path, {}, 1), `${path}?page=1&page_size=20`);
  }
});

test('SPEC-UI-23 omits empty filters (TC-UI-23a)', () => {
  assert.equal(
    listQuery('/tickets', { state: '', client_id: null, representative_id: undefined }, 2),
    '/tickets?page=2&page_size=20',
  );
});

test('SPEC-UI-101 reads the page and total from a page body (TC-UI-101a)', () => {
  assert.deepEqual(pageInfo({ page: 2, page_size: 20, total: 45 }), { page: 2, total: 45 });
});

test('SPEC-UI-102 next page keeps the filters and moves forward (TC-UI-102a)', () => {
  const next = nextPage(listState({ state: 'Open', q: 'x' }, 1));
  assert.equal(next.page, 2);
  assert.deepEqual(next.filters, { state: 'Open', q: 'x' });
  assert.equal(reloadQuery('/tickets', next), '/tickets?state=Open&q=x&page=2&page_size=20');
});

test('SPEC-UI-103 previous page keeps the filters and moves back (TC-UI-103a)', () => {
  const prev = previousPage(listState({ state: 'Open', q: 'x' }, 3));
  assert.equal(prev.page, 2);
  assert.deepEqual(prev.filters, { state: 'Open', q: 'x' });
});

test('SPEC-UI-104 a filter, q or order change resets to page 1 (TC-UI-104a)', () => {
  const state = listState({ state: 'Open' }, 3);
  assert.equal(applyFilter(state, { state: 'Closed' }).page, 1);
  assert.equal(applyFilter(state, { q: 'abc' }).page, 1);
  assert.equal(applyFilter(state, { order: 'asc' }).page, 1);
  assert.deepEqual(applyFilter(state, { q: 'abc' }).filters, { state: 'Open', q: 'abc' });
  assert.equal(state.page, 3);
});

test('SPEC-UI-105 has previous only after page 1 (TC-UI-105a)', () => {
  assert.equal(hasPrevious(listState({}, 1)), false);
  assert.equal(hasPrevious(listState({}, 2)), true);
});

test('SPEC-UI-106 has next only while page * 20 is below total (TC-UI-106a)', () => {
  const cases = [
    [0, 1, false],
    [20, 1, false],
    [21, 1, true],
    [40, 1, true],
    [0, 2, false],
    [20, 2, false],
    [21, 2, false],
    [40, 2, false],
    [41, 2, true],
  ];
  for (const [total, page, expected] of cases) {
    assert.equal(hasNext({ page, page_size: 20, total }), expected, `total ${total} page ${page}`);
  }
});

test('SPEC-UI-120 reload repeats the URL of the current page (TC-UI-120e)', () => {
  const state = listState({ state: 'Open', q: ' abc ' }, 3);
  assert.equal(reloadQuery('/tickets', state), '/tickets?state=Open&q=abc&page=3&page_size=20');
});

test('SPEC-UI-125 last valid page is ceil(total / 20) (TC-UI-125a)', () => {
  assert.equal(lastValidPage(41), 3);
  assert.equal(lastValidPage(40), 2);
  assert.equal(lastValidPage(1), 1);
});

test('SPEC-UI-26 builds the URL with the chosen page_size and keeps 20 as default (TC-UI-26e)', () => {
  assert.equal(listQuery('/users', {}, 1, 50), '/users?page=1&page_size=50');
  assert.equal(listQuery('/users', { q: 'a' }, 2, 10), '/users?q=a&page=2&page_size=10');
  assert.equal(listQuery('/users', {}, 1), '/users?page=1&page_size=20');
  assert.equal(listState({}, 1).pageSize, 20);
  const state = listState({ state: 'Open' }, 2, 50);
  assert.equal(reloadQuery('/tickets', state), '/tickets?state=Open&page=2&page_size=50');
});

test('SPEC-UI-140 offers the sizes 10, 20 and 50 with 20 by default (TC-UI-140a)', () => {
  assert.deepEqual(PAGE_SIZE_OPTIONS, [10, 20, 50]);
  assert.equal(DEFAULT_PAGE_SIZE, 20);
  assert.equal(normalizePageSize('50'), 50);
  assert.equal(normalizePageSize(10), 10);
  assert.equal(normalizePageSize('7'), 20);
  assert.equal(normalizePageSize(undefined), 20);
});

test('SPEC-UI-141 changing the size asks for page 1 with the same filters, q and order (TC-UI-141a)', () => {
  const state = listState({ state: 'Open', q: 'x', order: 'asc' }, 3, 20);
  const next = changePageSize(state, '50');
  assert.equal(next.page, 1);
  assert.equal(next.pageSize, 50);
  assert.deepEqual(next.filters, { state: 'Open', q: 'x', order: 'asc' });
  assert.equal(
    reloadQuery('/tickets', next),
    '/tickets?state=Open&q=x&order=asc&page=1&page_size=50',
  );
  assert.equal(state.pageSize, 20);
  assert.equal(state.page, 3);
});

test('SPEC-UI-141 keeps the chosen size on the next, previous and filter changes (TC-UI-141b)', () => {
  const state = listState({}, 1, 10);
  assert.equal(nextPage(state).pageSize, 10);
  assert.equal(previousPage(nextPage(state)).pageSize, 10);
  assert.equal(applyFilter(state, { q: 'a' }).pageSize, 10);
});

test('SPEC-UI-142 formats the visible range and the total (TC-UI-142a)', () => {
  assert.equal(rangeText({ page: 1, pageSize: 20, total: 57 }), '1–20 de 57');
  assert.equal(rangeText({ page: 2, pageSize: 20, total: 57 }), '21–40 de 57');
  assert.equal(rangeText({ page: 3, pageSize: 20, total: 57 }), '41–57 de 57');
  assert.equal(rangeText({ page: 1, pageSize: 10, total: 3 }), '1–3 de 3');
  assert.equal(rangeText({ page: 1, pageSize: 50, total: 57 }), '1–50 de 57');
});

test('SPEC-UI-142 shows 0 de 0 when the total is 0 (TC-UI-142b)', () => {
  assert.equal(rangeText({ page: 1, pageSize: 20, total: 0 }), '0 de 0');
});

test('SPEC-UI-143 slices the full array into the visible page (TC-UI-143a)', () => {
  const items = Array.from({ length: 57 }, (_, i) => i + 1);
  const first = memoryPage(items, 1, 20);
  assert.equal(first.items.length, 20);
  assert.deepEqual([first.items[0], first.items.at(-1)], [1, 20]);
  assert.deepEqual([first.page, first.pageSize, first.total], [1, 20, 57]);
  const last = memoryPage(items, 3, 20);
  assert.deepEqual(last.items, [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57]);
  assert.equal(memoryPage(items, 1, 10).items.length, 10);
  assert.equal(memoryPage(items, 1, 50).items.length, 50);
  assert.deepEqual(memoryPage([], 1, 20), { items: [], page: 1, pageSize: 20, total: 0 });
});

test('SPEC-UI-144 flattens the product types into one row per type in API order (TC-UI-144a)', () => {
  const categories = [
    { id: 3, name: 'Computación' },
    { id: 5, name: 'Redes' },
  ];
  const types = [
    { id: 6, name: 'Router', category_id: 5 },
    { id: 4, name: 'Notebook', category_id: 3 },
    { id: 7, name: 'Switch', category_id: 5 },
  ];
  assert.deepEqual(flattenProductTypes(types, categories), [
    { id: 6, name: 'Router', category_id: 5, category: 'Redes' },
    { id: 4, name: 'Notebook', category_id: 3, category: 'Computación' },
    { id: 7, name: 'Switch', category_id: 5, category: 'Redes' },
  ]);
  assert.deepEqual(flattenProductTypes([{ id: 1, name: 'Suelto', category_id: 99 }], categories), [
    { id: 1, name: 'Suelto', category_id: 99, category: '' },
  ]);
});

test('SPEC-UI-145 moves between in-memory pages and sizes without touching the list (TC-UI-145a)', () => {
  const items = Array.from({ length: 45 }, (_, i) => i);
  const state = listState({}, 1, 20);
  const second = memoryPage(items, nextPage(state).page, state.pageSize);
  assert.equal(second.page, 2);
  assert.deepEqual([second.items[0], second.items.at(-1)], [20, 39]);
  const resized = changePageSize(nextPage(state), 10);
  const view = memoryPage(items, resized.page, resized.pageSize);
  assert.deepEqual([view.page, view.items.length, view.items[0]], [1, 10, 0]);
  assert.equal(hasNext({ page: view.page, page_size: view.pageSize, total: view.total }), true);
  assert.equal(items.length, 45);
});

test('SPEC-UI-146 a new search text goes back to page 1 and keeps the size (TC-UI-146a)', () => {
  const state = listState({ q: 'a' }, 3, 50);
  const next = applyFilter(state, { q: 'b' });
  assert.deepEqual([next.page, next.pageSize, next.filters.q], [1, 50, 'b']);
});

test('SPEC-UI-147 shows the last valid page when the page is beyond it and keeps it otherwise (TC-UI-147a)', () => {
  const items = Array.from({ length: 41 }, (_, i) => i);
  assert.equal(memoryPage(items, 5, 20).page, 3);
  assert.equal(memoryPage(items, 3, 20).items.length, 1);
  assert.equal(memoryPage(items, 2, 20).page, 2);
  assert.equal(memoryPage(items, 2, 50).page, 1);
  assert.equal(memoryPage([], 4, 20).page, 1);
  assert.equal(lastValidPage(41, 20), 3);
  assert.equal(lastValidPage(41, 10), 5);
  assert.equal(lastValidPage(0, 10), 1);
});
