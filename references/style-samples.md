# Style samples

A few Japanese-to-Chinese pairs that show the voice this skill should reproduce. The
translator reads this file before translating and matches its register, sentence rhythm,
and how it handles honourifics and first-person pronouns.

Keep it short. Three to eight pairs is enough; more dilutes the signal.

Only the content under the `## Sample pairs` heading is sent to the model. Everything above
it — these rules and the format notes — stays out of the prompt on purpose. The heading
must be present, and the pairs must live under it.

## The hard rule

Do not paste a fan translation (汉化组译文) into this file. Those are copyrighted
derivative works, and committing them to a public repository redistributes infringing
content. It is also not subtle: translation groups file DMCA notices and the host act on
them.

The same rule covers official or licensed excerpts, even ones the user pastes into the
session. An excerpt is calibration material: read it in-session, adopt its decisions
(names, format, register), then discard it. What may be committed is only the derived
decisions — a glossary entry, a style rule — never the excerpt itself, here or anywhere
else in the repository.

Acceptable sources, in order of preference:

1. **Your own past translations.** The best sample you can get, and unambiguously yours.
2. **Public-domain works.** Aozora Bunko Japanese originals paired with a Chinese
   translation whose translator died more than 50 years ago (public domain in China).
3. **Author-permitted works.** Some なろう and カクヨム authors explicitly allow
   translation, sometimes with a translation licence stated in the work's afterword.
   Check before using and cite the permission.

If a sample cannot be sourced under one of those three, write a synthetic pair instead —
invent a line in the right style rather than copying someone else's.

## Format

One pair per block: the Japanese, then the line, then the Chinese. Add a one-line note
whenever the pair demonstrates a specific decision.

````markdown
### 敬称を残す例 / honourific kept

**JA:** 「おはよう、ユウキさん」
**ZH:** 「早上好，悠纪さん」

Keeps さん because the speaker's distance from 悠纪 is a plot point. Do not write 悠纪桑.
````

## Sample pairs

The pairs below are synthetic illustrations written for this file. They are not taken
from any published work, so they carry no third-party rights. Replace them with your own
material once you have it.

### Honourific kept when distance matters

**JA:** 「おはよう、ユウキさん」
**ZH:** 「早上好，悠纪さん」

### Honourific dropped when it would sound stiff in Chinese

**JA:** 「お兄ちゃん、また負けたの?」
**ZH:** 「哥，你又输了?」

お兄ちゃん becomes a natural kinship term rather than a literal 欧尼酱.

### First-person pronoun distinguishes the speaker

**JA:** 「あたし、絶対に負けない」
**ZH:** 「我才不会输呢」

あたし is rendered with a colloquial, slightly girlish register instead of a neutral 我.

**JA:** 「僕は……たぶん、そう思う」
**ZH:** 「我……大概也是这么想的吧」

僕 gets a softer, more hesitant register than 俺 would.

### Onomatopoeia by feeling, not by word

**JA:** 「どきっ、と胸が鳴った」
**ZH:** 「心里咯噔一下」

どきっ is translated as the feeling it describes, not as a sound-effect string.

### Sentence rhythm

**JA:** 「魔剣を握りしめた。もう、迷わない」
**ZH:** 「他握紧了魔剑。不再犹豫。」

Two short sentences stay two short sentences. Do not merge them into one flowing clause.
