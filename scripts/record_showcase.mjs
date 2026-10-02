// Playwright CLI run-code function. Use against a dedicated no-key replay session.
// Requires the saved GRADE conversation to be loaded (see docs/showcase.md).
async (page) => {
  const pause = () => page.waitForTimeout(3000);
  const shot = (name) => page.screenshot({path: `output/playwright/${name}.png`});
  await page.getByRole('button', {name: /^1 · Answer saved · 2 audits/}).click();
  await pause();
  await page.mouse.move(670, 780);
  await page.mouse.wheel(0, 350);
  await pause();
  await shot('ask-answer');
  await page.getByRole('button', {name: 'Audit', exact: true}).click();
  await page.getByRole('heading', {name: 'Review the answer and its evidence.'}).scrollIntoViewIfNeeded();
  await pause();
  await shot('audit-overview');
  await page.getByRole('button', {name: /^PMC:PMC11567630 · Glycemia/}).click();
  await pause();
  await shot('audit-direct');
  await page.getByLabel('Saved audit run').selectOption({label: '2 · atomic_v2 · Original answer · partial_error'});
  await pause();
  await shot('audit-qualifiers');
  await page.getByRole('button', {name: 'Locate in answer · 20–77', exact: true}).click();
  await pause();
  await shot('audit-summary');
  await page.getByRole('button', {name: 'Needs review · parsing unresolved · select claim', exact: true}).click();
  await pause();
  await shot('audit-review');
  await page.getByRole('button', {name: 'Export audit JSON', exact: true}).click();
  await page.getByRole('button', {name: 'Back to answer', exact: true}).click();
  await page.getByRole('button', {name: /^2 · Answer saved · 1 audit/}).click();
  await pause();
  await page.getByRole('button', {name: 'Export conversation', exact: true}).click();
  await pause();
}
