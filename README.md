# SEO/GEO 外链发现与邮件外联

**简体中文** | [English](README.en.md)

用于寻找外链合作媒体、核实公开业务联系方式、准备外联邮件、记录 Gmail 发送状态、跟踪回复及报价，并导出结果表的代理工作流项目。

这是原邮件外联版本的独立公开副本，来自 2026-10-19 归档项目。公开副本保留工作流、脚本、测试和虚构示例；移除了代码中写死的历史客户名称，并替换了测试中的原发件人署名。原始归档保留在本地。

## 功能

- 发现候选网站，分别评估 SEO / GEO 质量、流量和合作证据。
- 查找公开业务邮箱，检查收件人职责与邮件域名。
- 根据已核实的资料生成个性化邮件，检查签名、禁止披露的信息和重复文案。
- 管理发送、跟进、转介绍、退信、回复、报价和风险标记。
- 按目标数量和预算管理持续外联，生成候选、联系记录与报价工作表。

## 项目结构

```text
SKILL.md         代理工作流入口与授权边界
agents/          代理界面元数据
assets/          不含真实账号的 campaign 配置示例
references/      数据契约、筛选标准、邮件风格与外联规则
scripts/         研究、文案、状态管理与表格工具
tests/           Python 单元测试
```

## 环境与使用

Python 3.10+。Python 脚本仅使用标准库；运行测试不需要邮箱或付费 API。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/pipeline.py --help
python3 scripts/outreach_state.py --help
python3 scripts/compose_messages.py --help
```

开始一个本地项目：

```bash
mkdir -p campaigns/my-campaign
cp assets/campaign-brief.example.json campaigns/my-campaign/campaign.json
```

编辑配置中的目标网站、市场、预算与已批准事实，并根据 `references/data-contract.md` 准备输入数据。具体步骤和筛选顺序见 [SKILL.md](SKILL.md)。

### 邮箱与自动化

邮件发送和读取由运行此工作流的代理调用已连接的 Gmail 工具完成。本仓库不包含独立 SMTP 发送服务、Gmail OAuth 客户端或常驻调度服务；只运行 Python 脚本不会自动发送邮件。实际运行需要支持 Gmail 连接器和计划任务的代理环境，并完成工作流要求的邮箱身份、发件人签名和外联授权配置。

示例配置默认为 `send_paused`，可准备文案但不会授权发送。首次启用 `automatic_outreach` 前，应确认邮箱、签名、发送范围和跟进设置。

### 可选 DataForSEO

需要使用 DataForSEO 检索或流量估算时，配置 `DATAFORSEO_LOGIN` 与 `DATAFORSEO_PASSWORD` 环境变量；macOS 也支持按该登录名从 Keychain 的 `seo-geo-link-finder-dataforseo` 服务读取密码。API 调用需要自行提供账号，可能产生费用。脚本不会自动读取 `.env` 文件。

### Excel 导出

`*.mjs` 工具依赖 Node.js 与 `@oai/artifact-tool`。该依赖需要运行环境提供，本仓库不附带，也不保证可从公共 npm 安装。缺少此依赖时仍可使用 Python 工作流和 JSON 结果；Excel 渲染与导出需要另行配置兼容环境。

## 数据与边界

真实客户名单、邮箱身份、实际邮件内容、Gmail 消息与线程 ID、历史报价和 Excel 导出不包含在公开仓库中。`campaigns/`、`outputs/`、凭据和运行产物已在 `.gitignore` 中排除。

工作流只收集合作回复与报价，不购买外链、不承诺付款或接受合同。邮件外联应遵守服务商规则和收件人的退出要求。
