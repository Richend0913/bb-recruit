#!/usr/bin/env python3
"""
見出しの明朝（字を絞った woff2）に、ページで明朝を使う字が全部入っているかを調べる門。

なぜ要るか:
  setagaya-yupack の見出しは「しっぽり明朝 B1 ExtraBold」を、ページで使う字だけに絞って配っている
  （全字の TTF は 15MB、絞ると数十KB）。文言を直したときに新しい字が woff2 に無いと、
  その字だけ端末の明朝で出て見た目が崩れるが、表示は壊れないので誰も気づかない。

何を見るか（check。既定）:
  1. <style> の中で明朝（var(--f-mincho) / "Shippori Mincho B1"）を指定している規則のセレクタが、
     この門が字を集められる対象（h1・h2・h3・.mc）だけであること。
     ほかの要素に明朝を付けたら、ここで落ちる（＝門が字を取りこぼす状態を作らない）
  2. HTML の style 属性で明朝を指定していないこと
  3. h1・h2・h3・class="mc" の要素の中の字が、全部 woff2 の文字表（cmap）にあること
     （その中でも、CSS で明朝以外の書体を指定したクラスの要素＝H1 の中の .hero-labels・数字の .nm などは数えない）
  4. Barlow（数字用）の woff2 が ASCII（U+0020-007E）を全部持っていること
  5. @font-face が指す woff2 が実在すること

字を足す（build）:
  python scripts/check-font-subset.py --build --src <ShipporiMinchoB1-ExtraBold.ttf> [--barlow-src <BarlowCondensed-SemiBold.ttf>]
  元の TTF は Google Fonts の配布元（SIL OFL 1.1）:
    https://github.com/google/fonts/tree/main/ofl/shipporiminchob1
    https://github.com/google/fonts/tree/main/ofl/barlowcondensed
  文言を直したら build → check の順に通す。

使い方: python scripts/check-font-subset.py [--page setagaya-yupack/index.html]
終了コード 1 = 不合格
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PAGE = os.path.join(ROOT, 'setagaya-yupack', 'index.html')
MINCHO_RE = re.compile(r'var\(\s*--f-mincho\s*\)|Shippori\s+Mincho', re.I)
MINCHO_TAGS = {'h1', 'h2', 'h3'}
MINCHO_CLASS = 'mc'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
# 文言を直したときに出やすい約物と数字は、使っていなくても必ず入れておく
ALWAYS = '、。，．・：；？！ー〜～／（）「」『』【】…―‐-0123456789'


class Collector(HTMLParser):
    """明朝で表示される要素（h1/h2/h3/.mc）の中の字を集める。

    見出しの中でも、CSS で明朝以外の書体を指定したクラス（例: H1 の中の小さなゴシックの行 .hero-labels、
    数字用の .nm）の中は明朝で出ないので数えない。その中に .mc や h1〜h3 があれば、そこから再び数える。
    """

    def __init__(self, other_font_classes: set[str] | None = None):
        super().__init__(convert_charrefs=True)
        # (tag, 状態) 状態は 'm'=ここから明朝 / 'g'=ここから明朝以外 / None=親を引き継ぐ
        self.stack: list[tuple[str, str | None]] = []
        self.skip = 0   # script/style の中
        self.chars: dict[str, str] = {}  # 字 -> 最初に見つかった文脈
        self.inline_mincho: list[str] = []
        self.title_depth = 0
        self.other = other_font_classes or set()

    def mode(self) -> str | None:
        for _, st in reversed(self.stack):
            if st:
                return st
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if MINCHO_RE.search(a.get('style') or ''):
            self.inline_mincho.append(f'<{tag} style="{a.get("style")}">')
        if tag in VOID:
            return
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'title':
            self.title_depth += 1
        classes = set((a.get('class') or '').split())
        if MINCHO_CLASS in classes:
            state = 'm'
        elif classes & self.other:
            state = 'g'   # クラスの指定はタグの指定（h1 等）より強い
        elif tag in MINCHO_TAGS:
            state = 'm'
        else:
            state = None
        self.stack.append((tag, state))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if MINCHO_RE.search(a.get('style') or ''):
            self.inline_mincho.append(f'<{tag} style="{a.get("style")}">')

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.title_depth = max(0, self.title_depth - 1)
        # 閉じ忘れに強くするため、同じ名前の要素まで巻き戻す
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        # SVG の <title>（読み上げ用）は h3 等の中に無いので対象外。明朝の要素の中だけ集める
        if self.skip or self.title_depth or self.mode() != 'm':
            return
        for ch in data:
            if ch.isspace():
                continue
            self.chars.setdefault(ch, data.strip()[:24])


def css_of(html: str) -> str:
    css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', html, re.S | re.I))
    return re.sub(r'/\*.*?\*/', '', css, flags=re.S)


def mincho_selectors(css: str) -> list[str]:
    """明朝を指定している規則のセレクタを全部返す（@font-face と変数の定義は除く）。"""
    found = []
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        sel = sel.strip()
        if sel.startswith('@'):
            continue
        for decl in body.split(';'):
            if ':' not in decl:
                continue
            prop, val = decl.split(':', 1)
            prop = prop.strip().lower()
            if prop.startswith('--'):
                continue
            if prop in ('font-family', 'font') and MINCHO_RE.search(val):
                found.extend(s.strip() for s in sel.split(','))
    return found


def other_font_classes(css: str) -> set[str]:
    """明朝以外の書体（ゴシック・数字用）を指定している、結合子の無い単独のクラスセレクタのクラス名。

    `.x .y{font-family:…}` のように祖先の条件つきの規則は、条件の外では明朝のままなので数えない
    （数えすぎは woff2 が少し太るだけで害が無いが、数え漏れは字の抜けになる）。
    """
    out: set[str] = set()
    for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
        sel = sel.strip()
        if sel.startswith('@'):
            continue
        fam = None
        for decl in body.split(';'):
            if ':' not in decl:
                continue
            prop, val = decl.split(':', 1)
            prop = prop.strip().lower()
            if prop in ('font-family', 'font'):
                fam = val
        if fam is None or MINCHO_RE.search(fam):
            continue
        for s in sel.split(','):
            s = re.sub(r'::?[\w-]+(\([^)]*\))?', '', s.strip())
            if re.fullmatch(r'[a-z0-9]*(\.[\w-]+)+', s, re.I):
                out.update(re.findall(r'\.([\w-]+)', s))
    out.discard(MINCHO_CLASS)
    return out


def subject_ok(selector: str) -> bool:
    """セレクタの対象（最後の複合セレクタ）が h1/h2/h3/.mc なら、門が字を集められる。"""
    last = re.split(r'\s*[>+~]\s*|\s+', selector.strip())[-1]
    last = re.sub(r'::?[\w-]+(\([^)]*\))?', '', last)  # 疑似クラス・疑似要素を外す
    m = re.match(r'^([a-z0-9]+)?((?:[.#\[][^.#\[]+)*)$', last, re.I)
    if not m:
        return False
    tag, rest = (m.group(1) or '').lower(), m.group(2) or ''
    classes = re.findall(r'\.([\w-]+)', rest)
    return tag in MINCHO_TAGS or MINCHO_CLASS in classes


def font_urls(css: str) -> dict[str, str]:
    out = {}
    for body in re.findall(r'@font-face\s*\{([^}]*)\}', css):
        fam = re.search(r'font-family\s*:\s*["\']?([^;"\']+)', body)
        url = re.search(r'url\(\s*["\']?([^)"\']+)', body)
        if fam and url:
            out[fam.group(1).strip()] = url.group(1).strip()
    return out


def cmap_of(path: str) -> set[int]:
    from fontTools.ttLib import TTFont
    return set(TTFont(path).getBestCmap().keys())


def build(page: str, src: str, barlow_src: str | None, chars: str) -> None:
    from fontTools import subset
    page_dir = os.path.dirname(page)
    fonts_dir = os.path.join(page_dir, 'img', 'fonts')
    os.makedirs(fonts_dir, exist_ok=True)

    def run(src_path: str, out_path: str, text: str | None, unicodes: list[int] | None, features: list[str]):
        opts = subset.Options()
        opts.flavor = 'woff2'
        opts.layout_features = features
        opts.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]  # 著作権・ライセンス（OFL）の欄を残す
        opts.hinting = False
        opts.desubroutinize = True
        font = subset.load_font(src_path, opts)
        sub = subset.Subsetter(opts)
        sub.populate(text=text or '', unicodes=unicodes or [])
        sub.subset(font)
        subset.save_font(font, out_path, opts)
        print(f'  書き出し {os.path.relpath(out_path, ROOT)}  {os.path.getsize(out_path):,} バイト')

    text = ''.join(sorted(set(chars) | set(ALWAYS)))
    with open(os.path.join(fonts_dir, 'mincho-chars.txt'), 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    print(f'明朝の字: {len(text)} 字')
    run(src, os.path.join(fonts_dir, 'mincho-800.woff2'), text, None, ['palt', 'kern'])
    if barlow_src:
        run(barlow_src, os.path.join(fonts_dir, 'barlow-cond-600.woff2'), None, list(range(0x20, 0x7F)), ['tnum', 'kern'])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default=DEFAULT_PAGE)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--src', help='ShipporiMinchoB1-ExtraBold.ttf（build のとき）')
    ap.add_argument('--barlow-src', help='BarlowCondensed-SemiBold.ttf（build のとき・任意）')
    a = ap.parse_args()

    page = os.path.abspath(a.page)
    html = open(page, encoding='utf-8').read()
    css = css_of(html)
    others = other_font_classes(css)
    col = Collector(others)
    col.feed(html)
    col.close()
    chars = ''.join(col.chars)

    if a.build:
        if not a.src:
            print('--build には --src（元の TTF）が要ります', file=sys.stderr)
            return 2
        build(page, a.src, a.barlow_src, chars)

    problems: list[str] = []

    # 1. 明朝を付けているセレクタが、門の集められる対象だけか
    sels = mincho_selectors(css)
    if not sels:
        problems.append('明朝を指定している規則が見つからない（門の前提が崩れている）')
    for s in sels:
        if not subject_ok(s):
            problems.append(f'明朝のセレクタ「{s}」は h1/h2/h3/.mc 以外を対象にしている。門が字を集められないので、要素に class="mc" を付けるか、セレクタを直す')

    # 2. style 属性で明朝
    for t in col.inline_mincho:
        problems.append(f'style 属性で明朝を指定している: {t[:80]}')

    # 5. woff2 の実在
    urls = font_urls(css)
    page_dir = os.path.dirname(page)
    mincho_url = next((u for f, u in urls.items() if 'Shippori' in f), None)
    barlow_url = next((u for f, u in urls.items() if 'Barlow' in f), None)
    paths = {}
    for name, url in (('明朝', mincho_url), ('Barlow', barlow_url)):
        if not url:
            problems.append(f'@font-face に {name} の指定が無い')
            continue
        p = os.path.normpath(os.path.join(page_dir, url))
        if not os.path.isfile(p):
            problems.append(f'{name} の woff2 が無い: {os.path.relpath(p, ROOT)}')
            continue
        paths[name] = p

    # 3. 字がそろっているか
    if '明朝' in paths:
        cm = cmap_of(paths['明朝'])
        missing = [(ch, ctx) for ch, ctx in col.chars.items() if ord(ch) not in cm]
        size = os.path.getsize(paths['明朝'])
        print(f'明朝: ページで明朝を使う字 {len(col.chars)} 字 / woff2 の字 {len(cm)} 字 / {size:,} バイト')
        for ch, ctx in missing:
            problems.append(f'明朝の woff2 に「{ch}」(U+{ord(ch):04X}) が無い … {ctx}')

    # 4. Barlow の ASCII
    if 'Barlow' in paths:
        cm = cmap_of(paths['Barlow'])
        lack = [chr(c) for c in range(0x20, 0x7F) if c not in cm]
        print(f'Barlow: ASCII 95 字のうち {95 - len(lack)} 字 / {os.path.getsize(paths["Barlow"]):,} バイト')
        if lack:
            problems.append(f'Barlow の woff2 に ASCII の字が無い: {"".join(lack)!r}')

    print(f'明朝のセレクタ: {", ".join(sels) if sels else "なし"}')
    print(f'明朝で数えないクラス（ほかの書体を指定）: {", ".join(sorted(others)) if others else "なし"}')
    if problems:
        print(f'\nNG {len(problems)} 件')
        for p in problems:
            print('  - ' + p)
        print('直し方: python scripts/check-font-subset.py --build --src <ShipporiMinchoB1-ExtraBold.ttf>')
        return 1
    print('OK 明朝で出す字は全部 woff2 に入っている')
    return 0


if __name__ == '__main__':
    sys.exit(main())
