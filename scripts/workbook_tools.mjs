#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";


function parseArgs(argv) {
  const [command, ...rest] = argv;
  const options = {};
  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith("--")) throw new Error(`Unexpected argument: ${token}`);
    const key = token.slice(2);
    const value = rest[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for --${key}`);
    options[key] = value;
    index += 1;
  }
  return { command, options };
}


function normalizeDomain(value) {
  const raw = String(value ?? "").trim().toLowerCase().split(/[（(]/u)[0].trim();
  if (!raw) return "";
  try {
    const url = new URL(raw.includes("://") ? raw : `https://${raw}`);
    return url.hostname.replace(/^www\./i, "").replace(/\.$/, "");
  } catch {
    return "";
  }
}


function parsePrice(value) {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) return value;
  const match = String(value ?? "").replaceAll(",", "").match(/(?:^|[^\d])(\d+(?:\.\d+)?)/);
  return match ? Number(match[1]) : null;
}


async function normalizeHistory(options) {
  if (!options.input || !options.output) throw new Error("normalize-history requires --input and --output");
  const input = await FileBlob.load(path.resolve(options.input));
  const workbook = await SpreadsheetFile.importXlsx(input);
  const sheet = workbook.worksheets.getItemAt(0);
  const used = sheet.getUsedRange();
  const rows = used?.values ?? [];
  const result = rows
    .filter((row) => row.some((cell) => cell !== null && cell !== ""))
    .map((row, index) => ({
      domain: normalizeDomain(row[0]),
      authority_metric_raw: row[1] ?? null,
      traffic_estimate_raw: row[2] ?? null,
      category: row[3] ?? "",
      link_attribute: row[4] ?? "",
      price_raw: row[5] ?? null,
      price_usd: parsePrice(row[5]),
      anchor_and_target_raw: row[6] ?? "",
      placement_url: String(row[7] ?? "").trim(),
      original_domain_raw: String(row[0] ?? "").trim(),
      source_row: index + 1,
    }));
  await fs.mkdir(path.dirname(path.resolve(options.output)), { recursive: true });
  await fs.writeFile(path.resolve(options.output), `${JSON.stringify(result, null, 2)}\n`, "utf8");
  console.log(`Normalized ${result.length} history rows to ${path.resolve(options.output)}`);
}


const COLORS = {
  navy: "#16324F",
  teal: "#1F7A8C",
  cyan: "#BFDBF7",
  pale: "#F3F8FC",
  yellow: "#FFF4CC",
  green: "#DDF4E4",
  red: "#FCE1E1",
  gray: "#667085",
  border: "#D7E0E8",
  white: "#FFFFFF",
};


function setTitle(sheet, rangeAddress, title) {
  const range = sheet.getRange(rangeAddress);
  range.merge();
  range.values = [[title]];
  range.format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 16 },
    verticalAlignment: "center",
  };
  range.format.rowHeight = 32;
}


function styleHeader(range) {
  range.format = {
    fill: COLORS.teal,
    font: { bold: true, color: COLORS.white },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.navy },
  };
  range.format.rowHeight = 34;
}


function seoScoreFormula(row) {
  const cells = ["AE", "AF", "AG", "AH", "AI", "AJ"];
  const weightRows = [4, 5, 6, 7, 8, 9];
  const numerator = cells.map((cell, index) => `IF(${cell}${row}="",0,${cell}${row}/5*'Scoring Guide'!$B$${weightRows[index]})`).join("+");
  const denominator = cells.map((cell, index) => `IF(${cell}${row}="",0,'Scoring Guide'!$B$${weightRows[index]})`).join("+");
  return `=IFERROR(ROUND((${numerator})/(${denominator})*100,0),"")`;
}


function geoScoreFormula(row) {
  const cells = ["AK", "AL", "AM", "AN", "AO", "AP"];
  const weightRows = [13, 14, 15, 16, 17, 18];
  const numerator = cells.map((cell, index) => `IF(${cell}${row}="",0,${cell}${row}/5*'Scoring Guide'!$B$${weightRows[index]})`).join("+");
  const denominator = cells.map((cell, index) => `IF(${cell}${row}="",0,'Scoring Guide'!$B$${weightRows[index]})`).join("+");
  return `=IFERROR(ROUND((${numerator})/(${denominator})*100,0),"")`;
}


function confidenceFormula(row, cells, weights) {
  const coverage = cells.map((cell, index) => `IF(${cell}${row}="",0,${weights[index]})`).join("+");
  return `=IF((${coverage})>=80,"high",IF((${coverage})>=55,"medium","low"))`;
}


function recommendationFormula(row, focus) {
  const scoreExpression = focus === "seo" ? `L${row}` : focus === "geo" ? `N${row}` : `AVERAGE(L${row},N${row})`;
  return `=IF(${scoreExpression}>=75,"优先",IF(${scoreExpression}>=60,"值得评估","补充候选"))`;
}


function writeCampaignSheet(sheet, campaign, candidateCount) {
  setTitle(sheet, "A1:H1", "SEO/GEO 外链资源发现 — Campaign");
  sheet.showGridLines = false;
  sheet.getRange("A3:H3").values = [["精选候选", "优先", "已购买域名", "明确合作型", "目标预算/条", "最高预算/条", "目标市场", "语言"]];
  styleHeader(sheet.getRange("A3:H3"));
  sheet.getRange("A4:H4").formulas = [[
    "=COUNTA('Candidates'!$A$2:$A$200)",
    '=COUNTIF(\'Candidates\'!$AA$2:$AA$200,"优先")',
    '=COUNTIF(\'Candidates\'!$X$2:$X$200,"是")',
    '=COUNTIF(\'Candidates\'!$G$2:$G$200,"明确合作型")',
    "",
    "",
    "",
    "",
  ]];
  sheet.getRange("E4:H4").values = [[
    campaign.target_price_usd,
    campaign.max_price_usd,
    (campaign.target_markets ?? []).join("、"),
    (campaign.languages ?? []).join("、"),
  ]];
  sheet.getRange("A4:H4").format = { fill: COLORS.pale, font: { bold: true, color: COLORS.navy }, wrapText: true };
  sheet.getRange("A4:H4").format.rowHeight = 48;
  sheet.getRange("E4:F4").format.numberFormat = '"$"#,##0';

  const rows = [
    ["Campaign 名称", campaign.campaign_name],
    ["目标网站", campaign.target_site],
    ["目标模式", campaign.focus ?? "balanced"],
    ["业务摘要", campaign.business_summary ?? ""],
    ["目标受众", campaign.audience_summary ?? ""],
    ["目标页面", (campaign.target_pages ?? []).join("\n")],
    ["核心主题", (campaign.core_topics ?? []).join("、")],
    ["相邻主题", (campaign.adjacent_topics ?? []).join("、")],
    ["内容角度", (campaign.content_angles ?? []).join("\n")],
    ["关键词", (campaign.keywords ?? []).join("、")],
    ["竞品", (campaign.competitors ?? []).join("\n")],
    ["排除项", (campaign.exclusions ?? []).join("、")],
    ["原始候选要求", "至少 90 个；不足时必须说明缺口，不得凑数"],
    ["交付要求", `${candidateCount} 个有证据且可联系的候选；邮箱确认后按 Campaign 授权自动外联`],
  ];
  sheet.getRange(`A7:B${6 + rows.length}`).values = rows;
  sheet.getRange(`A7:A${6 + rows.length}`).format = { fill: COLORS.cyan, font: { bold: true, color: COLORS.navy } };
  sheet.getRange(`B7:B${6 + rows.length}`).format = { wrapText: true, verticalAlignment: "top" };
  sheet.getRange(`A7:B${6 + rows.length}`).format.borders = { preset: "inside", style: "thin", color: COLORS.border };
  sheet.getRange("A:A").format.columnWidth = 19;
  sheet.getRange("B:B").format.columnWidth = 62;
  sheet.getRange("C:H").format.columnWidth = 18;
  sheet.freezePanes.freezeRows(3);
}


function writeCandidatesSheet(sheet, candidates, focus) {
  sheet.showGridLines = false;
  const headers = [
    "排名", "域名", "网站名", "国家/地区", "语言", "行业", "候选池", "发现方式", "证据 URL", "相关性理由",
    "合作证据", "SEO 分", "SEO 置信度", "GEO 分", "GEO 置信度", "权威指标", "指标来源", "流量估计", "流量来源",
    "估价下限 USD", "估价上限 USD", "价格依据", "价格置信度", "历史已购", "历史价格 USD", "风险提示", "推荐等级",
    "人工决定", "审核备注", "最后核验", "SEO-主题相关", "SEO-自然可见", "SEO-域名权威", "SEO-收录新鲜", "SEO-编辑质量",
    "SEO-上下文潜力", "GEO-主题权威", "GEO-可引用性", "GEO-实体透明", "GEO-可发现性", "GEO-内容新鲜", "GEO-自然提及",
  ];
  sheet.getRange(`A1:AP1`).values = [headers];
  styleHeader(sheet.getRange("A1:AP1"));

  const values = candidates.map((row) => [
    row.rank,
    row.normalized_domain,
    row.site_name,
    row.country_region,
    row.language,
    row.industry,
    row.pool === "explicit" ? "明确合作型" : "编辑机会型",
    row.discovery_method,
    row.evidence_url,
    row.relevance_reason,
    row.cooperation_evidence,
    null,
    null,
    null,
    null,
    row.authority_metric ?? null,
    row.metric_source ?? "",
    row.traffic_estimate ?? "",
    row.traffic_source ?? "",
    row.price_min_usd ?? null,
    row.price_max_usd ?? null,
    row.price_basis,
    row.price_confidence,
    row.purchased_before ? "是" : "否",
    row.previous_price_usd ?? null,
    Array.isArray(row.risk_flags) ? row.risk_flags.join("；") : String(row.risk_flags ?? ""),
    null,
    row.human_decision ?? "待审核",
    row.reviewer_notes ?? "",
    row.last_verified,
    row.seo_components?.topical_relevance ?? null,
    row.seo_components?.organic_visibility ?? null,
    row.seo_components?.domain_authority ?? null,
    row.seo_components?.indexation_freshness ?? null,
    row.seo_components?.editorial_quality ?? null,
    row.seo_components?.contextual_link_potential ?? null,
    row.geo_components?.topical_authority ?? null,
    row.geo_components?.citation_worthiness ?? null,
    row.geo_components?.entity_transparency ?? null,
    row.geo_components?.discoverability ?? null,
    row.geo_components?.content_freshness ?? null,
    row.geo_components?.natural_mention_fit ?? null,
  ]);
  if (values.length) sheet.getRange(`A2:AP${values.length + 1}`).values = values;
  if (values.length) sheet.getRange(`A2:AP${values.length + 1}`).format.rowHeight = 54;

  for (let index = 0; index < candidates.length; index += 1) {
    const row = index + 2;
    sheet.getRange(`L${row}`).formulas = [[seoScoreFormula(row)]];
    sheet.getRange(`M${row}`).formulas = [[confidenceFormula(row, ["AE", "AF", "AG", "AH", "AI", "AJ"], [30, 20, 15, 15, 10, 10])]];
    sheet.getRange(`N${row}`).formulas = [[geoScoreFormula(row)]];
    sheet.getRange(`O${row}`).formulas = [[confidenceFormula(row, ["AK", "AL", "AM", "AN", "AO", "AP"], [25, 25, 15, 15, 10, 10])]];
    sheet.getRange(`AA${row}`).formulas = [[recommendationFormula(row, focus)]];
  }

  const lastRow = Math.max(2, candidates.length + 1);
  const table = sheet.tables.add(`A1:AP${lastRow}`, true, "CandidatesTable");
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);

  sheet.getRange(`L2:L${lastRow}`).conditionalFormats.add("colorScale", { colors: [COLORS.red, COLORS.yellow, COLORS.green] });
  sheet.getRange(`N2:N${lastRow}`).conditionalFormats.add("colorScale", { colors: [COLORS.red, COLORS.yellow, COLORS.green] });
  sheet.getRange(`AB2:AB200`).dataValidation = { rule: { type: "list", values: ["待审核", "值得联系", "不合适", "稍后复核"] } };
  sheet.getRange(`T2:U${lastRow}`).format.numberFormat = '"$"#,##0';
  sheet.getRange(`Y2:Y${lastRow}`).format.numberFormat = '"$"#,##0';
  sheet.getRange(`L2:O${lastRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`A2:H${lastRow}`).format.verticalAlignment = "top";
  sheet.getRange(`I2:K${lastRow}`).format = { wrapText: true, verticalAlignment: "top" };
  sheet.getRange(`Z2:AC${lastRow}`).format = { wrapText: true, verticalAlignment: "top" };
  sheet.getRange(`AE2:AP${lastRow}`).format.horizontalAlignment = "center";

  const widths = {
    A: 7, B: 24, C: 24, D: 15, E: 12, F: 18, G: 14, H: 17, I: 46, J: 42, K: 36,
    L: 10, M: 12, N: 10, O: 12, P: 12, Q: 21, R: 15, S: 21, T: 14, U: 14,
    V: 20, W: 12, X: 11, Y: 14, Z: 28, AA: 13, AB: 13, AC: 28, AD: 13,
  };
  for (const [column, width] of Object.entries(widths)) sheet.getRange(`${column}:${column}`).format.columnWidth = width;
  sheet.getRange("AE:AP").format.columnWidth = 12;
}


function writeHistorySheet(sheet, history) {
  sheet.showGridLines = false;
  const headers = ["规范域名", "通用权威指标（原值）", "流量估计（原值）", "类别", "链接属性", "成交价 USD", "锚文本与目标页（原值）", "已发布文章 URL", "原始域名", "原表行号"];
  sheet.getRange("A1:J1").values = [headers];
  styleHeader(sheet.getRange("A1:J1"));
  const rows = history.map((row) => [
    row.domain,
    row.authority_metric_raw,
    row.traffic_estimate_raw,
    row.category,
    row.link_attribute,
    row.price_usd,
    row.anchor_and_target_raw,
    row.placement_url,
    row.original_domain_raw,
    row.source_row,
  ]);
  if (rows.length) sheet.getRange(`A2:J${rows.length + 1}`).values = rows;
  const table = sheet.tables.add(`A1:J${Math.max(2, rows.length + 1)}`, true, "PurchasedHistoryTable");
  table.style = "TableStyleMedium2";
  sheet.freezePanes.freezeRows(1);
  sheet.getRange(`F2:F${Math.max(2, rows.length + 1)}`).format.numberFormat = '"$"#,##0';
  sheet.getRange(`G2:I${Math.max(2, rows.length + 1)}`).format = { wrapText: true, verticalAlignment: "top" };
  const widths = [24, 20, 19, 16, 14, 14, 48, 48, 34, 10];
  widths.forEach((width, index) => sheet.getRangeByIndexes(0, index, 1, 1).format.columnWidth = width);
}


function writeSearchLogSheet(sheet, searchLog) {
  sheet.showGridLines = false;
  const headers = ["搜索词", "来源类型", "检查结果数", "保留候选数", "备注", "搜索时间"];
  sheet.getRange("A1:F1").values = [headers];
  styleHeader(sheet.getRange("A1:F1"));
  const rows = searchLog.map((row) => [
    row.query,
    row.source_type,
    row.results_reviewed,
    row.candidates_kept,
    row.notes,
    String(row.searched_at ?? "").replace("T", " ").replace("+08:00", " CST"),
  ]);
  if (rows.length) sheet.getRange(`A2:F${rows.length + 1}`).values = rows;
  const table = sheet.tables.add(`A1:F${Math.max(2, rows.length + 1)}`, true, "SearchLogTable");
  table.style = "TableStyleMedium2";
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("A:A").format.columnWidth = 52;
  sheet.getRange("B:B").format.columnWidth = 18;
  sheet.getRange("C:D").format.columnWidth = 14;
  sheet.getRange("E:E").format.columnWidth = 50;
  sheet.getRange("F:F").format.columnWidth = 22;
  sheet.getRange(`A2:F${Math.max(2, rows.length + 1)}`).format = { wrapText: true, verticalAlignment: "top" };
}


function writeScoringGuideSheet(sheet) {
  sheet.showGridLines = false;
  setTitle(sheet, "A1:C1", "评分标准与置信度");
  sheet.getRange("A3:C3").values = [["SEO 组件", "权重", "核验重点"]];
  styleHeader(sheet.getRange("A3:C3"));
  sheet.getRange("A4:C9").values = [
    ["topical_relevance", 30, "目标主题、产品或买家问题的直接相关性"],
    ["organic_visibility", 20, "公开搜索表现或有来源的自然流量证据"],
    ["domain_authority", 15, "行业权威或有来源的第三方指标"],
    ["indexation_freshness", 15, "可抓取、可收录、持续更新"],
    ["editorial_quality", 10, "原创、实用且有编辑责任"],
    ["contextual_link_potential", 10, "存在自然引用或品牌提及的上下文"],
  ];
  sheet.getRange("A12:C12").values = [["GEO 组件", "权重", "核验重点"]];
  styleHeader(sheet.getRange("A12:C12"));
  sheet.getRange("A13:C18").values = [
    ["topical_authority", 25, "持续覆盖相关主题并具备专业性"],
    ["citation_worthiness", 25, "解释性、数据性、专家型或参考型内容"],
    ["entity_transparency", 15, "机构、作者、资质和编辑身份清晰"],
    ["discoverability", 15, "内容可抓取、结构清楚且容易被发现"],
    ["content_freshness", 10, "近期更新或维护良好的常青内容"],
    ["natural_mention_fit", 10, "品牌或专业信息能够自然出现"],
  ];
  sheet.getRange("A21:C21").values = [["置信度", "覆盖权重", "规则"]];
  styleHeader(sheet.getRange("A21:C21"));
  sheet.getRange("A22:C24").values = [
    ["high", ">=80", "已核验至少 80% 权重，且最重组件有直接证据"],
    ["medium", ">=55", "已核验至少 55% 权重"],
    ["low", "<55", "证据不足；不把缺失项当作 0 分"],
  ];
  sheet.getRange("A27:C27").values = [["价格依据", "置信度", "解释"]];
  styleHeader(sheet.getRange("A27:C27"));
  sheet.getRange("A28:C32").values = [
    ["public", "high", "公开精确报价或公开范围"],
    ["same_domain_history", "medium", "同域名历史成交价；无日期时不视为当前报价"],
    ["historical_peer", "low", "相同行业和相近指标历史样本的四分位区间"],
    ["historical_global", "low", "历史价格总体四分位区间"],
    ["unknown", "low", "没有可靠依据，需后续询价"],
  ];
  sheet.getRange("A4:C32").format.borders = { preset: "inside", style: "thin", color: COLORS.border };
  sheet.getRange("A:A").format.columnWidth = 30;
  sheet.getRange("B:B").format.columnWidth = 15;
  sheet.getRange("C:C").format.columnWidth = 62;
  sheet.getRange("C:C").format.wrapText = true;
  sheet.freezePanes.freezeRows(1);
}


async function buildReport(options) {
  for (const name of ["campaign", "shortlist", "history", "search-log", "output", "preview-dir"]) {
    if (!options[name]) throw new Error(`build-report requires --${name}`);
  }
  const campaign = JSON.parse(await fs.readFile(path.resolve(options.campaign), "utf8"));
  const shortlistPayload = JSON.parse(await fs.readFile(path.resolve(options.shortlist), "utf8"));
  const history = JSON.parse(await fs.readFile(path.resolve(options.history), "utf8"));
  const searchLog = JSON.parse(await fs.readFile(path.resolve(options["search-log"]), "utf8"));
  const candidates = shortlistPayload.shortlist ?? [];

  const workbook = Workbook.create();
  const campaignSheet = workbook.worksheets.add("Campaign");
  const candidatesSheet = workbook.worksheets.add("Candidates");
  const historySheet = workbook.worksheets.add("Purchased History");
  const searchLogSheet = workbook.worksheets.add("Search Log");
  const scoringSheet = workbook.worksheets.add("Scoring Guide");

  writeCampaignSheet(campaignSheet, campaign, candidates.length);
  writeCandidatesSheet(candidatesSheet, candidates, campaign.focus ?? "balanced");
  writeHistorySheet(historySheet, history);
  writeSearchLogSheet(searchLogSheet, searchLog);
  writeScoringGuideSheet(scoringSheet);

  const outputPath = path.resolve(options.output);
  const previewDir = path.resolve(options["preview-dir"]);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.mkdir(previewDir, { recursive: true });

  const inspect = await workbook.inspect({
    kind: "table",
    range: `Candidates!A1:AD${Math.min(candidates.length + 1, 12)}`,
    include: "values,formulas",
    tableMaxRows: 12,
    tableMaxCols: 30,
    maxChars: 12000,
  });
  console.log(inspect.ndjson);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);

  for (const sheetName of ["Campaign", "Candidates", "Purchased History", "Search Log", "Scoring Guide"]) {
    const renderOptions = sheetName === "Candidates"
      ? { sheetName, range: `A1:AD${Math.min(candidates.length + 1, 12)}`, scale: 1, format: "png" }
      : { sheetName, autoCrop: "all", scale: 1, format: "png" };
    const preview = await workbook.render(renderOptions);
    const filename = `${sheetName.toLowerCase().replaceAll(" ", "-")}.png`;
    await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await preview.arrayBuffer()));
  }

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  console.log(`Created ${outputPath} with ${candidates.length} candidates.`);
}


const { command, options } = parseArgs(process.argv.slice(2));
if (command === "normalize-history") {
  await normalizeHistory(options);
} else if (command === "build-report") {
  await buildReport(options);
} else {
  throw new Error("Command must be normalize-history or build-report");
}
