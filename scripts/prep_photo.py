"""Prepara a foto para virar ASCII: contraste local + isolamento do rosto.

O artigo original usa rembg (remover fundo) + OpenCV (CLAHE). Nenhum dos dois
tem wheel para Python 3.14, entao os dois passos estao reimplementados aqui em
numpy puro -- a unica dependencia de imagem e' o Pillow.

  python scripts/prep_photo.py assets/source-photo.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def clahe(img: np.ndarray, tiles: int = 8, clip: float = 2.6) -> np.ndarray:
    """Equalizacao adaptativa com limite de contraste, interpolada entre tiles.

    E' o passo que tira o rosto do 'cinza chapado' e cria luz e sombra de verdade.
    """
    h, w = img.shape
    th, tw = int(np.ceil(h / tiles)), int(np.ceil(w / tiles))
    luts = np.zeros((tiles, tiles, 256), dtype=np.float64)

    for ty in range(tiles):
        for tx in range(tiles):
            block = img[ty * th : (ty + 1) * th, tx * tw : (tx + 1) * tw]
            if block.size == 0:
                luts[ty, tx] = np.arange(256)
                continue
            hist = np.bincount(block.ravel(), minlength=256).astype(np.float64)
            limit = max(1.0, clip * block.size / 256.0)
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit) + excess / 256.0
            cdf = np.cumsum(hist)
            luts[ty, tx] = (cdf - cdf[0]) / max(cdf[-1] - cdf[0], 1e-9) * 255.0

    # posicao de cada pixel na grade de centros de tile
    yy = np.clip((np.arange(h) - th / 2) / th, 0, tiles - 1)
    xx = np.clip((np.arange(w) - tw / 2) / tw, 0, tiles - 1)
    y0, x0 = np.floor(yy).astype(int), np.floor(xx).astype(int)
    y1, x1 = np.minimum(y0 + 1, tiles - 1), np.minimum(x0 + 1, tiles - 1)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]

    def take(ys, xs):
        return luts[ys[:, None], xs[None, :], img]

    top = take(y0, x0) * (1 - fx) + take(y0, x1) * fx
    bot = take(y1, x0) * (1 - fx) + take(y1, x1) * fx
    return np.clip(top * (1 - fy) + bot * fy, 0, 255)


def unsharp(img: np.ndarray, radius: int = 2, amount: float = 0.55) -> np.ndarray:
    blur = np.asarray(
        Image.fromarray(img.astype(np.uint8)).filter(
            __import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(radius)
        ),
        dtype=np.float64,
    )
    return np.clip(img + amount * (img - blur), 0, 255)


def elliptical_mask(h: int, w: int, cx: float, cy: float, rx: float, ry: float, feather: float) -> np.ndarray:
    """1 dentro do rosto, 0 fora, com borda suave -- substitui o recorte do rembg."""
    y = (np.arange(h)[:, None] / h - cy) / ry
    x = (np.arange(w)[None, :] / w - cx) / rx
    dist = np.sqrt(x**2 + y**2)
    return np.clip((1.0 + feather - dist) / max(feather, 1e-6), 0, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", default=str(ROOT / "assets" / "source-photo.png"))
    ap.add_argument("--cx", type=float, default=0.475, help="centro X do rosto (0-1)")
    ap.add_argument("--cy", type=float, default=0.435, help="centro Y do rosto (0-1)")
    ap.add_argument("--rx", type=float, default=0.335, help="raio X da mascara")
    ap.add_argument("--ry", type=float, default=0.475, help="raio Y da mascara")
    ap.add_argument("--feather", type=float, default=0.13)
    ap.add_argument("--clip", type=float, default=2.9)
    ap.add_argument("--tiles", type=int, default=8, help="menos tiles = formas maiores, menos ruido")
    ap.add_argument("--unsharp", type=float, default=0.55)
    ap.add_argument("--gamma", type=float, default=2.4)
    args = ap.parse_args()

    im = Image.open(args.source).convert("L")
    arr = np.asarray(im, dtype=np.uint8)

    out = clahe(arr, tiles=args.tiles, clip=args.clip)
    if args.unsharp > 0:
        out = unsharp(out, amount=args.unsharp)

    # normaliza usando so' o miolo do rosto, para a rampa inteira ser usada
    mask = elliptical_mask(*arr.shape, args.cx, args.cy, args.rx, args.ry, args.feather)
    inside = out[mask > 0.6]
    lo, hi = np.percentile(inside, 1.5), np.percentile(inside, 98.5)
    out = np.clip((out - lo) / max(hi - lo, 1e-6), 0, 1)
    if args.gamma != 1.0:
        out = out ** args.gamma

    # composita sobre PRETO: no terminal escuro, caractere denso = mais luz na tela,
    # entao a rampa mapeia claro->denso e o fundo precisa cair no 0 = espaco.
    out = out * mask

    dst = ROOT / "assets" / "source-prepped.png"
    Image.fromarray((out * 255).astype(np.uint8)).save(dst)
    print(f"{dst.relative_to(ROOT)} pronto ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
