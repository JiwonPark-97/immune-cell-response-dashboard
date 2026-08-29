# Immune Cell Response Dashboard

An interactive application for exploring immune cell populations and treatment response in clinical trial samples. A Python pipeline loads the source data into SQLite and calculates relative cell frequencies. FastAPI supplies the results to a React and TypeScript dashboard.

## Run the project

The project requires Python 3.10 or later, Node.js, npm, and GNU Make. From the repository root:

```bash
make setup
make pipeline
make dashboard
```

`make setup` installs the Python and frontend dependencies. `make pipeline` recreates the database and writes every analysis output. `make dashboard` builds the React application and starts the dashboard at [http://localhost:8000](http://localhost:8000).

For development with hot reloading, start FastAPI from the repository root:

```bash
python -m uvicorn api:app --reload --port 8000
```

Then start Vite in a second terminal:

```bash
cd frontend
npm run dev
```

The development frontend is available at [http://localhost:5173](http://localhost:5173). FastAPI's interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Project structure

- `load_data.py` creates the SQLite database and loads `cell-count.csv`.
- `analysis.py` calculates Parts 2-4 and writes reproducible output files.
- `api.py` exposes analysis results through FastAPI.
- `frontend/` contains the React, TypeScript, Plotly, and Vite application.
- `tests/` contains regression tests for row counts and analytical results.
- `output/` contains the generated tables, plot, form calculation, and report.

## Database schema

The schema separates projects, subjects, samples, cell populations, and cell counts. Each subject belongs to one project in the supplied dataset, and each sample belongs to one subject. The `cell_counts` table joins samples to cell populations and stores one count for each pair.

This normalized design avoids adding a database column whenever a new population is measured. Integer keys keep joins compact as the number of projects and samples grows. If the domain expands, condition, treatment, and sample type can move into reference tables. A subject-to-project enrollment table can represent subjects who participate in more than one project.

## Analysis

The population-frequency table contains one row for each sample and population. `total_count` is the sum of the five population counts within a sample, and `percentage` is the population count divided by that total.

The responder analysis includes melanoma PBMC samples from subjects treated with miraclib. Each subject has repeated measurements, so the analysis averages relative frequencies within each subject before comparing responders with non-responders. It applies a two-sided Mann-Whitney U test to each population and uses a Bonferroni correction across the five comparisons. No population reaches the 0.05 significance threshold after correction.

The baseline subset contains 656 melanoma PBMC samples collected at time 0 from subjects treated with miraclib. The dashboard reports counts by project, response, and sex and displays the matching samples. The separate form calculation includes male melanoma responders at time 0 across all sample and treatment types. It uses 485 samples and produces an average B-cell count of `10206.15`.

## Generated outputs

- `output/cell_population_frequencies.csv`
- `output/part3_subject_mean_frequencies.csv`
- `output/part3_statistics.csv`
- `output/part4_baseline_samples.csv`
- `output/part4_counts.csv`
- `output/figures/responder_vs_nonresponder_boxplot.svg`
- `output/form_answer.json`
- `output/analysis_results.md`

## Tests

Run the regression suite after `make pipeline`:

```bash
make test
```

The tests verify the Part 2 table shape and percentages, Part 3 group sizes and conclusions, Part 4 counts, and the separate form calculation.

## Deployment

`render.yaml` defines a single Render web service. The build installs both dependency sets and compiles the React application. At startup, FastAPI recreates the SQLite database and serves the API and compiled dashboard from one process. Connect this repository to Render and select the included Blueprint to create a hosted instance.

## Manual commands

The Make targets wrap these commands:

```bash
python load_data.py
python analysis.py
npm --prefix frontend run build
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```
