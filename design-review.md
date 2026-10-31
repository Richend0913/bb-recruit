# デザインQA記録 — 2026-10-31

対象:
- `setagaya-yupack/index.html`（新規）… http://127.0.0.1:8899/setagaya-yupack/ → 本番 https://richend0913.github.io/bb-recruit/setagaya-yupack/
- `index.html`（修正）… https://richend0913.github.io/bb-recruit/

ツール: Playwright MCP（browser_resize → navigate → take_screenshot → Read で目視 → console_messages）

## スクリーンショット

| ファイル | 内容 |
|---|---|
| `shots/setagaya-375-viewport.png` | 1周目・375px第一画面（不合格） |
| `shots/setagaya-375-viewport2.png` | 2周目・375px第一画面（合格） |
| `shots/setagaya-375-sim.png` | 375px 収入シミュレータ |
| `shots/setagaya-375-result.png` | 375px 試算結果カード |
| `shots/setagaya-375-table.png` | 375px 条件開示表 |
| `shots/setagaya-1280-hero.png` | 1280px デスクトップ |
| `shots/index-375-apply.png` | 修正後の応募セクション（死んだフォームを撤去） |
| `shots/index-375-areas.png` → `areas3.png` | エリア一覧の世田谷リンク（1周目→修正後） |

## 1周目で見つけた不合格点と修正

| # | 欠陥 | 検出 | 修正 |
|---|---|---|---|
| 1 | H1が文節の途中で折れた（「世田谷区のゆうパック／を、」「探して／います。」） | 375px viewportスクショ目視 | 文節を `<span class="ph">{display:inline-block}` で3分割、フォントを `clamp(26px, 6.6vw, 68px)` に縮小 |
| 2 | FVバッジが1行1個で縦に伸びた | 同上 | `display:grid; repeat(auto-fit, minmax(150px,1fr))` に変更＋文言短縮（2列化） |
| 3 | 「普通免許（AT可）で／OK」が2行に折れた | 2周目スクショ | 「普通免許（AT可）」に短縮 |
| 4 | 全エリア版の世田谷リンクで「→」が単独行に落ちた | `shots/index-375-areas.png` | サブラベルを `<b>` のブロックに分離、`flex-wrap:wrap` ＋左揃え |
| 5 | 「売上（個数 × 単価 × 稼働日／数）」が割れた | `shots/setagaya-375-result.png` | 空白を詰めて1語化 |
| 6 | GH Pagesプロジェクトページの favicon 404 | 既知の罠（skill記載） | インラインSVGの `<link rel="icon">` を両ページに追加 |

## 採点（2周目・ai-employee-site Phase 2.7 ルーブリック）

| # | 項目 | 点 | 備考 |
|---|---|---|---|
| 1 | 第一印象 | 4 | 黒×#d32f2f の既存LPと同じ語彙。「盛らない」を前面に出した構成は同業の募集ページと明確に違う |
| 2 | 見出しの改行 | 4 | 文節分割で意図した位置に固定。375/1280とも確認 |
| 3 | 本文組版 | 4 | シミュレータ導入文の末尾に1字の孤立（「…ありませ／ん。」）が残る。読みには影響しない |
| 4 | 余白 | 4 | セクション64px/90pxの2段。カード内は18〜26pxで統一 |
| 5 | 色 | 5 | アクセントは #d32f2f 1色（反転時 #ff5252/#ff8a80 の濃淡のみ） |
| 6 | 写真 | 3 | 公式サイトの既存写真を流用。世田谷の実写・実ドライバーの写真が無い（撮れば上がる） |
| 7 | 375px | 5 | 横スクロールなし（scrollWidth 360 ≤ 375／1280では1265 ≤ 1280）。全操作が親指で完結 |
| 8 | CTA | 5 | ヘッダーの電話・FVの電話・下部固定バー（電話／フォーム）・応募セクション。どのスクロール位置からも1タップ |
| 9 | 情報設計 | 5 | 「正直に書く宣言 → 自分で試算 → 全条件開示 → 1日の流れ → FAQ → 応募」。面談で話す順と一致 |
| 10 | 禁止リスト | 5 | 収入表示5原則の違反ゼロ（legal-check.md 参照）。placeholder・ダミーリンクなし |
| 11 | 固定バー重なり | 5 | 下部固定バーは `body{padding-bottom:72px}` で本文を隠さない。768px以上では非表示。viewportスクショで確認済み |

**平均 4.45 / 2点以下なし → 合格**

## コンソール

`browser_console_messages level=error` → **エラー0・警告0**（favicon追加後）

## 本番URLでの確認

- `https://richend0913.github.io/bb-recruit/setagaya-yupack/` … HTTP 200、本文「任せられる人を」を含むことを確認（200だけで合格にしない）
- `https://richend0913.github.io/bb-recruit/` … `formspree` の出現回数 **0**（死んだフォームが本番から消えたことを確認）

## 次に上げるなら

- 項目6（写真）: 世田谷の実際の配達風景・実ドライバーの写真。本人の承諾を取ってから差し替える（ステマ規制・肖像権）
- 「先輩の声」セクションは**実在者がいないので意図的に作っていない**。実名・取得経緯を記録できる人が出たら追加する
