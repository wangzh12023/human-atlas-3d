// Chrome/Chromium discovery shared by the optional screenshot tools.
import fs from 'node:fs';
import path from 'node:path';

export function browserOptions() {
  const candidates = process.platform === 'win32'
    ? [path.join(process.env.PROGRAMFILES || 'C:/Program Files', 'Google/Chrome/Application/chrome.exe'),
       path.join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
       path.join(process.env['PROGRAMFILES(X86)'] || 'C:/Program Files (x86)', 'Google/Chrome/Application/chrome.exe')]
    : process.platform === 'darwin'
      ? ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium']
      : ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  const executablePath = process.env.CHROME_PATH || candidates.find(p => fs.existsSync(p));
  if (!executablePath || !fs.existsSync(executablePath)) {
    throw new Error('Chrome/Chromium not found. Set CHROME_PATH to the installed browser executable.');
  }
  return {
    executablePath,
    headless: true,
    args: [process.platform === 'win32' ? '--use-angle=d3d11' : '--use-angle=swiftshader',
           '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--enable-unsafe-swiftshader'],
  };
}
