import { test } from '@jupyterlab/galata';

import { expect } from '@playwright/test';

const TIMEOUT = 600000;

test.describe('General Tests', () => {
  test.setTimeout(TIMEOUT);

  test.beforeEach(({ page }) => {
    page.on('console', (message) => {
      console.log('CONSOLE MSG ---', message.text());
    });
  });

  test('should execute some code', async ({ page }) => {
    await page.goto('lab/index.html');

    const kernel = page.locator('[title="Python (Pyodide)"]').first();
    await kernel.click();

    // Wait for kernel to be idle
    await page.locator('#jp-main-statusbar').getByText('Idle').waitFor();

    await page.notebook.setCell(0, 'code', 'print("ok")');
    await page.notebook.runCell(0);

    // Wait for kernel to be idle
    await page.locator('#jp-main-statusbar').getByText('Idle').waitFor();

    const cell = await page.notebook.getCellOutput(0);

    expect(await cell?.screenshot()).toMatchSnapshot('execute.png');
  });

  test('the kernel should have access to the file system', async ({ page }) => {
    await page.goto('lab/index.html');

    // Create a Python notebook
    const kernel = page.locator('[title="Python (Pyodide)"]').first();
    await kernel.click();

    await page.notebook.save();

    await page.notebook.setCell(0, 'code', 'import os; os.listdir()');
    await page.notebook.runCell(0);

    const cell = await page.notebook.getCellOutput(0);
    const cellContent = await cell?.textContent();
    const name = 'Untitled.ipynb';
    expect(cellContent).toContain(name);
  });
});
