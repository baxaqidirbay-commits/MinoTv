const { chromium } = require('playwright');

(async () => {
  console.log("==========================================");
  console.log("Ko'k rangli Chromium brauzeri ishga tushirilmoqda...");
  console.log("==========================================");

  const browser = await chromium.launch({
    headless: false,
    slowMo: 1000,
    args: ['--start-maximized', '--no-sandbox']
  });

  const context = await browser.newContext({
    viewport: null // to'liq ekranga moslashish uchun
  });

  const page = await context.newPage();

  console.log("1. Google Flow (flow.google.com) sahifasi ochilmoqda...");
  await page.goto('https://flow.google.com', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  console.log("2. Sahifa pastga aylantirilmoqda (scroll)...");
  await page.evaluate(() => window.scrollBy({ top: 600, behavior: 'smooth' }));
  await page.waitForTimeout(3000);

  console.log("3. Sahifa yana pastga aylantirilmoqda...");
  await page.evaluate(() => window.scrollBy({ top: 800, behavior: 'smooth' }));
  await page.waitForTimeout(3000);

  console.log("==========================================");
  console.log("Brauzer yopilmaydi! 3 daqiqa davomida ekranda ochiq turadi.");
  console.log("Alt + Tab bosing yoki pastdagi Taskbar'dan ko'k belgili Chromium'ni tanlang!");
  console.log("==========================================");

  // 3 daqiqa ochiq qoldiramiz
  await page.waitForTimeout(180000);

  await browser.close();
})();
