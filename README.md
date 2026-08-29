# Immune Cell Response Dashboard

An interactive application for exploring immune cell populations and treatment response in clinical trial samples.

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
