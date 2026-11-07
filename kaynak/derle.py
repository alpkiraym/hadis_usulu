#!/usr/bin/env python3
"""Hadis Usulü · kaynak dosyalarından index.html üretir.

Kullanım:  python3 kaynak/derle.py
Okur:      kaynak/01.txt … 17.txt (üniteler), kaynak/sorular.txt, kaynak/sinav.txt, kaynak/sablon.html,
           kaynak/bildir.html (Giray Akademi ortak hata bildirimi)
Yazar:     index.html (depo kökü)

Ünite dosyası biçimi:
  # Ünite başlığı          > giriş cümlesi
  ## Bölüm başlığı         ### Alt başlık
  - madde                  1. numaralı madde
  : Terim = tanım          ! not kutusu
  **kalın**  «Arapça»
"""
import json, re, sys
from pathlib import Path

K = Path(__file__).resolve().parent
KOK = K.parent


def hata(msg):
    sys.exit('HATA: ' + msg)


def unite_oku(yol):
    u = {'t': '', 'intro': '', 's': []}
    sec = None
    for no, satir in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        s = satir.rstrip()
        if not s.strip():
            continue
        if s.startswith('## '):
            sec = {'h': s[3:].strip(), 'b': []}
            u['s'].append(sec)
            continue
        if s.startswith('# '):
            u['t'] = s[2:].strip()
            continue
        if s.startswith('> '):
            u['intro'] = s[2:].strip()
            continue
        if sec is None:
            hata(f'{yol.name}:{no} bölüm başlığından önce içerik')
        if s.startswith('### '):
            sec['b'].append({'k': 'h', 'x': s[4:].strip()})
        elif s.startswith('- '):
            sec['b'].append({'k': 'li', 'x': s[2:].strip()})
        elif s.startswith('! '):
            sec['b'].append({'k': 'not', 'x': s[2:].strip()})
        elif s.startswith(': '):
            if ' = ' not in s:
                hata(f'{yol.name}:{no} tanım satırında " = " yok')
            t, d = s[2:].split(' = ', 1)
            sec['b'].append({'k': 'd', 't': t.strip(), 'x': d.strip()})
        elif re.match(r'^\d+\.\s', s):
            n, x = s.split('.', 1)
            sec['b'].append({'k': 'n', 'n': int(n), 'x': x.strip()})
        else:
            hata(f'{yol.name}:{no} tanınmayan satır: {s[:40]}')
    if not u['t'] or not u['s']:
        hata(f'{yol.name} başlık veya bölüm eksik')
    return u


def sorular_oku(yol, adet):
    out, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('? '):
            if q:
                out.append(q)
            u, metin = s[2:].split('|', 1)
            q = {'u': int(u) - 1, 'q': metin.strip(), 'a': [], 'x': ''}
        elif s.startswith('+ '):
            q['a'].insert(0, s[2:].strip())
        elif s.startswith('- '):
            q['a'].append(s[2:].strip())
        elif s.startswith('= '):
            q['x'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    if q:
        out.append(q)
    for i, q in enumerate(out):
        if len(q['a']) != 4 or len(set(q['a'])) != 4:
            hata(f'soru {i + 1}: 4 farklı şık olmalı ({q["q"][:40]})')
        if not (0 <= q['u'] < adet):
            hata(f'soru {i + 1}: ünite numarası geçersiz')
        if not q['x']:
            hata(f'soru {i + 1}: açıklama yok')
    return out


def sinav_oku(yol, uniteler):
    out, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('? '):
            if q:
                out.append(q)
            q = {'q': s[2:].strip(), 'r': [], 'x': ''}
        elif s.startswith('> '):
            u, h = s[2:].split(':', 1)
            ui = int(u) - 1
            basliklar = [x['h'] for x in uniteler[ui]['s']]
            if h.strip() not in basliklar:
                hata(f'{yol.name}:{no} "{h.strip()}" bölümü {u}. ünitede yok')
            q['r'].append([ui, basliklar.index(h.strip())])
        elif s.startswith('= '):
            q['x'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    if q:
        out.append(q)
    return out


def main():
    dosyalar = sorted(K.glob('[0-9][0-9].txt'))
    uniteler = [unite_oku(p) for p in dosyalar]
    sorular = sorular_oku(K / 'sorular.txt', len(uniteler))
    sinav = sinav_oku(K / 'sinav.txt', uniteler)
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    veri = f'const UNITELER = {j(uniteler)};\nconst SORULAR = {j(sorular)};\nconst SINAV = {j(sinav)};'
    sablon = (K / 'sablon.html').read_text(encoding='utf-8')
    if '/*VERI*/' not in sablon:
        hata('sablon.html içinde /*VERI*/ yok')
    if '<!--BILDIR-->' not in sablon:
        hata('sablon.html içinde <!--BILDIR--> yok')
    sablon = sablon.replace('<!--BILDIR-->', (K / 'bildir.html').read_text(encoding='utf-8'))
    sablon = sablon.replace('<!--ALTCUBUK-->', (K / 'altcubuk.html').read_text(encoding='utf-8'))  # ortak alt çubuk (Giray Akademi)
    (KOK / 'index.html').write_text(sablon.replace('/*VERI*/', veri), encoding='utf-8')
    tanim = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'd')
    print(f'{len(uniteler)} ünite, {sum(len(u["s"]) for u in uniteler)} bölüm, {tanim} tanım, '
          f'{len(sorular)} el ile soru, {len(sinav)} sınav sorusu → index.html')


if __name__ == '__main__':
    main()
