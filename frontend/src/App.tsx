import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState("Connecting...");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Connection failed"));
  }, []);

  return <h1>API status: {status}</h1>;
}

export default App;