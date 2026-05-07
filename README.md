# Andy Miah — CV Generator

A command-line tool that generates a tailored PDF CV from a single structured portfolio file, selecting and ranking content based on a focus area.

## How it works

All CV content lives in `portfolio.json`. Every item (role, grant, publication, keynote, partnership...) is tagged with one or more focus keywords. When you run the generator with a focus area, it scores every item by tag overlap and builds a PDF that foregrounds the most relevant content — reordering sections, filtering bullet points, selecting the right profile paragraph, and choosing the most relevant metrics.

## Setup

```bash
git clone https://github.com/andymiah/cv-generator.git
cd cv-generator
pip install -r requirements.txt
```

Python 3.9+ required. No API keys or external services needed.

## Usage

```bash
# Generate an esports-focused CV
python generate_cv.py --focus esports

# Generate a creative-manchester leadership CV
python generate_cv.py --focus creative-manchester

# Generate a science communication CV to a custom path
python generate_cv.py --focus science-communication --out ~/Desktop/miah_scicomm_cv.pdf

# See all available focus areas
python generate_cv.py --list-focuses
```

Output lands in `output/cv_<focus>.pdf` by default.

## Available focus areas

| Focus | Content emphasised |
|---|---|
| `esports` | BEF/GEF governance, esports research, gaming keynotes, Innovate UK gametech strand |
| `creative-manchester` | Platform leadership, GMCA/Factory International, CreaTech, UoM collaborations |
| `science-communication` | SciComm Space, SNSF, festival work, FameLab, media presence, Josh Award |
| `ai-ethics` | AI Foundry, DCMS, PROBABLE Futures, metaverse ethics, AI keynotes |
| `digital-health` | Wellcome Trust, wearables research, NHS/gaming papers |
| `olympic-studies` | IOC, Sport 2.0, Culture @ the Olympics, mega-events research |
| `bioethics` | Genetically Modified Athletes, gene doping, enhancement philosophy |
| `platform-leadership` | Leadership roles, interdisciplinary platforms, REF, civic partnerships |

## Updating your portfolio

All content is in `portfolio.json`. To add a new item, add it to the relevant array with appropriate `tags`. To add a new focus area, add an entry to the `focus_areas` object.

### Tag conventions

Tags are lowercase, hyphenated strings. A good item has 2–4 tags. The more specific the better — `esports` is more useful than `sport`.

### Adding a profile variant

Add a key matching your new focus area name to `portfolio.profile.variants`:

```json
"variants": {
  "my-new-focus": "Professor Andy Miah is..."
}
```

## Project structure

```
cv-generator/
├── README.md
├── portfolio.json        ← all CV content and tags
├── generate_cv.py        ← CLI entry point
├── requirements.txt
├── generator/
│   ├── __init__.py
│   ├── scorer.py         ← tag-based relevance scoring
│   └── builder.py        ← PDF assembly via ReportLab
└── output/               ← generated CVs land here (gitignored)
```

## Extending

**Add a new output format:** Implement a new builder (e.g. `builder_docx.py`) with the same signature as `build_cv()` in `builder.py`, then add a `--format` flag to `generate_cv.py`.

**Add AI-assisted scoring:** Replace the `score_item()` function in `scorer.py` with a call to an embeddings API to score semantic similarity rather than exact tag matches.

**Add a web UI:** The generator is stateless and fast — a minimal Streamlit wrapper around `generate_cv.py` would work well.

## Licence

MIT — use and adapt freely.
