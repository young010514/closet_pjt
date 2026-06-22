import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });

// user2로 로그인 (미신청 일반유저)
await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' });
await page.type('input[placeholder*="아이디"], input[type="text"]', 'user2');
await page.type('input[type="password"]', 'test1234!');
await page.click('button[type="submit"]');
await page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(() => {});

// 상세 페이지
await page.goto('http://localhost:5173/community/2', { waitUntil: 'networkidle0' });
await new Promise(r => setTimeout(r, 800));

// 신청하기 버튼 클릭
const btn = await page.$('.btn-apply');
if (btn) {
  await btn.click();
  await new Promise(r => setTimeout(r, 600));
}

// 폼이 열린 상태 스크린샷 (fullPage)
await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_form_open2.png', fullPage: true });
console.log('[1] Form open - saved');

// 폼 입력
await page.type('input[placeholder*="실명"]', '김테스터');
await page.type('input[placeholder*="010"]', '010-7777-8888');
await page.type('input[placeholder*="인스타그램"]', '@fashion_tester');
await page.type('textarea', '린넨 셔츠에 관심이 많아서 신청합니다. 패션 블로그를 운영 중이며 솔직한 후기를 작성할 자신이 있습니다.');

await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_form_filled.png', fullPage: true });
console.log('[2] Form filled - saved');

// 제출
await page.click('.btn-submit');
await new Promise(r => setTimeout(r, 800));

await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_form_submitted.png', fullPage: true });
console.log('[3] After submit - saved');

await browser.close();
