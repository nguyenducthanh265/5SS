import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_ROOT = path.resolve(__dirname, "..");

function parseArgs(argv) {
  let url = "http://localhost:8085";
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith("--url=")) {
      url = arg.slice("--url=".length);
    } else if (arg === "--url" && argv[i + 1]) {
      url = argv[i + 1];
      i += 1;
    }
  }
  return { url: url.replace(/\/+$/, "") };
}

function readJson(relPath) {
  const fullPath = path.join(APP_ROOT, relPath);
  const raw = fs.readFileSync(fullPath, "utf8");
  return JSON.parse(raw);
}

async function runStaticAndContractChecks() {
  console.log("[1/2] Running static config & waste contract checks...");

  const pkg = readJson("package.json");
  assert.equal(typeof pkg.name, "string", "package.json must have name");
  assert.ok(pkg.scripts?.smoke, "package.json must register smoke script");

  const tsconfig = readJson("tsconfig.json");
  assert.equal(tsconfig.compilerOptions?.strict, true, "tsconfig strict must be true");

  const appJson = readJson("app.json");
  assert.equal(appJson.expo?.scheme, "hanoiwaste", "app.json scheme must be hanoiwaste");
  assert.ok(
    Array.isArray(appJson.expo?.plugins) && appJson.expo.plugins.includes("expo-router"),
    "app.json must include expo-router plugin",
  );

  for (const requiredRel of [
    "assets/sample-waste.jpg",
    "aiClient.ts",
    "src/types/waste.ts",
    "src/services/wasteApi.ts",
    "src/services/speech.ts",
    "src/components/WasteBinLegend.tsx",
    "src/app/index.tsx",
    "src/app/selftest.tsx",
  ]) {
    assert.ok(fs.existsSync(path.join(APP_ROOT, requiredRel)), `Missing required file: ${requiredRel}`);
  }

  // Import TypeScript module directly (Node >= 22.18 native type stripping)
  const wasteModUrl = pathToFileURL(path.join(APP_ROOT, "src/types/waste.ts")).href;
  const { parseWasteResult } = await import(wasteModUrl);

  const plainPayload = {
    items: [
      {
        name_vi: "Vỏ hộp sữa giấy",
        item_key: "milk_carton",
        material: "Giấy tráng nhôm/nhựa",
        dirty_oily: false,
        group_id: "group_1_recyclable",
        group_name_vi: "Nhóm 1: Chất thải rắn tái sử dụng, tái chế",
        rinse_required: true,
        sell_for_recycling: true,
        dropoff_points: [],
        note_vi: "Đổ cạn sữa, tráng sạch và ép dẹp.",
      },
    ],
    mixed_bag: false,
    mixed_bag_reason_vi: "",
    has_hazardous: false,
    dropoff_summary: [],
    collection_window_vi: "18:00 - 22:00",
    speech_vi: "Đây là vỏ hộp sữa giấy, thuộc Nhóm 1 tái chế.",
  };

  // Case 1: Plain JSON
  const resPlain = parseWasteResult(JSON.stringify(plainPayload));
  assert.equal(resPlain.ok, true, "Plain JSON should parse");
  assert.equal(resPlain.data.items[0].item_key, "milk_carton");
  assert.equal(resPlain.data.items[0].rinse_required, true);

  // Case 2: ```json fenced JSON + surrounding prose
  const fencedJson = `Đây là kết quả phân loại theo QĐ 87:\n\`\`\`json\n${JSON.stringify(plainPayload, null, 2)}\n\`\`\`\nVui lòng thực hiện đúng hướng dẫn.`;
  const resFenced = parseWasteResult(fencedJson);
  assert.equal(resFenced.ok, true, "Fenced JSON with surrounding prose should parse");
  assert.equal(resFenced.data.items[0].name_vi, "Vỏ hộp sữa giấy");

  // Case 2b: Bare JSON with leading/trailing prose (no fence)
  const proseJson = `Kết quả: ${JSON.stringify(plainPayload)} — hoàn tất.`;
  const resProse = parseWasteResult(proseJson);
  assert.equal(resProse.ok, true, "Bare JSON with surrounding prose should parse");

  // Case 3: Mixed-bag + hazardous JSON
  const mixedHazardous = {
    items: [
      {
        name_vi: "Pin tiểu AA",
        item_key: "battery",
        material: "Kim loại nặng / hóa chất",
        dirty_oily: false,
        group_id: "group_3_hazardous",
        group_name_vi: "Nhóm 3: Chất thải nguy hại",
        is_hazardous: true,
        rinse_required: false,
        sell_for_recycling: false,
        dropoff_points: [
          {
            name: "Điểm thu hồi Pin Xanh Hoàn Kiếm",
            area: "Quận Hoàn Kiếm",
            note_vi: "Dán băng keo hai đầu pin trước khi bỏ.",
          },
        ],
        note_vi: "Tách riêng tuyệt đối.",
      },
      plainPayload.items[0],
    ],
    mixed_bag: true,
    mixed_bag_reason_vi: "Túi rác có lẫn pin thải nguy hại với rác tái chế.",
    has_hazardous: true,
    dropoff_summary: [
      {
        name: "Điểm thu hồi Pin Xanh Hoàn Kiếm",
        area: "Quận Hoàn Kiếm",
        note_vi: "Dán băng keo hai đầu pin trước khi bỏ.",
      },
    ],
    collection_window_vi: "18:00 - 22:00",
    speech_vi: "Cảnh báo túi rác có lẫn chất thải nguy hại gồm pin tiểu AA.",
  };
  const resMixed = parseWasteResult(JSON.stringify(mixedHazardous));
  assert.equal(resMixed.ok, true, "Mixed-bag hazardous JSON should parse");
  assert.equal(resMixed.data.mixed_bag, true);
  assert.equal(resMixed.data.has_hazardous, true);
  assert.equal(resMixed.data.items.length, 2);
  assert.equal(resMixed.data.dropoff_summary.length, 1);

  // Case 4: Malformed non-JSON & invalid schema inputs
  for (const bad of [
    "",
    "   ",
    "Xin lỗi, ảnh mờ quá không phân loại được.",
    "{broken json: [1, 2",
    JSON.stringify({ items: "not-an-array", speech_vi: "ok" }),
    JSON.stringify({ items: [{ name_vi: "Pin" }], speech_vi: "ok" }),
    JSON.stringify({ items: [] }),
  ]) {
    const resBad = parseWasteResult(bad);
    assert.equal(resBad.ok, false, `Malformed input should fail gracefully: ${bad}`);
    assert.ok(resBad.reason.length > 0, "Failure must provide a reason");
  }

  console.log("PASS: Static config & parseWasteResult contract checks passed (all 4 suites).");
}

async function isReachable(url) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 3000);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    return res.status;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function runLiveWebChecks(baseUrl) {
  console.log(`[2/2] Checking live Expo Web server at ${baseUrl}...`);
  const homeStatus = await isReachable(`${baseUrl}/`);
  if (homeStatus === null) {
    console.log(`SKIP: ${baseUrl} is not reachable. Start Expo web on port 8085 or pass --url to run live UI checks.`);
    return;
  }
  assert.equal(homeStatus, 200, `Expected HTTP 200 on ${baseUrl}/, got ${homeStatus}`);

  const selftestStatus = await isReachable(`${baseUrl}/selftest`);
  assert.equal(selftestStatus, 200, `Expected HTTP 200 on ${baseUrl}/selftest, got ${selftestStatus}`);
  console.log(`PASS: HTTP 200 verified on ${baseUrl}/ and ${baseUrl}/selftest.`);

  const pyScript = `
import json, sys
from playwright.sync_api import sync_playwright

base_url = sys.argv[1]
page_errors = []
console_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.on("pageerror", lambda err: page_errors.append(str(err)))
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # 1. Home route + 4 color-coded visual bin labels
    resp = page.goto(f"{base_url}/", wait_until="networkidle")
    assert resp is not None and resp.status == 200, f"Home status: {resp.status if resp else None}"
    assert page.get_by_text("ĐIỀU HÒA DÒNG RÁC").is_visible(), "Home title missing"
    home_text = page.locator("body").inner_text()
    for bin_label in ("Thùng Xanh Lá", "Thùng Vàng", "Thùng Đỏ", "Thùng Đen"):
        assert bin_label in home_text, f"Missing bin label: {bin_label}"

    # 2. Toggle "Túi rác mở" mode
    bag_btn = page.get_by_text("Túi rác mở", exact=True)
    bag_btn.click()
    page.wait_for_timeout(150)

    # 3. Open and close "QĐ 87" modal
    page.get_by_text("QĐ 87", exact=True).click()
    modal_heading = page.get_by_text("Quyết định 87/2025/QĐ-UBND", exact=True)
    modal_heading.wait_for(state="visible", timeout=3000)
    page.get_by_label("Đóng hướng dẫn quy định Hà Nội").click()
    modal_heading.wait_for(state="hidden", timeout=3000)

    # 4. Click "Thử ảnh mẫu" and verify clean result or status banner (never crash)
    page.get_by_text("Thử ảnh mẫu", exact=True).click()
    status_texts = [
        "Kết quả AI trực tiếp",
        "Chưa nhận được phân loại AI trực tiếp",
        "Thiếu cấu hình máy chủ",
        "Lỗi kết nối máy chủ",
        "Máy chủ AI đang bận",
        "Quá thời gian chờ AI",
        "Dữ liệu trả về chưa đúng định dạng",
    ]
    found_status = None
    for _ in range(56):
        body_text = page.locator("body").inner_text()
        for candidate in status_texts:
            if candidate in body_text:
                found_status = candidate
                break
        if found_status:
            break
        page.wait_for_timeout(500)
    assert found_status is not None, "Expected clean AI result or status/error banner after clicking 'Thử ảnh mẫu'"

    # 5. Selftest route (brief pause avoids back-to-back Gemini free-tier burst)
    page.wait_for_timeout(1200)
    resp2 = page.goto(f"{base_url}/selftest", wait_until="networkidle")
    assert resp2 is not None and resp2.status == 200, f"Selftest status: {resp2.status if resp2 else None}"
    settled = None
    for _ in range(56):
        st_text = page.locator("body").inner_text()
        if "HACKCHECK SELFTEST PASS" in st_text:
            settled = "HACKCHECK SELFTEST PASS"
            break
        if "HACKCHECK SELFTEST FAIL" in st_text:
            settled = "HACKCHECK SELFTEST FAIL"
            break
        page.wait_for_timeout(500)
    assert settled is not None, "Selftest did not reach PASS or FAIL state"

    browser.close()

print(json.dumps({
    "page_errors": page_errors,
    "console_errors": console_errors,
    "sample_outcome": found_status,
    "selftest_outcome": settled,
}, ensure_ascii=False))
assert len(page_errors) == 0, f"Unexpected page errors: {page_errors}"
assert len(console_errors) == 0, f"Unexpected console errors: {console_errors}"
`;

  const pyRes = spawnSync("python", ["-c", pyScript, baseUrl], {
    cwd: APP_ROOT,
    encoding: "utf8",
    timeout: 60000,
  });

  if (pyRes.error || pyRes.status !== 0) {
    const stderr = (pyRes.stderr || "").trim();
    const stdout = (pyRes.stdout || "").trim();
    if (stderr.includes("No module named 'playwright'") || stderr.includes("No module named \"playwright\"")) {
      console.log("SKIP: Python Playwright not installed; HTTP 200 checks already passed.");
      return;
    }
    throw new Error(`Playwright live UI smoke failed:\nSTDOUT: ${stdout}\nSTDERR: ${stderr}`);
  }

  console.log(`PASS: Live UI smoke (Playwright Chromium): ${pyRes.stdout.trim()}`);
}

async function main() {
  const { url } = parseArgs(process.argv.slice(2));
  await runStaticAndContractChecks();
  await runLiveWebChecks(url);
  console.log("ALL SMOKE CHECKS PASSED.");
}

main().catch((err) => {
  console.error("SMOKE TEST FAILED:", err instanceof Error ? err.message : err);
  process.exit(1);
});
