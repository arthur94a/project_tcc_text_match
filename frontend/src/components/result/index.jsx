import React from "react";

import styles from './styles.module.scss'

export function Result({index, doc1, doc2, similarityScore}) {
    return (
        <article className={styles.card}>
            <h2 className={styles.title}>Resultado {index + 1}</h2>

            <section className={styles.container}>
                <div className={styles.card_content}>
                    <p className={styles.label}>Fragmento de texto 1</p>
                    <span>{doc1}</span>
                </div>

                <div className={styles.card_content}>
                    <p className={styles.label}>Fragmento de texto 2</p>
                    <span>{doc2}</span>
                </div>

                <div className={styles.card_score}>
                    <p className={styles.label}>Pontuação de similaridade:</p>
                    <span>{similarityScore}</span>
                </div>
            </section>
        </article>
    )
}