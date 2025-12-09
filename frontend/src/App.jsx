import { useState, useEffect } from "react";
import { Header } from "./components/header";
import { Form } from "./components/form";

import './themes/global.scss'
import { Result } from "./components/result";

export function App() {
  const [result, setResult] = useState(null);
  const [paragraphs, setParagraphs] = useState(null)

  useEffect(() => {
    if(result) {
      setParagraphs(result.plagiarized_paragraphs)
    }
  }, [result]);

  console.log(typeof paragraphs, paragraphs)

  return (
    <>
      <Header />
      <Form setResult={setResult} />

      {paragraphs && (
        paragraphs.map((item, index) => {

          return (
            <Result
              key={index}
              index={index}
              doc1={item.doc1.content}
              doc2={item.doc2.content}
              similarityScore={item.similarity_score}
            />
          )
        })
      )}
    </>
  );
}
