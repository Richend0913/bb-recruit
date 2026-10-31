#!/usr/bin/env node
/**
 * 公開される HTML に「仮置き」と「どこにも届かない導線」が残っていないか調べる門。
 *
 * なぜ要るか: 2026-10-31 時点で index.html の応募フォームが
 * action="https://formspree.io/f/placeholder" のまま本番に出ており、
 * Web から応募した人の情報が1件も届いていなかった。
 * 構文は正しく、表示も正常で、HTTP も 200 なので、誰も気づかない型の故障。
 *
 * 使い方: node scripts/check-live-links.mjs
 * 終了コード 1 = 不合格（CI を落とす）
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = process.cwd();
const SKIP_DIRS = new Set(['.git', 'node_modules', 'shots', '.github']);

/** 本文に出てきたら不合格にする文字列（“正直な文”を巻き込まないよう、記号まで含めて具体的に書く） */
const DEAD_PATTERNS = [
  { re: /\/f\/placeholder/i, why: 'Formspree のフォームIDが placeholder のまま＝送信先が存在しない' },
  { re: /action=["']\s*["']/i, why: 'form の action が空＝自分自身に送信して何も起きない' },
  { re: /action=["']#/i, why: 'form の action が # ＝送信しても何も起きない' },
  { re: /href=["']#["']/i, why: 'リンク先が # だけ＝押しても何も起きない' },
  { re: /https?:\/\/(example\.(com|org|net)|localhost|127\.0\.0\.1)/i, why: '公開物に例示用/ローカルのURLが残っている' },
  { re: /[＜<](?:あなたの|ここに|本番|自社|要記入|TODO)[^>＞]*[＞>]/u, why: '差し替え前のプレースホルダが残っている' },
  { re: /\b(TODO|FIXME|XXX)\b/, why: '作業メモが公開物に残っている' },
  { re: /\bdummy@|\bexample@|090-0000-0000|000-0000-0000/i, why: 'ダミーの連絡先が残っている' },
];

/** form があるのに送信先が外部URLでない、を別途見る */
function checkForms(html, file, problems) {
  const forms = html.match(/<form[^>]*>/gi) || [];
  for (const tag of forms) {
    const m = tag.match(/action=["']([^"']*)["']/i);
    const action = m ? m[1].trim() : '';
    if (!/^https?:\/\//i.test(action)) {
      problems.push({ file, why: `form の送信先が外部URLでない (action="${action}")`, line: tag.slice(0, 120) });
    }
  }
}

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name)) continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.html?$/i.test(name)) out.push(p);
  }
  return out;
}

const files = walk(ROOT);
const problems = [];

for (const f of files) {
  const html = readFileSync(f, 'utf8');
  const rel = relative(ROOT, f).replace(/\\/g, '/');
  html.split('\n').forEach((line, i) => {
    for (const { re, why } of DEAD_PATTERNS) {
      if (re.test(line)) problems.push({ file: `${rel}:${i + 1}`, why, line: line.trim().slice(0, 120) });
    }
  });
  checkForms(html, rel, problems);
}

console.log(`検査した HTML: ${files.length} 件`);
if (problems.length === 0) {
  console.log('✅ 届かない導線・仮置きは見つかりませんでした。');
  process.exit(0);
}
console.error(`\n❌ ${problems.length} 件。公開すると「押せるのに届かない」状態になります。\n`);
for (const p of problems) console.error(`  ${p.file}\n    理由: ${p.why}\n    該当: ${p.line}\n`);
process.exit(1);
