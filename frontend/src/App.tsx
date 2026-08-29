import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import Plot from "react-plotly.js";
import type { Data } from "plotly.js";

type PopulationFrequency = {
  sample: string;
  total_count: number;
  population: string;
  count: number;
  percentage: number;
};

type FrequencyPage = {
  records: PopulationFrequency[];
  total: number;
  offset: number;
  limit: number;
};

type Frequency = {
  project: string;
  subject: string;
  response: "yes" | "no";
  population: string;
  mean_percentage: number;
};

type Statistic = {
  population: string;
  responders_n: number;
  nonresponders_n: number;
  responders_median: number;
  nonresponders_median: number;
  median_difference: number;
  mann_whitney_u: number;
  p_value: number;
  adjusted_p_value: number;
  significant: boolean;
};

type Comparison = {
  frequencies: Frequency[];
  statistics: Statistic[];
};

type BaselineSample = {
  project: string;
  subject: string;
  sample: string;
  response: "yes" | "no";
  sex: "M" | "F";
};

type BreakdownCount = {
  breakdown: "project" | "response" | "sex";
  group: string;
  count: number;
};

type BaselineAnalysis = {
  samples: BaselineSample[];
  counts: BreakdownCount[];
  form_calculation: {
    average_b_cells: number;
    sample_count: number;
  };
};

const populations = [
  "b_cell",
  "cd4_t_cell",
  "cd8_t_cell",
  "monocyte",
  "nk_cell",
];
const pageSize = 100;

function App() {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [baseline, setBaseline] = useState<BaselineAnalysis | null>(null);
  const [frequencyPage, setFrequencyPage] = useState<FrequencyPage | null>(null);
  const [page, setPage] = useState(0);
  const [sampleInput, setSampleInput] = useState("");
  const [sampleFilter, setSampleFilter] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const parameters = new URLSearchParams({
      offset: String(page * pageSize),
      limit: String(pageSize),
      sample: sampleFilter,
    });

    fetch(`/api/population-frequencies?${parameters}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load population frequencies");
        }

        return response.json();
      })
      .then(setFrequencyPage)
      .catch((requestError: Error) => setError(requestError.message));
  }, [page, sampleFilter]);

  useEffect(() => {
    fetch("/api/responder-comparison")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load responder analysis");
        }

        return response.json();
      })
      .then(setComparison)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  useEffect(() => {
    fetch("/api/baseline-analysis")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Unable to load baseline analysis");
        }

        return response.json();
      })
      .then(setBaseline)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  if (error) {
    return <p>{error}</p>;
  }

  if (!comparison || !baseline || !frequencyPage) {
    return <p>Loading analysis...</p>;
  }

  const submitSampleFilter = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(0);
    setSampleFilter(sampleInput.trim());
  };

  const clearSampleFilter = () => {
    setSampleInput("");
    setSampleFilter("");
    setPage(0);
  };

  const traces: Data[] = populations.flatMap((population) =>
    (["yes", "no"] as const).map((response) => {
      const records = comparison.frequencies.filter(
        (record) =>
          record.population === population &&
          record.response === response,
      );

      return {
        type: "box",
        name: response === "yes" ? "Responder" : "Non-responder",
        legendgroup: response,
        showlegend: population === populations[0],
        x: records.map(() => population),
        y: records.map((record) => record.mean_percentage),
        marker: {
          color: response === "yes" ? "#2563eb" : "#e8793e",
        },
        boxpoints: "outliers",
      };
    }),
  );

  const significantPopulations = comparison.statistics
    .filter((statistic) => statistic.significant)
    .map((statistic) => statistic.population);

  return (
    <main>
      <h1>Immune Cell Response Dashboard</h1>

      <p>
        Explore immune-cell composition and treatment response across clinical
        trial samples.
      </p>

      <section className="overview-section">
        <h2>Population frequency overview</h2>
        <p className="section-description">
          Each row reports one cell population as a percentage of its sample's
          total cell count.
        </p>

        <form className="table-controls" onSubmit={submitSampleFilter}>
          <label htmlFor="sample-search">Filter by sample</label>
          <div>
            <input
              id="sample-search"
              type="search"
              value={sampleInput}
              placeholder="e.g. sample00000"
              onChange={(event) => setSampleInput(event.target.value)}
            />
            <button type="submit">Apply</button>
            <button
              className="secondary-button"
              type="button"
              disabled={!sampleInput && !sampleFilter}
              onClick={clearSampleFilter}
            >
              Clear
            </button>
          </div>
        </form>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Sample</th>
                <th>Total count</th>
                <th>Population</th>
                <th>Count</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {frequencyPage.records.map((record) => (
                <tr key={`${record.sample}-${record.population}`}>
                  <td>{record.sample}</td>
                  <td>{record.total_count.toLocaleString()}</td>
                  <td>{record.population}</td>
                  <td>{record.count.toLocaleString()}</td>
                  <td>{record.percentage.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((current) => current - 1)}
          >
            Previous
          </button>
          <span>
            {frequencyPage.total === 0
              ? "No matching rows"
              : `${frequencyPage.offset + 1}-${Math.min(
                  frequencyPage.offset + frequencyPage.records.length,
                  frequencyPage.total,
                )} of ${frequencyPage.total.toLocaleString()}`}
          </span>
          <button
            type="button"
            disabled={
              frequencyPage.offset + frequencyPage.records.length >=
              frequencyPage.total
            }
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </div>
      </section>

      <section className="responder-section">
        <h2>Responder comparison</h2>
        <p className="section-description">
          Relative frequencies for melanoma PBMC samples from patients treated
          with miraclib.
        </p>

        <Plot
          data={traces}
          layout={{
            autosize: true,
            boxmode: "group",
            title: {
              text: "Responders vs. non-responders",
            },
            xaxis: {
              title: { text: "Cell population" },
            },
            yaxis: {
              title: { text: "Mean relative frequency (%)" },
            },
          }}
          config={{
            displaylogo: false,
            responsive: true,
          }}
          useResizeHandler
          style={{ width: "100%", height: "550px" }}
        />

        <section className="finding">
          <h2>Conclusion</h2>

          <p>
            {significantPopulations.length === 0
              ? "No cell population showed a statistically significant difference after correction for multiple comparisons."
              : `${significantPopulations.join(", ")} showed a statistically significant difference.`}
          </p>

          <p className="method">
            Two-sided Mann–Whitney U tests compared subject-level mean
            frequencies across PBMC timepoints. P-values were adjusted for five
            comparisons using the Bonferroni method.
          </p>
        </section>

        <h2>Statistical results</h2>

        <table>
          <thead>
            <tr>
              <th>Population</th>
              <th>Responder median</th>
              <th>Non-responder median</th>
              <th>Adjusted p-value</th>
              <th>Significant</th>
            </tr>
          </thead>
          <tbody>
            {comparison.statistics.map((statistic) => (
              <tr key={statistic.population}>
                <td>{statistic.population}</td>
                <td>{statistic.responders_median.toFixed(2)}%</td>
                <td>{statistic.nonresponders_median.toFixed(2)}%</td>
                <td>{statistic.adjusted_p_value.toFixed(4)}</td>
                <td>{statistic.significant ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="baseline-section">
        <h2>Baseline subset analysis</h2>

        <p className="section-description">
          Melanoma PBMC samples collected at time 0 from patients treated
          with miraclib.
        </p>

        <div className="summary-grid">
          {(["project", "response", "sex"] as const).map((breakdown) => (
            <article className="summary-card" key={breakdown}>
              <h3>
                {breakdown === "project"
                  ? "Samples by project"
                  : `Subjects by ${breakdown}`}
              </h3>

              {baseline.counts
                .filter((item) => item.breakdown === breakdown)
                .map((item) => (
                  <div className="count-row" key={item.group}>
                    <span>{item.group}</span>
                    <strong>{item.count}</strong>
                  </div>
                ))}
            </article>
          ))}
        </div>

        <article className="metric-card">
          <div>
            <h3>Average B-cell count</h3>
            <p>
              Male melanoma responders at time 0 across all sample and
              treatment types.
            </p>
          </div>

          <div>
            <strong>
              {baseline.form_calculation.average_b_cells.toFixed(2)}
            </strong>
            <span>
              {baseline.form_calculation.sample_count} samples
            </span>
          </div>
        </article>

        <h3 className="sample-heading">
          Matching baseline samples
          <span>{baseline.samples.length}</span>
        </h3>

        <div className="sample-table">
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Subject</th>
                <th>Sample</th>
                <th>Response</th>
                <th>Sex</th>
              </tr>
            </thead>
            <tbody>
              {baseline.samples.map((sample) => (
                <tr key={sample.sample}>
                  <td>{sample.project}</td>
                  <td>{sample.subject}</td>
                  <td>{sample.sample}</td>
                  <td>{sample.response}</td>
                  <td>{sample.sex}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

export default App;
