from fastapi import FastAPI, File, UploadFile, HTTPException
from starlette.middleware.cors import CORSMiddleware
import pdfplumber
import io
import re
from thefuzz import process, fuzz

# --- CONFIGURAÇÕES GLOBAIS ---
app = FastAPI(title="PDF Plagiarism/Similarity Checker (Fuzzy Sentence-level)")

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIMILARITY_CUTOFF = 80
MIN_PARTITION_LENGTH = 64

# Regex para quebrar sentenças
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.?!])\s+')

# Limpeza de artefatos de PDF
CLEANUP_REGEX = re.compile(r'[\n\r\t]+|\s{2,}')

# Remove seção de referências (mais seguro para textos acadêmicos)
REFERENCE_REGEX = re.compile(
    r'^\s*(REFERÊNCIAS|Referências|REFERENCES).*',
    re.DOTALL | re.MULTILINE
)

# --- EXTRAÇÃO DE TEXTO COM SUPORTE A 2 COLUNAS ---
def extract_pdf_text(pdf_bytes: bytes) -> str:
    text = ""

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )
            if page_text:
                text += page_text + " "
            else:
                print(f"Atenção: página {i + 1} sem texto extraível")

    return text


# --- PRÉ-PROCESSAMENTO E SPLIT ---
def extract_text_and_split_by_dot(pdf_file: bytes) -> list[dict]:
    try:
        full_text = extract_pdf_text(pdf_file)

        cleaned = CLEANUP_REGEX.sub(" ", full_text).strip()
        cleaned = REFERENCE_REGEX.sub("", cleaned)

        partitions = [
            p.strip()
            for p in SENTENCE_SPLIT_REGEX.split(cleaned)
            if len(p.strip()) >= MIN_PARTITION_LENGTH
        ]

        return [
            {"partition_index": i + 1, "content": p}
            for i, p in enumerate(partitions)
        ]

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar PDF: {e}"
        )


# --- ENDPOINT PRINCIPAL ---
@app.post("/compare-pdfs-by-partition")
async def compare_pdfs_by_partition(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...)
):
    if not file1.filename.lower().endswith(".pdf") or not file2.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Ambos os arquivos devem ser PDFs"
        )

    content1 = await file1.read()
    content2 = await file2.read()

    partitions1 = extract_text_and_split_by_dot(content1)
    partitions2 = extract_text_and_split_by_dot(content2)

    choices = [p["content"] for p in partitions2]
    content_to_index2 = {
        p["content"]: p["partition_index"]
        for p in partitions2
    }

    similar_partitions = []

    for p1 in partitions1:
        if not choices:
            break

        best_match = process.extractOne(
            query=p1["content"],
            choices=choices,
            processor=lambda x: x.lower(),
            scorer=fuzz.token_set_ratio
        )

        if best_match:
            match_content, similarity_score = best_match

            if similarity_score >= SIMILARITY_CUTOFF:
                similar_partitions.append({
                    "doc1": {
                        "partition_index": p1["partition_index"],
                        "content": p1["content"]
                    },
                    "doc2": {
                        "partition_index": content_to_index2.get(match_content, "Desconhecido"),
                        "content": match_content
                    },
                    "similarity_score": similarity_score,
                    "similarity_metric": "token_set_ratio (TheFuzz)"
                })

    return {
        "message": "Comparação concluída com sucesso (pdfplumber + fuzzy matching).",
        "similarity_cutoff": f"{SIMILARITY_CUTOFF}%",
        "minimum_partition_length": f"{MIN_PARTITION_LENGTH} caracteres",
        "summary": {
            "total_partitions_file1": len(partitions1),
            "total_partitions_file2": len(partitions2),
            "matching_pairs_count": len(similar_partitions)
        },
        "plagiarized_paragraphs": similar_partitions
    }


# --- ENDPOINT ROOT ---
@app.get("/")
def read_root():
    return {
        "message": "PDF Plagiarism/Similarity API rodando com suporte a PDFs acadêmicos em duas colunas."
    }
