#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";


function parseArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    const value = argv[i + 1];
    if (!key?.startsWith("--") || !value) throw new Error(`Invalid argument near ${key ?? "end"}`);
    options[key.slice(2)] = value;
  }
  for (const required of ["state", "shortlist", "history", "usage", "output", "preview-dir"]) {
    if (!options[required]) throw new Error(`Missing --${required}`);
  }
  return options;
}


const COLORS = {
  ink: "#26332F",
  muted: "#5F6B66",
  header: "#536B61",
  headerText: "#FFFFFF",
  pale: "#EEF2EF",
  line: "#D8DFDB",
  quote: "#EAF3EC",
  risk: "#F6E8E6",
  white: "#FFFFFF",
};


function unwrapRows(value) {
  if (Array.isArray(value)) return value;
  return value.shortlist ?? value.candidates ?? [];
}


function title(sheet, address, value, subtitle = "") {
  sheet.showGridLines = false;
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[value]];
  range.format = { fill: COLORS.white, font: { bold: true, size: 16, color: COLORS.ink }, verticalAlignment: "center" };
  range.format.rowHeight = 30;
  if (subtitle) {
    const row = Number(address.match(/\d+/)?.[0] ?? 1) + 1;
    const endCol = address.split(":")[1].replace(/\d+/g, "");
    const note = sheet.getRange(`A${row}:${endCol}${row}`);
    note.merge();
    note.values = [[subtitle]];
    note.format = { font: { color: COLORS.muted, size: 10 }, wrapText: true };
    note.format.rowHeight = 26;
  }
}


function header(range) {
  range.format = {
    fill: COLORS.header,
    font: { bold: true, color: COLORS.headerText },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.header },
  };
  range.format.rowHeight = 30;
}


function body(range) {
  range.format = {
    verticalAlignment: "top",
    wrapText: true,
    borders: { insideHorizontal: { style: "thin", color: COLORS.line } },
  };
}

function actionText(row) {
  const terms = row.placement_terms ?? {};
  const actions = {
    awaiting_user_fact: "待客户确认所需事实",
    blocked_by_sector_only_disclosure_policy: "待客户决定是否披露公司信息",
    find_official_contact: "从官方渠道更换联系人",
    client_prepare_submission: "可交客户：准备选题或摘要",
    client_review_over_budget: "超预算：交客户核实",
    awaiting_referred_contact_reply: "已转负责联系人，等待回复",
    client_review_editorial_route: "编辑投稿路线，交客户决定",
  };
  if (terms.next_action && actions[terms.next_action]) return actions[terms.next_action];
  if (terms.price_status === "free_editorial_route") return "可交客户：准备选题或摘要";
  if (row.referral_status === "awaiting_reply") return "已转负责联系人，等待回复";
  if (row.status === "quoted") return "交客户核实报价与条款";
  if (row.status === "rejected") return "已拒绝，不再跟进";
  if (row.status === "risk_hold") return "风险待核实，不自动回复";
  return "待判断下一步";
}

function termsSourceText(row) {
  const terms = row.placement_terms ?? {};
  if (terms.price_evidence) return terms.price_evidence;
  if (terms.price_status === "free_editorial_route") return "回复正文确认：免费编辑路线";
  if (row.quote?.raw) return `回复正文：${row.quote.raw}`;
  return "未提供报价";
}


function writeEffective(sheet, state) {
  const prospects = state.prospects ?? [];
  const humanStatuses = new Set(["quoted", "replied", "rejected", "unsubscribed", "risk_hold"]);
  const effective = prospects.filter((row) => humanStatuses.has(row.status));
  const referralCount = prospects.reduce((total, row) => total + (row.referral_outreach ?? []).length, 0);
  title(sheet, "A1:S1", "有效回复与报价", `Campaign：${state.campaign_name || ""} ｜ 最后更新：${new Date().toISOString().slice(0, 19).replace("T", " ")} UTC`);
  sheet.getRange("A4:G4").values = [["已发送线程", "人工回复", "有报价", "转介绍已联系", "风险待查", "待回复", "退信"]];
  header(sheet.getRange("A4:G4"));
  const contactEnd = Math.max(5, prospects.length + referralCount + 5);
  sheet.getRange("A5:G5").formulas = [[
    `=COUNTA('联系记录'!$C$6:$C$${contactEnd})`,
    `=COUNTIF('联系记录'!$G$6:$G$${contactEnd},"quoted")+COUNTIF('联系记录'!$G$6:$G$${contactEnd},"replied")+COUNTIF('联系记录'!$G$6:$G$${contactEnd},"rejected")+COUNTIF('联系记录'!$G$6:$G$${contactEnd},"unsubscribed")+COUNTIF('联系记录'!$G$6:$G$${contactEnd},"risk_hold")`,
    `=COUNTIF('联系记录'!$G$6:$G$${contactEnd},"quoted")`,
    `=COUNTIF('联系记录'!$A$6:$A$${contactEnd},"转介绍")`,
    `=COUNTIF('联系记录'!$G$6:$G$${contactEnd},"risk_hold")`,
    `=COUNTIF('联系记录'!$G$6:$G$${contactEnd},"awaiting_reply")`,
    `=COUNTIF('联系记录'!$G$6:$G$${contactEnd},"bounced")`,
  ]];
  sheet.getRange("A5:G5").format = { fill: COLORS.pale, font: { bold: true, size: 13, color: COLORS.ink } };
  sheet.getRange("A5:G5").format.numberFormat = "#,##0";
  sheet.getRange("A5:G5").format.rowHeight = 30;

  const headers = ["网站", "域名", "状态", "回复邮箱", "转介绍联系人", "转介绍状态", "报价下限", "报价上限", "币种", "价格状态", "链接属性", "永久性", "交付周期", "下一步", "价格/条款依据", "回复摘要", "风险", "Gmail Thread", "最后回复"];
  sheet.getRange("A8:S8").values = [headers];
  header(sheet.getRange("A8:S8"));
  const rows = effective.map((row) => [
    row.site_name ?? "", row.domain ?? "", row.status ?? "", row.reply_from ?? "",
    row.referral_contact ?? "", row.referral_status ?? "",
    row.quote?.amount_min ?? null, row.quote?.amount_max ?? null, row.quote?.currency ?? "", row.placement_terms?.price_status ?? "",
    row.placement_terms?.link_attribute ?? "", row.placement_terms?.permanence ?? "",
    row.placement_terms?.turnaround ?? "", actionText(row), termsSourceText(row), row.reply_excerpt ?? "",
    (row.risk_flags ?? []).join("；"), row.gmail_thread_url ?? row.thread_id ?? "", row.last_reply_at ?? "",
  ]);
  if (rows.length) {
    sheet.getRange(`A9:S${rows.length + 8}`).values = rows;
    body(sheet.getRange(`A9:S${rows.length + 8}`));
    sheet.getRange(`G9:H${rows.length + 8}`).format.numberFormat = "#,##0.00";
    sheet.getRange(`S9:S${rows.length + 8}`).format.numberFormat = "yyyy-mm-dd hh:mm";
    sheet.getRange(`A9:S${rows.length + 8}`).format.rowHeight = 48;
  } else {
    sheet.getRange("A9:S9").merge();
    sheet.getRange("A9:S9").values = [["尚未收到人工回复或报价。"]];
    sheet.getRange("A9:S9").format = { fill: COLORS.pale, font: { color: COLORS.muted }, verticalAlignment: "center" };
    sheet.getRange("A9:S9").format.rowHeight = 32;
  }
  const widths = [24, 22, 14, 26, 28, 16, 12, 12, 9, 20, 14, 12, 14, 28, 34, 52, 30, 36, 22];
  widths.forEach((width, i) => sheet.getRangeByIndexes(0, i, 1, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(8);
}


function writeMessages(sheet, messages, state) {
  const statusByDomain = new Map((state.prospects ?? []).map((row) => [row.domain, row.status]));
  title(sheet, "A1:P1", "邮件外联状态", `自动外联已启用 ｜ 发件邮箱：${state.mailbox?.detected_email || ""} ｜ 签名：${state.sender_identity?.signature || ""}`);
  sheet.getRange("A4:F4").values = [["邮件总数", "已发送/处理中", "待发送", "客户信息检查通过", "签名检查通过", "AI 套话检查通过"]];
  header(sheet.getRange("A4:F4"));
  const end = Math.max(9, messages.length + 8);
  sheet.getRange("A5:F5").formulas = [[
    `=COUNTA($C$9:$C$${end})`,
    `=COUNTA($F$9:$F$${end})-COUNTIF($F$9:$F$${end},"ready_to_send")`,
    `=COUNTIF($F$9:$F$${end},"ready_to_send")`,
    `=COUNTIF($L$9:$L$${end},"pass")`,
    `=COUNTIF($M$9:$M$${end},"pass")`,
    `=COUNTIF($N$9:$N$${end},"pass")`,
  ]];
  sheet.getRange("A5:F5").format = { fill: COLORS.pale, font: { bold: true, size: 13, color: COLORS.ink } };
  sheet.getRange("A5:F5").format.numberFormat = "#,##0";
  sheet.getRange("A5:F5").format.rowHeight = 30;

  const headers = ["排名", "网站", "域名", "收件邮箱", "邮箱匹配度", "状态", "主题", "邮件正文", "个性化依据", "证据 URL", "文案类型", "客户信息检查", "签名检查", "AI 套话检查", "重复风险", "备注"];
  sheet.getRange("A8:P8").values = [headers];
  header(sheet.getRange("A8:P8"));
  const rows = messages.map((row) => [
    // Current status comes from the Campaign state, not the pre-send message file.
    row.rank ?? null, row.site_name ?? "", row.domain ?? "", row.recipient ?? "",
    `${row.recipient_fit ?? ""}\n${row.recipient_fit_reason ?? ""}`, statusByDomain.get(row.domain) ?? row.status ?? "",
    row.subject ?? "", row.body ?? "", row.personalization_evidence ?? "", row.evidence_url ?? "",
    row.template_family ?? "", row.prohibited_disclosure_check ?? "", row.signature_check ?? "",
    row.banned_phrase_check ?? "", row.duplication_risk ?? "",
    (statusByDomain.get(row.domain) === "awaiting_reply" ? "已通过 Gmail 发送，等待回复。" : row.notes ?? ""),
  ]);
  if (rows.length) {
    sheet.getRange(`A9:P${rows.length + 8}`).values = rows;
    body(sheet.getRange(`A9:P${rows.length + 8}`));
    sheet.getRange(`A9:P${rows.length + 8}`).format.rowHeight = 118;
    sheet.getRange(`F9:F${rows.length + 8}`).conditionalFormats.add("containsText", { text: "contact_recheck", format: { fill: COLORS.risk } });
    sheet.getRange(`F9:F${rows.length + 8}`).conditionalFormats.add("containsText", { text: "ready_to_send", format: { fill: COLORS.quote } });
  }
  const widths = [7, 24, 22, 28, 42, 18, 38, 72, 48, 48, 22, 16, 14, 16, 12, 36];
  widths.forEach((width, i) => sheet.getRangeByIndexes(0, i, 1, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(8);
}


function writeReadableMessages(sheet, messages, state) {
  const statusByDomain = new Map((state.prospects ?? []).map((row) => [row.domain, row.status]));
  title(sheet, "A1:F1", "正式邮件文案", `自动外联已启用 ｜ 发件邮箱：${state.mailbox?.detected_email || ""} ｜ 已确认签名：${state.sender_identity?.signature || ""}`);
  sheet.getRange("A4:F4").values = [["说明", "以下邮箱均已通过前置匹配检查，正文不包含客户网站或公司信息。", null, null, null, null]];
  sheet.getRange("A4:F4").format = { fill: COLORS.pale, font: { color: COLORS.ink }, wrapText: true };
  let row = 6;
  for (const message of messages) {
    const heading = sheet.getRange(`A${row}:F${row}`);
    heading.merge();
    heading.values = [[`${message.rank}. ${message.site_name}  |  ${statusByDomain.get(message.domain) ?? message.status}`]];
    heading.format = { fill: COLORS.quote, font: { bold: true, color: COLORS.ink }, verticalAlignment: "center" };
    heading.format.rowHeight = 26;

    const details = [
      ["收件邮箱", message.recipient ?? ""],
      ["主题", message.subject ?? ""],
      ["正文", message.body ?? ""],
      ["邮箱判断", `${message.recipient_fit ?? ""} — ${message.recipient_fit_reason ?? ""}`],
      ["个性化依据", message.personalization_evidence ?? ""],
      ["证据 URL", message.evidence_url ?? ""],
      ["检查", `客户信息：${message.prohibited_disclosure_check} ｜ 签名：${message.signature_check} ｜ AI 套话：${message.banned_phrase_check} ｜ 重复风险：${message.duplication_risk}`],
      ["备注", statusByDomain.get(message.domain) === "awaiting_reply" ? "已通过 Gmail 发送，等待回复。" : message.notes ?? ""],
    ];
    for (let i = 0; i < details.length; i += 1) {
      const current = row + 1 + i;
      sheet.getRange(`A${current}`).values = [[details[i][0]]];
      sheet.getRange(`A${current}`).format = { font: { bold: true, color: COLORS.muted }, verticalAlignment: "top" };
      const valueRange = sheet.getRange(`B${current}:F${current}`);
      valueRange.merge();
      valueRange.values = [[details[i][1]]];
      valueRange.format = { wrapText: true, verticalAlignment: "top", borders: { bottom: { style: "thin", color: COLORS.line } } };
      valueRange.format.rowHeight = i === 2 ? 116 : i === 3 || i === 4 ? 40 : 28;
    }
    row += 10;
  }
  sheet.getRange("A:A").format.columnWidth = 16;
  sheet.getRange("B:F").format.columnWidth = 24;
  sheet.freezePanes.freezeRows(4);
}


function writeContacts(sheet, state) {
  title(sheet, "A1:P1", "联系记录", `发件邮箱：${state.mailbox?.confirmed_email || state.mailbox?.detected_email || "未确认"} ｜ 签名：${state.sender_identity?.signature || "未确认"} ｜ 授权：${state.authorization?.mode || "disabled"}`);
  const headers = ["类型", "网站", "域名", "收件邮箱", "联系方式来源", "发送时间", "状态", "跟进次数", "最后回复", "回复邮箱", "报价", "币种", "风险", "Thread ID", "Message ID", "上级 Thread"];
  sheet.getRange("A5:P5").values = [headers];
  header(sheet.getRange("A5:P5"));
  const rows = (state.prospects ?? []).flatMap((row) => {
    const original = [[
      "初始", row.site_name ?? "", row.domain ?? "", row.recipient ?? "", row.contact_source_url ?? "",
      row.sent_at ?? "", row.status ?? "", row.follow_up_count ?? 0, row.last_reply_at ?? "",
      row.reply_from ?? "", row.quote?.amount_min ?? null, row.quote?.currency ?? "",
      (row.risk_flags ?? []).join("；"), row.thread_id ?? "", row.message_id ?? "", "",
    ]];
    const referrals = (row.referral_outreach ?? []).map((referral) => [
      "转介绍", row.site_name ?? "", row.domain ?? "", referral.recipient ?? "",
      `回复转介绍：${referral.referred_by || "未署名"}`, referral.sent_at ?? "", referral.status ?? "",
      referral.follow_up_count ?? 0, referral.last_reply_at ?? "", referral.reply_from ?? "",
      referral.quote?.amount_min ?? null, referral.quote?.currency ?? "", (referral.risk_flags ?? []).join("；"),
      referral.thread_id ?? "", referral.message_id ?? "", referral.parent_thread_id ?? "",
    ]);
    return [...original, ...referrals];
  });
  if (rows.length) {
    sheet.getRange(`A6:P${rows.length + 5}`).values = rows;
    body(sheet.getRange(`A6:P${rows.length + 5}`));
    sheet.getRange(`K6:K${rows.length + 5}`).format.numberFormat = "#,##0.00";
    sheet.getRange(`F6:F${rows.length + 5}`).format.numberFormat = "yyyy-mm-dd hh:mm";
    sheet.getRange(`I6:I${rows.length + 5}`).format.numberFormat = "yyyy-mm-dd hh:mm";
    sheet.getRange(`A6:P${rows.length + 5}`).format.rowHeight = 38;
    sheet.getRange(`G6:G${rows.length + 5}`).conditionalFormats.add("containsText", { text: "quoted", format: { fill: COLORS.quote } });
    sheet.getRange(`G6:G${rows.length + 5}`).conditionalFormats.add("containsText", { text: "risk_hold", format: { fill: COLORS.risk } });
  }
  const widths = [10, 24, 22, 28, 32, 22, 16, 10, 22, 28, 12, 9, 30, 30, 30, 30];
  widths.forEach((width, i) => sheet.getRangeByIndexes(0, i, 1, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(5);
}


function writeCandidates(sheet, shortlist, state) {
  title(sheet, "A1:Q1", "候选资源", "符合流量、文章质量、公开邮箱和部门匹配门槛的正式候选");
  const statusByDomain = new Map((state.prospects ?? []).map((row) => [row.domain, row.status]));
  const headers = ["排名", "网站", "域名", "国家/地区", "行业", "月自然流量", "流量来源", "SEO 分", "GEO 分", "文章可索引性", "出站链接属性", "文章样本 URL", "推荐渠道", "公开邮箱", "邮箱匹配", "当前状态", "证据 URL"];
  sheet.getRange("A5:Q5").values = [headers];
  header(sheet.getRange("A5:Q5"));
  const rows = shortlist.map((row, index) => {
    const quality = row.quality_checks ?? {};
    const contact = row.contact_info ?? {};
    const domain = row.normalized_domain ?? row.domain ?? "";
    const sampleSize = quality.sample_size ?? 0;
    const techCount = quality.technically_indexable_count ?? 0;
    const linkSummary = `Follow ${quality.follow_count ?? 0} | Nofollow ${quality.nofollow_count ?? 0} | Sponsored ${quality.sponsored_count ?? 0} | UGC ${quality.ugc_count ?? 0}\nDominant: ${quality.dominant_link_attribute ?? "not_observed"}`;
    const evidence = [row.evidence_url, contact.recommended_url].filter(Boolean).join("\n");
    return [
      row.rank ?? index + 1, row.site_name ?? "", domain, row.country_region ?? "", row.industry ?? "",
      quality.traffic_estimate ?? row.traffic_estimate ?? null, quality.traffic_source ?? row.traffic_source ?? "",
      row.seo_score ?? null, row.geo_score ?? null,
      `${techCount}/${sampleSize} 技术可索引\n${quality.index_status ?? "not_checked"}`,
      linkSummary, (quality.sample_urls ?? []).join("\n"), contact.recommended_channel ?? "",
      contact.recommended_email ?? "", `${contact.recipient_fit ?? ""}\n${contact.recipient_fit_reason ?? ""}`,
      statusByDomain.get(domain) ?? "", evidence,
    ];
  });
  if (rows.length) {
    sheet.getRange(`A6:Q${rows.length + 5}`).values = rows;
    body(sheet.getRange(`A6:Q${rows.length + 5}`));
    sheet.getRange(`F6:F${rows.length + 5}`).format.numberFormat = "#,##0";
    sheet.getRange(`H6:I${rows.length + 5}`).format.numberFormat = "0";
    sheet.getRange(`A6:Q${rows.length + 5}`).format.rowHeight = 76;
  }
  const widths = [8, 24, 22, 16, 20, 14, 26, 10, 10, 20, 34, 54, 18, 28, 38, 16, 52];
  widths.forEach((width, i) => sheet.getRangeByIndexes(0, i, 1, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(5);
}


function writeKeyValue(sheet, name, titleText, data) {
  title(sheet, "A1:B1", titleText, "自动记录，便于复核本轮来源和消耗");
  sheet.getRange("A5:B5").values = [["项目", "值"]];
  header(sheet.getRange("A5:B5"));
  const rows = Object.entries(data ?? {}).map(([key, value]) => [key, Array.isArray(value) ? value.join("；") : typeof value === "object" && value !== null ? JSON.stringify(value) : value]);
  if (rows.length) {
    sheet.getRange(`A6:B${rows.length + 5}`).values = rows;
    body(sheet.getRange(`A6:B${rows.length + 5}`));
  }
  sheet.getRange("A:A").format.columnWidth = 30;
  sheet.getRange("B:B").format.columnWidth = name === "usage" ? 58 : 70;
  sheet.freezePanes.freezeRows(5);
}


function writeHistory(sheet, historyRows) {
  title(sheet, "A1:J1", "历史记录", "只用于查重和价格校准，不作为相似网站发现来源");
  const headers = ["域名", "权威指标（原值）", "流量估计（原值）", "分类", "链接属性", "成交价 USD", "锚文本与目标页", "已发布文章 URL", "原始域名", "原表行"];
  sheet.getRange("A5:J5").values = [headers];
  header(sheet.getRange("A5:J5"));
  const rows = (historyRows ?? []).map((row) => [
    row.domain ?? "", row.authority_metric_raw ?? null, row.traffic_estimate_raw ?? null,
    row.category ?? "", row.link_attribute ?? "", row.price_usd ?? null,
    row.anchor_and_target_raw ?? "", row.placement_url ?? "", row.original_domain_raw ?? "", row.source_row ?? null,
  ]);
  if (rows.length) {
    sheet.getRange(`A6:J${rows.length + 5}`).values = rows;
    body(sheet.getRange(`A6:J${rows.length + 5}`));
    sheet.getRange(`F6:F${rows.length + 5}`).format.numberFormat = '"$"#,##0.00';
    sheet.getRange(`A6:J${rows.length + 5}`).format.rowHeight = 38;
  }
  const widths = [24, 20, 20, 18, 14, 14, 48, 48, 28, 10];
  widths.forEach((width, i) => sheet.getRangeByIndexes(0, i, 1, 1).format.columnWidth = width);
  sheet.freezePanes.freezeRows(5);
}


async function main() {
  const options = parseArgs(process.argv.slice(2));
  const state = JSON.parse(await fs.readFile(path.resolve(options.state), "utf8"));
  const shortlist = unwrapRows(JSON.parse(await fs.readFile(path.resolve(options.shortlist), "utf8")));
  const historyRows = JSON.parse(await fs.readFile(path.resolve(options.history), "utf8"));
  const usage = JSON.parse(await fs.readFile(path.resolve(options.usage), "utf8"));
  const messages = options.messages ? JSON.parse(await fs.readFile(path.resolve(options.messages), "utf8")) : null;
  const responseStatuses = new Set(["quoted", "replied", "rejected", "unsubscribed", "risk_hold"]);
  const hasResponses = (state.prospects ?? []).some((row) => responseStatuses.has(row.status));
  const messageDomains = new Set((messages ?? []).map((row) => row.domain));
  const displayShortlist = messages ? shortlist.filter((row) => messageDomains.has(row.normalized_domain ?? row.domain)) : shortlist;
  const displayState = messages ? { ...state, prospects: (state.prospects ?? []).filter((row) => messageDomains.has(row.domain)) } : state;

  const workbook = Workbook.create();
  const effective = hasResponses ? workbook.worksheets.add("有效回复与报价") : null;
  const readableMessagesSheet = messages ? workbook.worksheets.add("邮件文案") : null;
  const messagesSheet = messages ? workbook.worksheets.add("邮件清单") : null;
  const effectiveOnly = !messages && !effective ? workbook.worksheets.add("有效回复与报价") : null;
  const candidates = workbook.worksheets.add("候选资源");
  const contacts = workbook.worksheets.add("联系记录");
  const usageSheet = workbook.worksheets.add("运行消耗");
  const history = workbook.worksheets.add("历史记录");

  if (readableMessagesSheet) writeReadableMessages(readableMessagesSheet, messages, displayState);
  if (messagesSheet) writeMessages(messagesSheet, messages, displayState);
  if (effective) writeEffective(effective, state);
  else if (effectiveOnly) writeEffective(effectiveOnly, state);
  writeCandidates(candidates, displayShortlist, displayState);
  writeContacts(contacts, displayState);
  writeKeyValue(usageSheet, "usage", "运行消耗", usage);
  writeHistory(history, historyRows);

  const inspectRange = hasResponses ? "有效回复与报价!A1:S15" : messages ? "邮件文案!A1:F25" : "有效回复与报价!A1:S15";
  const inspect = await workbook.inspect({ kind: "table", range: inspectRange, include: "values,formulas", tableMaxRows: 15, tableMaxCols: 15, maxChars: 10000 });
  console.log(inspect.ndjson);
  const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 200 }, summary: "final formula error scan" });
  console.log(errors.ndjson);

  const previewDir = path.resolve(options["preview-dir"]);
  await fs.mkdir(previewDir, { recursive: true });
  const renderPlans = messages ? [
    ...(hasResponses ? [{ sheetName: "有效回复与报价", range: "A1:S15" }] : []),
    { sheetName: "邮件文案", range: "A1:F55" },
    { sheetName: "邮件清单", range: "A1:P30" },
    { sheetName: "候选资源", range: "A1:Q35" },
    { sheetName: "联系记录", range: "A1:P40" },
    { sheetName: "运行消耗", range: "A1:B80" },
    { sheetName: "历史记录", range: "A1:J35" },
  ] : [
    { sheetName: "有效回复与报价", range: "A1:S15" },
    { sheetName: "候选资源", range: "A1:Q35" },
    { sheetName: "联系记录", range: "A1:P40" },
    { sheetName: "运行消耗", range: "A1:B80" },
    { sheetName: "历史记录", range: "A1:J35" },
  ];
  for (const { sheetName, range } of renderPlans) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }

  const outputPath = path.resolve(options.output);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const blob = await SpreadsheetFile.exportXlsx(workbook);
  await blob.save(outputPath);
  console.log(`Created ${outputPath}`);
}


await main();
