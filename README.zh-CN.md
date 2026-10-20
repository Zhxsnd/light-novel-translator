# light-novel-translator

[English](README.md) | **中文**

一个把日文轻小说（ラノベ 与网络小说）翻译成中文的 agent skill，核心是**先锁死术语表**——
让角色名、技能名、每个角色的说话语气从第一章到最后一章始终一致。

多数翻译工具把小说当成一整篇长文档。这个 skill 把它当成一本书：动笔前先定术语，在
分块边界之间传递上下文，交付前先量化评测再下结论。

## 安装

仓库根目录本身就是 skill，因此任何支持 open skills 格式的 agent 都能直接加载使用。

```bash
npx skills add Zhxsnd/light-novel-translator
```

也可以手动安装——克隆仓库，把整个文件夹拷进你所用的 agent 的 skills 目录：

```bash
git clone https://github.com/Zhxsnd/light-novel-translator
cp -r light-novel-translator ~/.claude/skills/     # Claude Code
cp -r light-novel-translator ~/.trae-cn/skills/    # Trae（国内版）
```

安装过程不向全局写入任何东西，也不执行任何代码。

## 环境要求

- **Python 3.9+。** 所有脚本只用标准库，没有任何需要 `pip install` 的依赖。
- **一个 OpenAI 兼容的对话接口** —— 本地 SakuraLLM 服务、DeepSeek，或任何实现了
  `/chat/completions` 的服务。

```bash
export LNT_BASE_URL=http://127.0.0.1:8080/v1   # 或 https://api.deepseek.com/v1
export LNT_API_KEY=sk-...
export LNT_MODEL=sakura                        # 或 deepseek-chat
```

SakuraLLM（`Sakura-GalTransl-7B`）是专为日译中轻小说与 Galgame 文本训练的模型，在这类
素材上明显优于通用模型。但有两点要注意：7B 量化版大约需要 6 GB 显存，小显存笔记本跑不
动；它的许可协议是 CC-BY-NC-SA，因此**不得**用于出售翻译成果。

## 不用 API key 就能跑

两条命令，看清这个 skill 到底做了什么——不需要接口，也不花钱。都跑在 `examples/` 里那段
原创样例上。

```bash
# 把样例切分成 chunk
python scripts/chunk_source.py --input examples/sample-source.txt --out-dir chunks

# 打印真正会发给模型的那个请求
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary examples/sample-glossary.json \
  --style-samples references/style-samples.md --dry-run
```

第二条命令不调用任何接口。它会把 system prompt 打印出来——你锁定的术语表和风格规则就在
开头——以及 user message 的前半段。这个 prompt 才是产品本体，其余都只是管道。
`examples/README.md` 说明了这段样例专门用来暴露哪些坑。

## 快速开始

```bash
# 1. 把生肉切成章节与场景
python scripts/chunk_source.py --input raws/novel.txt --out-dir chunks --max-chars 3500

# 2. （可选）从日中平行语料里挖出术语
python scripts/mine_glossary.py --pairs pairs.jsonl --glossary-out glossary.json

# 3. 翻译，然后读一遍记录并和用户确认 glossary.json
python scripts/translate_chunks.py \
  --chunks-dir chunks --glossary glossary.json --out-dir out \
  --style-samples references/style-samples.md --context-chars 300

# 4. 合成整本书
python scripts/export_book.py \
  --chunks-dir chunks --translated-dir out --out book.epub \
  --format epub --title "作品名" --author "著者" --lang zh
```

第 3 步跑到一半中断了？原命令再跑一遍即可，已完成的 chunk 会自动跳过。

## 工作流程

1. **导入** —— 把 EPUB、なろう/カクヨム 下载件或纯文本，统一整理成按章节的文本。
2. **锁定术语表** —— 提取所有反复出现的专有名词并给出译法，然后**停下来**请用户确认。
   这一步不可跳过。
3. **分块** —— 先按章节切，再按场景断点切，绝不在句中切断。
4. **翻译** —— 每次请求都带上术语表、风格规则、最相关的风格样例，以及上一块的尾部作为
   只读上下文。
5. **校验** —— 逐个核对术语表条目，并专门排查机翻痕迹，例如 `さん` 译成「桑」、所有角色
   的第一人称都塌成「我」。
6. **评测** —— 先在留出集上打分，再宣布某个 prompt 版本更好。方法见 `references/eval.md`。
7. **导出** —— EPUB 3、双语对照或纯译文。

## 文件说明

| 路径 | 说明 |
|---|---|
| `SKILL.md` | skill 本体：agent 遵循的工作流程 |
| `scripts/chunk_source.py` | 把生肉切成 chunk，并生成带哈希的 manifest |
| `scripts/mine_glossary.py` | 从平行语料中提出术语表候选 |
| `scripts/translate_chunks.py` | 执行翻译，支持断点续跑、失败重试与有界上下文 |
| `scripts/export_book.py` | 生成 EPUB 3 / 双语 / 纯文本 |
| `scripts/verify_glossary.py` | 翻译后的确定性检查：假名残留、敬称误译、人称塌缩 |
| `tests/` | 脚本的标准库 unittest 测试 |
| `references/capability-boundaries.md` | 这个 skill 今天覆盖什么、部分覆盖什么、刻意不做什么 |
| `references/data-sources.md` | 合法获取日中平行语料的渠道 |
| `references/eval.md` | 如何量化质量，而不是凭感觉 |
| `references/glossary-base.md` | 题材基线：異世界 通用词汇，提前锁死 |
| `references/style-samples.md` | 日中对照样例，以及选材的合法边界 |
| `examples/` | 零密钥演示：原创样例、术语表，以及该检查什么 |

## 法律

翻译自己没有权利的作品并公开发布或再分发，属于侵权。なろう 与 カクヨム 都禁止未经授权
公开传播译文。民间汉化本身也是受版权保护的演绎作品，因此同样不得提交进本仓库——哪些素
材可以合法用作参考，见 `references/style-samples.md`。

请只在你有权翻译的素材上使用本 skill：你自己的作品、公有领域作品，或作者已授予翻译许可
的作品。

## 许可证

MIT，见 `LICENSE`。
