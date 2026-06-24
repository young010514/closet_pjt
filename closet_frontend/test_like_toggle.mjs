import puppeteer from 'puppeteer'

const browser = await puppeteer.launch({
  headless: true,
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
})

const page = await browser.newPage()
await page.setViewport({ width: 1280, height: 900 })

function parseLikeCount(text) {
  const match = text.trim().match(/(\d+)\s*$/)
  if (!match) {
    throw new Error(`Could not parse like count from: ${text}`)
  }
  return Number(match[1])
}

async function readLikeButtonState() {
  const text = await page.$eval('.btn-like', (el) => el.textContent ?? '')
  const active = await page.$eval('.btn-like', (el) => el.classList.contains('active'))
  return {
    text: text.trim(),
    count: parseLikeCount(text),
    active,
  }
}

async function waitForLikeStateChange(previousText) {
  await page.waitForFunction(
    (oldText) => {
      const button = document.querySelector('.btn-like')
      return Boolean(button) && button.textContent?.trim() !== oldText
    },
    {},
    previousText,
  )
}

async function login(username, password) {
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle0' })
  await page.waitForSelector('#login-username')
  await page.type('#login-username', username)
  await page.type('#login-password', password)
  await Promise.all([
    page.waitForFunction(() => window.location.pathname !== '/login'),
    page.click('button[type="submit"]'),
  ])
}

await login('normal_test', 'test1234!')

await page.goto('http://localhost:5173/community/2', { waitUntil: 'networkidle0' })
await page.waitForSelector('.btn-like')

const initialState = await readLikeButtonState()

await page.click('.btn-like')
await waitForLikeStateChange(initialState.text)

const likedState = await readLikeButtonState()
if (likedState.active === initialState.active) {
  throw new Error('Like button active state did not toggle after the first click')
}

const firstStep = initialState.active ? -1 : 1
if (likedState.count !== initialState.count + firstStep) {
  throw new Error(
    `Like count did not change by ${firstStep} after the first click: ${initialState.count} -> ${likedState.count}`,
  )
}

await page.click('.btn-like')
await waitForLikeStateChange(likedState.text)

const revertedState = await readLikeButtonState()
if (revertedState.active !== initialState.active) {
  throw new Error('Like button did not return to its initial active state after the second click')
}

if (revertedState.count !== initialState.count) {
  throw new Error(
    `Like count did not return to the initial value after the second click: ${initialState.count} -> ${revertedState.count}`,
  )
}

await browser.close()
console.log('Like toggle smoke test passed.')
