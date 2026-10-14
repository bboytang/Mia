import { test, expect } from '@playwright/test';
import { mockBackend, longText } from './fixtures.js';

const routes = [
  '/login', '/register', '/retrieve-password', '/home',
  '/role-config?agentId=test-agent', '/voice-print?agentId=test-agent',
  '/device-management?agentId=test-agent', '/user-management', '/model-config',
  '/params-management', '/knowledge-base-management', '/server-side-management',
  '/ota-management', '/voice-resource-management', '/voice-clone-management',
  '/dict-management', '/provider-management', '/agent-template-management',
  '/template-quick-config?templateId=test-template', '/feature-management',
  '/replacement-word-management', '/address-book-management',
];

async function assertFits(page, label) {
  const metrics = await page.evaluate(() => {
    const width = document.documentElement.clientWidth;
    return { width, scroll: document.documentElement.scrollWidth,
      overflow: [...document.querySelectorAll('body *')].filter(el => {
        const rect = el.getBoundingClientRect();
        return rect.width && (rect.right > width + 1 || rect.left < -1);
      }).slice(0, 12).map(el => `${el.tagName}.${el.className}`) };
  });
  expect.soft(metrics.scroll, label + ' ' + metrics.overflow.join(', ')).toBeLessThanOrEqual(metrics.width + 1);
}

for (const width of [360, 390, 430, 768, 1024, 1440]) {
  test(`all routes fit at ${width}px with populated long-text records`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await mockBackend(page);
    const errors = [];
    page.on('pageerror', error => errors.push(page.url() + ': ' + error.message));
    for (const route of routes) {
      await test.step(route, async () => {
        if (!['/login','/register','/retrieve-password'].includes(route)) {
          await page.evaluate(() => localStorage.setItem('token', JSON.stringify({ token: 'synthetic-test-token' })));
        }
        await page.goto('/#' + route);
        const name = route.split('?')[0].slice(1).replace('server-side-management', 'server-side-manager');
        await expect(page.locator('.page-' + name)).toBeVisible();
        if (route.startsWith('/device-management')) {
          await expect(page.getByRole('button', { name: '私有授权码', exact: true }).first()).toBeVisible();
        }
        await page.waitForTimeout(300);
        await assertFits(page, route);
        if (route === '/home' || route.startsWith('/device-management') || route === '/params-management') {
          await page.screenshot({ path: testInfo.outputPath(`${width}-${route.split('?')[0].slice(1)}.png`), fullPage: true });
        }
      });
    }
    expect(errors).toEqual([]);
  });
}

test('compact navigation preserves permissions, supports close and route changes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockBackend(page, false);
  await page.goto('/#/home');
  const toggle = page.getByRole('button', { name: '导航菜单', exact: true });
  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  const navigation = page.getByRole('navigation');
  await expect(navigation.getByText('模型配置', { exact: true })).toHaveCount(0);
  await expect(navigation.getByText('知识库', { exact: true })).toBeVisible();
  await toggle.press('Escape');
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await navigation.getByText('知识库', { exact: true }).click();
  await expect(page).toHaveURL(/knowledge-base-management/);
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await assertFits(page, 'navigation');
});

test('mobile card selection, editing, cancel and desktop rotation keep existing data', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockBackend(page);
  await page.goto('/#/provider-management');
  const card = page.locator('.mobile-record').first();
  await expect(card).toBeVisible();
  await card.locator('.el-checkbox').click();
  await expect(card.locator('input[type=checkbox]')).toBeChecked();
  await card.getByRole('button', { name: '编辑', exact: true }).click();
  const dialog = page.locator('.el-dialog:visible');
  await expect(dialog).toBeVisible();
  await assertFits(page, 'edit dialog');
  await dialog.locator('input').nth(1).fill('test-code');
  await dialog.locator('.el-dialog__headerbtn').click();
  await expect(dialog).toHaveCount(0);
  await page.setViewportSize({ width: 1024, height: 768 });
  await expect(page.locator('.custom-table .el-table__body-wrapper')).toBeVisible();
  await expect(page.locator('.custom-table .el-table__body input[type=checkbox]').first()).toBeChecked();
  await page.setViewportSize({ width: 430, height: 932 });
  await expect(page.locator('.mobile-record input[type=checkbox]').first()).toBeChecked();
  await assertFits(page, 'rotation');
});

test('mobile pagination reaches arbitrary pages and keeps page-size selection', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await mockBackend(page);
  const requests = [];
  await page.route('**/xiaozhi/models/provider?**', async route => {
    requests.push(new URL(route.request().url()).searchParams);
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ code: 0, data: { list: [], total: 1234 } }) });
  });
  await page.goto('/#/provider-management');
  const pagination = page.locator('.pagination-wrapper');
  await expect(pagination.locator('.el-pagination__total')).toContainText('1234');
  await assertFits(page, 'large page count');
  await pagination.locator('.btn-next').click();
  await expect.poll(() => requests.at(-1)?.get('page')).toBe('2');
  const jump = pagination.locator('.el-pagination__jump input');
  await jump.fill('88');
  await jump.press('Enter');
  await expect.poll(() => requests.at(-1)?.get('page')).toBe('88');
  await pagination.locator('.el-select').click();
  await page.locator('.el-select-dropdown:visible').getByText(/50\s*条\/页/).click();
  await expect.poll(() => requests.at(-1)?.get('limit')).toBe('50');
  expect(requests.at(-1).get('page')).toBe('1');
  await assertFits(page, 'page-size selection');
});

test('parameter edit survives constrained keyboard height; cancel makes no API write', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await mockBackend(page);
  const writes = [];
  page.on('request', request => { if (['POST','PUT','DELETE'].includes(request.method())) writes.push(request.url()); });
  await page.goto('/#/params-management');
  await page.getByRole('button', { name: '编辑', exact: true }).first().click();
  const dialog = page.locator('.el-dialog:visible');
  await expect(dialog).toBeVisible();
  await dialog.locator('input').first().fill('server.test');
  await page.setViewportSize({ width: 360, height: 360 });
  await assertFits(page, 'keyboard-height dialog');
  const bounds = await dialog.boundingBox();
  expect(bounds.height).toBeLessThanOrEqual(360);
  await dialog.locator('.el-dialog__headerbtn').click();
  await expect(dialog).toHaveCount(0);
  expect(writes).toEqual([]);
});

test('mobile prompt details are touch accessible without losing long content', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockBackend(page);
  await page.goto('/#/home');
  await page.locator('.device-info-button').first().click();
  await expect(page.locator('.device-prompt-detail:visible')).toHaveText(longText);
  await assertFits(page, 'prompt details');
});

for (const width of [390, 768]) {
  test(`all management add dialogs close at ${width}px without writing data`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await mockBackend(page);
    const writes = [];
    page.on('request', request => { if (['POST','PUT','DELETE'].includes(request.method())) writes.push(request.url()); });
    for (const route of ['/params-management','/ota-management','/provider-management','/voice-resource-management','/replacement-word-management','/agent-template-management','/voice-print?agentId=test-agent']) {
      await page.goto('/#' + route);
      const add = page.locator('.ctrl_btn button:has(.el-icon-plus)').first();
      await expect(add).toBeVisible();
      await add.click();
      const dialog = page.locator('.el-dialog:visible');
      await expect(dialog).toBeVisible();
      await assertFits(page, route + ' dialog');
      await dialog.locator('.el-dialog__headerbtn').click();
      await expect(dialog).toHaveCount(0);
    }
    expect(writes).toEqual([]);
  });
}

test('role configuration drawers, context settings and history remain reachable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockBackend(page);
  await page.goto('/#/role-config?agentId=test-agent');
  await page.getByRole('button', { name: '编辑源', exact: true }).click();
  let dialog = page.locator('.el-dialog:visible');
  await expect(dialog).toBeVisible();
  await assertFits(page, 'context providers');
  await dialog.locator('.el-dialog__headerbtn').click();
  await page.getByRole('button', { name: '编辑功能', exact: true }).click();
  const drawer = page.locator('.el-drawer:visible');
  await expect(drawer).toBeVisible();
  await assertFits(page, 'functions drawer');
  await drawer.locator('.custom-close-btn').click();
  await expect(drawer).toHaveCount(0);
  await page.locator('.history-btn').click();
  dialog = page.locator('.el-dialog:visible');
  await expect(dialog).toBeVisible();
  await assertFits(page, 'snapshot history');
  await dialog.locator('.el-dialog__headerbtn').click();
  await page.goto('/#/home');
  await page.getByRole('button', { name: '聊天记录', exact: true }).first().click();
  dialog = page.locator('.el-dialog:visible');
  await expect(dialog).toBeVisible();
  await assertFits(page, 'chat history');
  await dialog.locator('.el-dialog__headerbtn').click();
  await expect(dialog).toHaveCount(0);
});
