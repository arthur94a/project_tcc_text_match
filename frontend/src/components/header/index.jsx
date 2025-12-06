import React from "react";
import styles from './styles.module.scss'

export function Header() {
    return (
        <header className={styles.header}>
            <h1>Text Match</h1>
            <p>Comparador de textos ".pdf" com python</p>
        </header>
    )
}