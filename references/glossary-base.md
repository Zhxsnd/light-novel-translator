# Baseline glossary: 異世界 / なろう系 works

The terms below recur in essentially every 異世界転生 web novel. Lock them once, then add the
work's own invented names on top.

Two layers, applied in this order:

1. **Baseline** — this file. Genre-wide system, item and role vocabulary.
2. **Work-specific** — the invented names, skills and places extracted from the text itself in
   Step 2.

The baseline is what makes this scale. A brand-new work may invent 「虚空斬」, which no corpus
will ever contain, but it will still use スキル, ギルド and レベル — and those have to match
every other translation the reader has already seen. A corpus cannot supply the invented names
and does not need to supply these.

## Fixed renderings

| Japanese | Chinese | Notes |
|---|---|---|
| スキル | 技能 | A few translations keep the katakana or transliterate. 技能 is the common reading |
| ステータス | 状态 | 状态栏 or 属性面板 when an actual UI panel is being described |
| 転生 | 转生 | 重生 appears, but 转生 is the established term |
| レベル | 等级 | |
| 経験値 | 经验值 | |
| ギルド | 公会 | 冒险者公会 when the guild in question is specifically the adventurers' |
| パーティ | 队伍 | 小队 for small groups; 团队 reads corporate |
| 魔剣 | 魔剑 | |
| 聖女 | 圣女 | |

## Not fixed — ask the user once, then lock it

These have two or more established renderings. Pick one per book and never mix them.

| Japanese | Candidates | Notes |
|---|---|---|
| ダンジョン | 地下城 / 迷宫 / 地牢 | 迷宫 is common in なろう circles; 地下城 is what the licensed Chinese editions use — it is in the licensed title of ダンジョンに出会いを求めるのは間違っているだろうか. 迷宫 is the safer default unless the work leans on the "city" metaphor |
| チート | 外挂 / 开挂 / 作弊 | 外挂 is the community default and reads naturally in dialogue |
| アイテムボックス | 道具箱 / 物品箱 / 収纳箱 / keep as-is | No settled rendering. Pick one, or leave the katakana |

## Sources

A term-to-term mapping is factual and can be quoted freely. The compilations it appears in are
not, so cite individual entries rather than copying a whole dictionary file.

- [re0-web 译名字典](https://github.com/re-zero-khis/re0-web/blob/539e35ce/gitbook/markdown/translation.md)
  — the most rigorous field structure I found: 日文 · 中文译名 · 中文又译 · 首现 · 备注.
- [未元境界《构筑异世界的通用法则》](https://molun.net/the-universal-rules-of-making-parallel-world/)
  — walks through status-panel elements, チート renderings and the guild rank system.
- [未元境界《轻小说中的冒险者公会浅描》](https://molun.net/thin-description-about-the-adventurer-guild-of-light-novel/)
- Baka-Tsuki per-work terminology pages (e.g. [Mushoku Tensei](https://www.baka-tsuki.org/project/index.php?title=Mushoku_Tensei_Nomi_e_Terminologia),
  [Log Horizon](https://www.baka-tsuki.org/project/index.php?title=Log_Horizon_Specific_Guidelines))
  — English, but useful for confirming the Japanese sense of a term.
- [Bangumi](https://bangumi.tv/) — official Chinese titles, for confirming which publisher
  picked which rendering.

## Using this file

Step 2 writes `glossary.json`. Seed it from the two tables above, then add the work's own
names, skills and places. Do not send this file to the model directly — it is a reference for
building `glossary.json`, and the Japanese column alone would be noise in a prompt.

For a work outside the 異世界 / なろう系 genre, most of this table does not apply. Drop it and
build the baseline from that genre's own recurring vocabulary instead.
