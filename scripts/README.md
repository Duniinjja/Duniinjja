# Como mexer nisto

O `README.md` da raiz é a vitrine do perfil. Ele só posiciona três SVGs que
estes scripts geram. O GitHub remove `<script>` e CSS externo de um README,
mas **renderiza SVG animado** via `<img>` — por isso toda a animação mora
dentro de cada arquivo `.svg`.

## O que atualiza sozinho

`.github/workflows/update-profile-art.yml` roda todo dia (~03:17 de Brasília):

```
fetch_contributions.py   ->  data/contributions.json
render_heatmap_svg.py    ->  contrib-heatmap.svg
make_info_card.py        ->  info-card.svg   (mostra os mesmos números)
```

Precisa só de `requests` — nada de token, nada de GraphQL. O calendário vem do
HTML público em `github.com/users/<login>/contributions`.

## Mudar o texto do card

Edite `data/profile.json` e faça commit. O workflow redesenha na próxima
execução, ou rode na mão:

```bash
python scripts/make_info_card.py
```

## Trocar a foto do retrato

O retrato **não** é regerado pelo workflow — só quando você quiser.

```bash
pip install -r scripts/requirements-portrait.txt
python scripts/prep_photo.py assets/sua-foto.jpg     # recorta, dá contraste
python scripts/make_ascii_svg.py --preview           # confere no terminal
python scripts/make_ascii_svg.py                     # grava o SVG
```

`prep_photo.py` aceita ajustes de enquadramento, porque a máscara elíptica é
posicionada na mão (o rosto de cada foto cai num lugar diferente):

| flag | o que faz |
|---|---|
| `--cx --cy` | centro do rosto, de 0 a 1 |
| `--rx --ry` | raios da máscara — aperte para cortar mais fundo |
| `--gamma` | acima de 1 escurece os meios-tons e abre mais espaço em branco |
| `--tiles --clip` | força do contraste local (CLAHE) |
| `--unsharp` | nitidez |

Duas armadilhas que custam tempo:

1. **A rampa segue o fundo.** Sobre fundo escuro, caractere denso = mais luz,
   então a rampa vai de claro para denso e o fundo tem de cair em `0` (preto).
   Inverter isso imprime o retrato em negativo.
2. **O estado natural do SVG é o estado final.** As animações usam
   `animation-fill-mode: backwards` (CSS) e `values`/`keyTimes` (SMIL), nunca
   um `opacity:0` fixo. Se a animação não rodar — leitor estático,
   `prefers-reduced-motion` — o desenho aparece inteiro em vez de sumir.
