import React, { useState } from "react";

import styles from './styles.module.scss'

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
        <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.input_container}>
                <label className={styles.label}>Arquivo 1:</label>

                <input
                    type="file"
                    id="file1"
                    accept="application/pdf"
                    className={styles.hiddenInput}
                    onChange={(e) => setFile1(e.target.files[0])}
                />

                <label htmlFor="file1" className={styles.fileButton}>
                    Selecionar PDF
                </label>

                <span className={styles.fileName}>
                    {file1?.name || "Nenhum arquivo selecionado"}
                </span>
            </div>

            <div className={styles.input_container}>
                <label className={styles.label}>Arquivo 2:</label>

                <input
                    type="file"
                    id="file2"
                    accept="application/pdf"
                    className={styles.hiddenInput}
                    onChange={(e) => setFile2(e.target.files[0])}
                />

                <label htmlFor="file2" className={styles.fileButton}>
                    Selecionar PDF
                </label>

                <span className={styles.fileName}>
                    {file2?.name || "Nenhum arquivo selecionado"}
                </span>
            </div>

            <button
                type="submit"
                disabled={loading}
                className={styles.button}
            >
                {loading ? "Comparando..." : "Enviar"}
            </button>
        </form>
    )
}