# 数学建模审查与论文图表

面向国赛、美赛与一般数学建模的独立 Agent Skill。它与另一 Skill 共享网站导航，但不依赖另一仓库才能使用。

[在线导航与阅读](https://strider002.github.io/math-modeling-review/) · [下载与使用](https://strider002.github.io/math-modeling-review/download.html) · [建模方法库](https://github.com/Strider002/math-modeling-library-skill) · [审查与论文图表](https://github.com/Strider002/math-modeling-review)

## 这个 Skill 做什么

只读审查已有模型、代码、结果与论文，根据模型、任务和主张规划论文需要的图与表，明确证据缺口与补充动作。

本仓库根目录的 [SKILL.md](SKILL.md) 是 Agent 入口；`references/`、`scripts/`、`assets/` 和 `agents/` 为 Skill 资源。`docs/` 与 `web-tools/` 仅用于网站和打包，不是运行 Skill 的前置依赖。

## 下载与使用

从网站的“下载与使用”页面获取独立 ZIP，解压后保留 `math-modeling-review/SKILL.md` 与完整配套目录。ZIP 不含网站依赖或 Git 历史。使用前核对下载页的 SHA-256。

Codex 可将解压后的完整目录放入项目的 `.agents/skills/`，再在对话中显式调用 `$math-modeling-review`；不要覆盖已有同名 Skill。其他支持 `SKILL.md` 的工具按其官方说明配置，未逐一验证兼容性。参见 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。

示例：`$math-modeling-review 只读检查现有结果是否支持论文结论，并列出对应模型的候选图表与所需字段。`

PowerShell 辅助工具要求 PowerShell 7；阅读文档与规划任务不要求运行脚本。审查包默认只读，任何执行代码、重算或改稿仍须符合用户授权。

## 本地预览网站

使用 Node.js 22 或更高版本：

```sh
npm ci
npm test
npm run build
npm run preview
```

`npm run build` 只读取 `publication.json` 中显式批准的 Skill 文件，生成网页、下载包及校验信息。添加公开文件时先审查内容，再更新清单；不要让构建程序扫描私人目录。

两个仓库的 `docs/.vitepress/portal.json`、公共主题和构建工具来自同一套发布模板；修改公共导航时应同步到两个仓库。两站均保留完整导航，不要求浏览器从另一个站点加载脚本。

## 发布与维护边界

- 仅包含获准公开的文本、模板、来源元数据与工具；不提供第三方原始论文、数据或图片。
- 未公开成果及其派生内容不得进入仓库、提交历史、网站搜索索引或下载包。
- 不承诺获奖、提高获奖率、模型必然正确或绝对无风险。
- 工程验证不等于重新运行所有案例，也不等于当届赛事合规审查。
- 软件使用 MIT；原创文档使用 CC BY 4.0；第三方材料另受原许可约束，见 [许可证范围](LICENSES.md)。

由 Strider002 维护。
