import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PAGE_SIZE,
  applyFilter,
  hasNext,
  hasPrevious,
  lastValidPage,
  listState,
  listQuery,
  nextPage,
  pageInfo,
  previousPage,
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
