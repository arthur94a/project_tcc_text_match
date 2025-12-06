import { useState, useEffect } from "react";
import { Header } from "./components/header";
import { Form } from "./components/form";

import './themes/global.scss'

export function App() {
  const [result, setResult] = useState(null);

  useEffect(() => {
    if(result) {
      console.log(result)
    }
  }, [result]);

  return (
    <div style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <Header />
      <Form setResult={setResult} />

      {/* {result && (
        <div style={{ marginTop: "2rem" }}>
          <h3>Resultado</h3>
          <p>Total linhas PDF 1: {result.total_lines_1}</p>
          <p>Total linhas PDF 2: {result.total_lines_2}</p>
          <p>Linhas idênticas: {result.identical_count}</p>
          <p>Linhas parecidas: {result.similar_count}</p>

          <details>
            <summary>Ver linhas idênticas</summary>
            <ul>
              {result.identical_lines.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </details>

          <details>
            <summary>Ver linhas parecidas</summary>
            <ul>
              {result.similar_lines.map((pair, i) => (
                <li key={i}>
                  <b>PDF1:</b> {pair.line_1} <br />
                  <b>PDF2:</b> {pair.line_2}
                </li>
              ))}
            </ul>
          </details>
        </div>
      )} */}
    </div>
  );
}
