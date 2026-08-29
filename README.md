# Immune Cell Response Dashboard

An interactive application for exploring immune cell populations and treatment response in clinical trial samples. A Python pipeline loads the source data into SQLite and calculates relative cell frequencies. A FastAPI service supplies the results to a React and TypeScript dashboard.

## Project structure

- `load_data.py` creates the SQLite database and loads `cell-count.csv`.
- `analysis.py` calculates population frequencies and performs the responder analysis.
- `api.py` exposes analysis results through FastAPI.
- `frontend/` contains the React, TypeScript, Plotly, and Vite application.

## Database schema

The schema separates projects, subjects, samples, cell populations, and cell counts. Each subject belongs to one project in the supplied dataset, and each sample belongs to one subject. The `cell_counts` table joins samples to cell populations and stores one count for each pair.

This normalized design avoids adding a database column whenever a new population is measured. Integer keys keep joins compact as the number of projects and samples grows. If the domain expands, condition, treatment, and sample type can move into reference tables. A subject-to-project enrollment table can represent subjects who participate in more than one project.

## Analysis

The population-frequency table contains one row for each sample and population. `total_count` is the sum of the five population counts within a sample, and `percentage` is the population count divided by that total.

The responder analysis includes melanoma PBMC samples from subjects treated with miraclib. Each subject has repeated measurements, so the analysis averages relative frequencies within each subject before comparing responders with non-responders. It applies a two-sided Mann-Whitney U test to each population and uses a Bonferroni correction across the five comparisons. No population reaches the 0.05 significance threshold after correction.

## Development setup

The project requires Python and Node.js.

Install the Python dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

Create and populate the SQLite database:

```bash
python load_data.py
```

Start the FastAPI development server:

```bash
python -m uvicorn api:app --reload --port 8000
```

The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

In a second terminal, install the frontend dependencies and start Vite:

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at [http://localhost:5173](http://localhost:5173).
