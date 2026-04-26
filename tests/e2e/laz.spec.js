const { test, expect } = require("@playwright/test");

test("laz frontend loads the sample index and previews a query", async ({ page }) => {
  await page.goto("file://" + process.cwd().replaceAll("\\", "/") + "/site/laz-tile-index.html");

  await expect(page.getByRole("heading", { name: "laz-tile-index" })).toBeVisible();
  await expect(page.getByText("Preview ready")).toBeVisible();
  await expect(page.locator("#sourceValue")).toContainText("urban-block.indexed.las");
  await expect(page.locator("#cellsValue")).not.toContainText("-");
  await expect(page.locator("#commandBox")).toContainText("laz-tile-index query");
  await expect(page.locator("#gridCanvas")).toBeVisible();
});
