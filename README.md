# Cold Years, Witch Years?

Scotland accused 3,840 people of witchcraft between 1563 and 1736, most of them in a few sudden panics. Where were they, who were they, and did the panics follow cold, hard years, as the Little Ice Age theory of witch-hunting suggests?

**Interactive version:** https://tristan-hotham.github.io/witch-hunts/
**Paper:** https://doi.org/10.5281/zenodo.23677167
**Blog post:** https://blog.tristanhotham.com/2026/10/27/witch-hunts/

This repository holds the interactive page, the cleaned data and the analysis code for the data study *Cold Years, Witch Years?* by Dr Tristan Hotham (Independent researcher, ORCID 0000-0003-4931-9349).

## Headline results

- The Survey of Scottish Witchcraft records 3,413 cases and 3,840 accused people (3,212 named). The five panics (1590 to 1591, 1597, 1628 to 1631, 1649 to 1650, 1661 to 1662) cover 11 of 174 years but hold 57% of dated accusations. The worst year was 1649, with 565.
- 85% of named accused whose sex is known were women; the share was the same in panic years (86%) and other years (85%).
- 54% of mapped accused lived within 50 km of Edinburgh; Haddington, Fife and Edinburgh counties hold 42% of those with a county. Each panic had its own heartland (1597: Aberdeenshire and Fife).
- No outcome survives for 2,687 named accused. Of the 525 with a known outcome, 248 (47%) were executed.
- Temperature: none of 30 year-by-year correlations with reconstructed European temperature (five seasons, lags 0 to 2, anomalies and year-to-year swings) reaches p < 0.05 under a circular-shift test (smallest p 0.13). Onset years averaged +0.04 °C (annual). The summers before the onsets averaged −0.28 °C (nominal p 0.033), but across the 30 event-study comparisons a result at least that striking turns up by chance 25% of the time. Decadal correlation −0.21 (p 0.15, phase-randomised).

## Files

- `index.html`: the interactive page (timeline, year-slider Leaflet map, panic cards, event study, correlation grid). `header.png`: social card.
- `data/cases.csv`: one row per Survey case: reference, named or not, number of people, year, name, sex, age, marital and social status, residence (settlement, parish, presbytery, county), Wikidata item and residence coordinates, trial count, most serious recorded outcome, execution method, torture and ordeal, and a link to the Survey case page.
- `data/annual.csv`: people accused per year 1563 to 1736 (by case year and by start year), women, men, executed, panic flag, and European seasonal and annual temperature (absolute, anomaly from the 1563 to 1736 mean, and year-to-year part after removing a 31-year running mean).
- `data/places.csv`, `data/parishes.csv`, `data/counties.csv`: accused by mapped place, by Survey parish and by county.
- `data/kde.geojson`: density contours (8 km Gaussian kernel, British National Grid) for all accused and for each panic.
- `data/europe_temperature.csv`: the seasonal temperature reconstruction 1500 to 2004, as read from the source file.
- `data/coast_ne10m.geojson`: simplified coastline for the small maps (Natural Earth, public domain).
- `work/site.json`, `work/kde.npz`: intermediate files for the page and figures (rebuilt by `02_analyse.py`).
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `code/`: run in order `01_clean.py`, `02_analyse.py`, `03_build_page.py`, `04_header.py`. Release outputs: `release/make_figures.py` (paper and blog figures), `release/paper/build_paper.py` (fills `paper_template.tex` and runs xelatex), `release/blog/build_post.py` (blog post and meta) and `reddit/collage.py` (collage). Figures and the collage need the fonts Fraunces, Source Serif 4 and IBM Plex Mono (set `FONT_DIR`).

## Method in brief and caveats

The Survey's text export has no header row, so its schema is inferred: I named each column I use by checking its contents. Cases are dated by case date, else start date. Coordinates come from Wikidata residences (3,133 of 3,212 named accused), which are place centres. The temperature series is a reconstruction for all of European land (25°W to 40°E, 35°N to 70°N), not Scotland. With only five panics and strongly autocorrelated series, every test uses a null that keeps autocorrelation (circular shifts, random onset sets, phase-randomised surrogates), and the event study reports a family-wise check. Outcomes are missing for most accused, so execution counts are floors.

## Sources and licences

- Goodare, J., Martin, L., Miller, J. and Yeoman, L. 2003. *The Survey of Scottish Witchcraft, 1563 to 1736*. University of Edinburgh. https://doi.org/10.7488/ds/100 (CC BY 4.0).
- Wikidata (CC0): items for accused witches with Survey identifiers and places of residence.
- Luterbacher, J. et al. 2006. European Seasonal Temperature Reconstructions. IGBP PAGES/World Data Center for Paleoclimatology Data Contribution Series 2006-060, NOAA/NCDC Paleoclimatology Program, Boulder CO. Original references: Luterbacher et al. 2004, *Science* 303, 1499 to 1503; Xoplaki et al. 2005, *Geophysical Research Letters* 32, L15713. Freely available from NOAA; please cite the contributors.
- Wikipedia, "Pendle witches" (CC BY-SA 4.0), for the Pendle comparison numbers.
- Natural Earth (public domain) for the coastline. Base map tiles on the page: Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community. Map library: Leaflet.

The derived data and the text are released under CC BY 4.0. Code is MIT (see `LICENSE`).

## Citation

Hotham, T. 2026. *Cold Years, Witch Years? Scotland's Witch Panics and the Little Ice Age, 1563 to 1736*. Zenodo. https://doi.org/10.5281/zenodo.23677167

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
