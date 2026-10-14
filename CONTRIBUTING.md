# Contributing to Human Atlas 3D

感谢你参与改进。小范围、可复现的修改最容易审查；界面、性能、翻译和内容修订均欢迎。

## 本地开发

```bash
npm ci
npm run dev
```

已编码模型位于 `public/data/`，一般功能开发不需要重跑 Python 管线。

提交前运行：

```bash
npm run check:assets
npm run build
```

修改模型或渲染后，检查男 / 女模型、图层开关、正 / 侧 / 背面、结构点击、部位特写及 Explode。截图工具与可选几何校验见 [模型管线指南](docs/PIPELINE.md)。

## 报告问题与提交 PR

- 问题报告请包含浏览器与操作系统、复现步骤、预期 / 实际表现，以及结构或部位名称。
- PR 说明解决的问题、最终行为与验证结果；视觉修改附前后截图。
- 保持变更范围集中；生成模型应同时更新 `public/data/manifest.json` 和对应二进制块。
- 保留数据来源与许可说明，不提交原始视频、生成缓存、依赖目录或本地备份。

## 解剖与学习内容

结构名称与条目位于 `src/content/`，部位结构规则位于 `src/regions-def.js`。内容修订请附可靠来源；涉及参考模型、示意性重建和个体差异时，应明确区分。避免将教育说明写成个人诊疗建议。

## Licenses

Code and original project text are contributed under MIT. Adapted anatomical assets and model screenshots are distributed under CC BY 4.0 with their source attribution. New external assets must include their source and compatible license information in `public/ATTRIBUTION.md`.
