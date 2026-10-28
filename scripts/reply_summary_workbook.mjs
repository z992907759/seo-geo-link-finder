#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [statePath, outputPath, previewPath] = process.argv.slice(2);
if (!statePath || !outputPath || !previewPath) throw new Error("Usage: state output preview");

const state = JSON.parse(await fs.readFile(path.resolve(statePath), "utf8"));
const responseRows = (state.prospects ?? []).filter((row) => ["quoted", "replied", "risk_hold"].includes(row.status));
const freeRows = responseRows.filter((row) => row.placement_terms?.price_status === "free_editorial_route");
const priceRows = responseRows.filter((row) => row.quote?.amount_min != null);
const actionRows = responseRows.filter((row) => row.status === "replied" && row.placement_terms?.price_status !== "free_editorial_route");

const colors = { ink: "#26332F", muted: "#5F6B66", green: "#536B61", light: "#EEF2EF", line: "#D8DFDB", amber: "#F7EFE0", risk: "#F6E8E6", white: "#FFFFFF" };
const wb = Workbook.create();
const ws = wb.worksheets.add("回复汇总");
ws.showGridLines = false;

function setTitle(row, text, subtitle) {
  ws.getRange(`A${row}`).values = [[text]];
  ws.getRange(`A${row}`).format = { font: { bold: true, size: 16, color: colors.ink }, verticalAlignment: "center" };
  ws.getRange(`A${row}:K${row}`).format.rowHeight = 28;
  if (subtitle) {
    ws.getRange(`A${row + 1}`).values = [[subtitle]];
    ws.getRange(`A${row + 1}`).format = { font: { color: colors.muted, size: 10 }, verticalAlignment: "center" };
  }
}
function section(row, text) {
  ws.getRange(`A${row}:K${row}`).merge();
  ws.getRange(`A${row}`).values = [[text]];
  ws.getRange(`A${row}:K${row}`).format = { fill: colors.green, font: { bold: true, color: colors.white }, verticalAlignment: "center" };
  ws.getRange(`A${row}:K${row}`).format.rowHeight = 23;
}
function header(row, cells) {
  ws.getRange(`A${row}:K${row}`).values = [cells];
  ws.getRange(`A${row}:K${row}`).format = { fill: colors.light, font: { bold: true, color: colors.ink }, wrapText: true, verticalAlignment: "center", borders: { bottom: { style: "thin", color: colors.line } } };
  ws.getRange(`A${row}:K${row}`).format.rowHeight = 26;
}
function body(row, values, fill = colors.white) {
  ws.getRange(`A${row}:K${row}`).values = [values];
  ws.getRange(`A${row}:K${row}`).format = { fill, wrapText: true, verticalAlignment: "top", borders: { bottom: { style: "thin", color: colors.line } } };
  ws.getRange(`A${row}:K${row}`).format.rowHeight = 48;
}
function action(row) {
  const t = row.placement_terms ?? {};
  if (row.status === "risk_hold") return "风险待核实，不自动回复";
  if (t.price_status === "free_editorial_route") return "可准备选题、摘要或文章";
  if (t.next_action === "awaiting_user_fact") return "客户补充对方要求的信息";
  if (t.next_action === "blocked_by_sector_only_disclosure_policy") return "客户决定是否披露公司信息";
  if (t.next_action === "find_official_contact") return "从官方联系页更换联系人";
  if (t.next_action === "client_review_editorial_route") return "客户决定是否走编辑投稿路线";
  if (row.referral_status === "awaiting_reply") return "已转负责联系人，等待回复";
  if (row.status === "quoted") return "客户核实报价及条款";
  return "待确认下一步";
}
function terms(row) {
  const t = row.placement_terms ?? {};
  return [
    t.link_attribute, t.additional_link_attribute && `另含 ${t.additional_link_attribute}`,
    t.permanence, t.placement_duration, t.turnaround,
    t.min_words && `${t.min_words} 词起`, t.max_links && `最多 ${t.max_links} 链`,
    t.content_requirement, t.fit_condition,
  ].filter(Boolean).join("；") || "未说明";
}
function dateText(value) {
  const raw = String(value ?? "");
  if (!raw) return "";
  const match = raw.match(/(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}年${match[2]}月${match[3]}日` : raw;
}
function sourceUrl(row) {
  return row.message_evidence_url || row.contact_source_url || (row.domain ? `https://${row.domain}` : "");
}

setTitle(1, "外链回复汇总", "仅含已收到人工回复的站点。报价为对方提供的信息，不代表接受、承诺或付款。更新日期：2026-09-08");
ws.getRange("A4:D4").values = [["人工回复", "明确报价", "免费编辑路线", "可直接交客户"]];
ws.getRange("A4:D4").format = { fill: colors.green, font: { bold: true, color: colors.white }, verticalAlignment: "center" };
ws.getRange("A5:D5").values = [[33, priceRows.length, freeRows.length, 10]];
ws.getRange("A5:D5").format = { fill: colors.light, font: { bold: true, size: 13, color: colors.ink }, verticalAlignment: "center" };
ws.getRange("A5:D5").format.rowHeight = 28;

let row = 8;
section(row, "免费编辑路线"); row += 1;
header(row, ["网站", "回复邮箱", "免费依据", "链接与周期", "内容要求", "客户下一步", "回复日期", "对应 URL", "", "", ""]); row += 1;
for (const item of freeRows) {
  const t = item.placement_terms ?? {};
  body(row, [item.site_name, item.reply_from, item.reply_excerpt, terms(item), t.content_requirement || t.fit_condition || "按对方投稿规则", action(item), dateText(item.last_reply_at), sourceUrl(item), "", "", ""]); row += 1;
}
row += 1;
section(row, "有明确报价"); row += 1;
header(row, ["网站", "回复邮箱", "价格", "币种", "主要条款", "是否预算内", "风险", "客户下一步", "回复日期", "对应 URL", ""]); row += 1;
for (const item of priceRows) {
  const t = item.placement_terms ?? {};
  const price = item.quote.amount_min === item.quote.amount_max ? item.quote.amount_min : `${item.quote.amount_min}-${item.quote.amount_max}`;
  const overBudget = item.quote.currency === "USD" ? item.quote.amount_min > 155 : true;
  body(row, [item.site_name, item.reply_from, price, item.quote.currency, terms(item), overBudget ? "待客户确认" : "预算内", (item.risk_flags ?? []).join("；") || "无", action(item), dateText(item.last_reply_at), sourceUrl(item), ""], item.status === "risk_hold" ? colors.risk : colors.white); row += 1;
}
row += 1;
section(row, "已回复但需要客户决定或补充信息"); row += 1;
header(row, ["网站", "回复邮箱", "对方明确要求", "当前状态", "客户下一步", "转介绍联系人", "回复日期", "对应 URL", "", "", ""]); row += 1;
for (const item of actionRows) {
  const t = item.placement_terms ?? {};
  const required = t.required_fact || t.content_requirement || item.reply_excerpt;
  body(row, [item.site_name, item.reply_from, required, item.status, action(item), t.referral_email || item.referral_contact || "", dateText(item.last_reply_at), sourceUrl(item), "", "", ""], colors.amber); row += 1;
}

const widths = [28, 30, 24, 12, 52, 26, 25, 54, 21, 54, 4];
widths.forEach((width, index) => ws.getRangeByIndexes(0, index, 1, 1).format.columnWidth = width);
ws.freezePanes.freezeRows(5);

const check = await wb.inspect({ kind: "table", range: "回复汇总!A1:I24", include: "values,formulas", tableMaxRows: 24, tableMaxCols: 9, maxChars: 12000 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);
const preview = await wb.render({ sheetName: "回复汇总", range: `A1:I${row}`, scale: 1, format: "png" });
await fs.writeFile(path.resolve(previewPath), new Uint8Array(await preview.arrayBuffer()));
await fs.mkdir(path.dirname(path.resolve(outputPath)), { recursive: true });
const blob = await SpreadsheetFile.exportXlsx(wb);
await blob.save(path.resolve(outputPath));
