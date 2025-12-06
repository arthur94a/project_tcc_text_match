import React, { useState } from "react";

export function Form({ setResult }) {
    const [file1, setFile1] = useState(null);
    const [file2, setFile2] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!file1 || !file2) {
            alert("Selecione os dois arquivos PDF!");
            return;
        }
    
        const formData = new FormData();
        formData.append("file1", file1);
        formData.append("file2", file2);
    
        setLoading(true);
    
        try {
            const response = await fetch("http://localhost:8000/compare-pdfs-by-partition/", {
                method: "POST",
                body: formData,
            });
    
            const data = await response.json();
            setResult(data);
        } catch (err) {
            console.error(err);
            alert("Erro ao comparar PDFs");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <div>
                <label>Arquivo 1:</label>
                <input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => setFile1(e.target.files[0])}
                />
            </div>

            <div>
                <label>Arquivo 2:</label>
                <input
                    type="file"
                    accept="application/pdf"
                    onChange={(e) => setFile2(e.target.files[0])}
                />
            </div>

            <button
                type="submit"
                disabled={loading}
                style={{ marginTop: "1rem" }}
            >
                {loading ? "Comparando..." : "Enviar"}
            </button>
        </form>
    )
}