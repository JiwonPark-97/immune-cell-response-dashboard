import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import type { Data } from "plotly.js";

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

const populations = [
  "b_cell",
  "cd4_t_cell",
  "cd8_t_cell",
  "monocyte",
  "nk_cell",
];

function App() {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [error, setError] = useState("");

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

  if (error) {
    return <p>{error}</p>;
  }

  if (!comparison) {
    return <p>Loading analysis...</p>;
  }

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
        Relative frequencies for melanoma PBMC samples from patients
        treated with miraclib.
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
    </main>
  );
}

export default App;