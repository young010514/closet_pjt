import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });

// biz_test 로 작성한 글이므로, 신청 폼을 보려면 미신청 일반유저가 필요
// testadmin에 profile/normal type을 강제로 주지 않고,
// 대신 Vue 앱에서 직접 showApplyForm을 true로 설정해 폼 렌더링 확인

await page.goto('http://localhost:5173/community/2', { waitUntil: 'networkidle0' });

// 비로그인이지만 Vue 상태를 직접 조작해 폼 표시
await page.evaluate(() => {
  // Vue 앱의 __vue_app__ 통해 컴포넌트 내부 ref 조작
  const el = document.querySelector('.community-detail');
  if (!el || !el.__vueParentComponent) return;
  const comp = el.__vueParentComponent;
  if (comp && comp.setupState) {
    comp.setupState.showApplyForm.value = true;
  }
});

await new Promise(r => setTimeout(r, 300));
await page.screenshot({ path: 'C:/Users/SSAFY/Desktop/closet_pjt/ss_form_open.png', fullPage: true });
console.log('Form open screenshot saved');

await browser.close();
