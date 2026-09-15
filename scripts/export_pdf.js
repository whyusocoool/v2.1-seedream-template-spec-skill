#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { spawnSync } = require("node:child_process");

function usage(message) {
  if (message) process.stderr.write(`error: ${message}\n`);
  process.stderr.write("Usage: node scripts/export_pdf.js <report.html> [--output report.pdf] [--browser-path executable]\n");
  process.exit(2);
}

const args = process.argv.slice(2);
if (!args.length) usage();
let input;
let output;
let browserPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
let browserPathWasExplicit = Boolean(browserPath);
for (let index = 0; index < args.length; index += 1) {
  const value = args[index];
  if (value === "--output") {
    if (index + 1 >= args.length || args[index + 1].startsWith("--")) usage("missing value for --output");
    output = args[++index];
  }
  else if (value === "--browser-path") {
    if (index + 1 >= args.length || args[index + 1].startsWith("--")) usage("missing value for --browser-path");
    browserPath = args[++index];
    browserPathWasExplicit = true;
  }
  else if (value.startsWith("--")) usage(`unknown option ${value}`);
  else if (!input) input = value;
  else usage("only one HTML input is allowed");
}
if (!input) usage("missing HTML input");
input = path.resolve(input);
output = path.resolve(output || path.join(path.dirname(input), "report.pdf"));
const inputStats = fs.statSync(input, { throwIfNoEntry: false });
if (!inputStats?.isFile()) usage(`HTML input not found: ${input}`);
if (input === output) usage("PDF output must differ from HTML input");
const existingOutputStats = fs.statSync(output, { throwIfNoEntry: false });
if (existingOutputStats && existingOutputStats.dev === inputStats.dev && existingOutputStats.ino === inputStats.ino) {
  usage("PDF output must not alias the HTML input through a symlink or hardlink");
}
fs.mkdirSync(path.dirname(output), { recursive: true });
const renderTarget = path.join(path.dirname(output), `.${path.basename(output)}.${process.pid}.tmp.pdf`);
try { fs.rmSync(renderTarget, { force: true }); } catch (_) { /* best-effort cleanup */ }

function isExecutableFile(candidate) {
  try {
    return fs.statSync(candidate).isFile() && (fs.accessSync(candidate, fs.constants.X_OK), true);
  } catch (_) { return false; }
}

if (browserPathWasExplicit && !isExecutableFile(browserPath)) usage(`browser executable is invalid or not executable: ${browserPath}`);

function pathBrowserCandidates() {
  const directories = (process.env.PATH || "").split(path.delimiter).filter(Boolean);
  const names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"];
  const extensions = process.platform === "win32" ? (process.env.PATHEXT || ".EXE;.CMD;.BAT").split(";") : [""];
  const candidates = [];
  for (const directory of directories) {
    for (const name of names) {
      for (const extension of extensions) candidates.push(path.join(directory, name + extension.toLowerCase()));
    }
  }
  return candidates;
}

const browserCandidates = [
  browserPath,
  ...pathBrowserCandidates(),
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  path.join(os.homedir(), "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
  path.join(os.homedir(), "Applications/Chromium.app/Contents/MacOS/Chromium"),
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  process.env.PROGRAMFILES && path.join(process.env.PROGRAMFILES, "Google/Chrome/Application/chrome.exe"),
  process.env["PROGRAMFILES(X86)"] && path.join(process.env["PROGRAMFILES(X86)"], "Google/Chrome/Application/chrome.exe"),
  process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"),
].filter(Boolean);
const executable = browserCandidates.find(isExecutableFile);

function loadPlaywright() {
  for (const moduleName of ["playwright", "playwright-core"]) {
    try { return require(moduleName); } catch (error) {
      if (error.code !== "MODULE_NOT_FOUND") throw error;
    }
  }
  return null;
}

async function viaPlaywright(playwright) {
  const options = { headless: true };
  if (executable) options.executablePath = executable;
  const browser = await playwright.chromium.launch(options);
  try {
    const page = await browser.newPage({ viewport: { width: 1160, height: 900 }, deviceScaleFactor: 1 });
    await page.goto(pathToFileURL(input).href, { waitUntil: "load" });
    await page.emulateMedia({ media: "print" });
    await page.pdf({ path: renderTarget, format: "A4", printBackground: true, preferCSSPageSize: true, displayHeaderFooter: false });
  } finally {
    await browser.close();
  }
}

function viaChrome() {
  if (!executable) throw new Error("Playwright is unavailable and no Chrome/Chromium executable was found. Set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH or pass --browser-path.");
  const result = spawnSync(executable, [
    "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    `--print-to-pdf=${renderTarget}`, pathToFileURL(input).href,
  ], { encoding: "utf8" });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error((result.stderr || result.stdout || `Chrome exited ${result.status}`).trim());
}

function validatePdf(file) {
  const stats = fs.statSync(file, { throwIfNoEntry: false });
  if (!stats?.isFile() || stats.size < 6) throw new Error("PDF renderer completed without a valid output file");
  const descriptor = fs.openSync(file, "r");
  try {
    const signature = Buffer.alloc(5);
    fs.readSync(descriptor, signature, 0, 5, 0);
    if (signature.toString("ascii") !== "%PDF-") throw new Error("renderer output is not a PDF file");
  } finally { fs.closeSync(descriptor); }
}

(async () => {
  const playwright = loadPlaywright();
  let playwrightError = null;
  if (playwright) {
    try { await viaPlaywright(playwright); }
    catch (error) {
      playwrightError = error;
      try { fs.rmSync(renderTarget, { force: true }); } catch (_) { /* best-effort cleanup */ }
    }
  }
  if (!playwright || playwrightError) {
    try { viaChrome(); }
    catch (chromeError) {
      if (playwrightError) throw new Error(`Playwright failed: ${playwrightError.message}; Chrome fallback failed: ${chromeError.message}`);
      throw chromeError;
    }
  }
  validatePdf(renderTarget);
  fs.renameSync(renderTarget, output);
  process.stdout.write(`Wrote ${output}\n`);
})().catch((error) => {
  try { fs.rmSync(renderTarget, { force: true }); } catch (_) { /* best-effort cleanup */ }
  process.stderr.write(`error: ${error.message}\n`);
  process.exit(1);
});
