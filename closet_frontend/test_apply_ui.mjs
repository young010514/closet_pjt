import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });

// 1. 상세 페이지 - 비로그인 상태 (신청하기 버튼 확인)
await page.goto('http://localhost:5173/community/2', { waitUntil: 'networkidle0' });
await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_1_detail.png' });
console.log('[1] Detail page (not logged in) - saved');

// 2. 신청하기 버튼 클릭 → 로그인 페이지로 이동 확인
const applyBtn = await page.$('.btn-apply');
if (applyBtn) {
  await applyBtn.click();
  await page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {});
  await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_2_login_redirect.png' });
  console.log('[2] After clicking apply (not logged in) - saved');
}

// 3. normal_test 로그인
await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' });
await page.type('input[type="text"], input[name="username"]', 'normal_test');
await page.type('input[type="password"]', 'test1234!');
const loginBtn = await page.$('button[type="submit"]');
if (loginBtn) {
  await loginBtn.click();
  await page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {});
}
await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_3_after_login.png' });
console.log('[3] After login (normal_test) - saved');

// 4. 상세 페이지 재방문 - 이미 신청한 상태
await page.goto('http://localhost:5173/community/2', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 1000));
await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_4_already_applied.png', fullPage: true });
console.log('[4] Detail page (normal_test, already applied) - saved');

// 5. 로그아웃 후 새 유저(testadmin)로 로그인해서 신청 폼 열기
// testadmin은 profile이 없으므로 다른 유저가 필요 - 여기서는 폼 자체를 보여주기 위해
// normal_test를 로그아웃하고, 직접 쿠키 조작 없이 폼만 테스트
// → 신청 완료 페이지에서 apply-done 메시지 확인으로 대신함
const applyDone = await page.$('.apply-done');
if (applyDone) {
  const text = await applyDone.evaluate(el => el.textContent);
  console.log('[4] apply-done text:', text.trim());
}

await browser.close();
console.log('Done!');
