from fastapi import FastAPI, File, UploadFile, HTTPException
from starlette.middleware.cors import CORSMiddleware
import pdfplumber
import io
import re
from thefuzz import process, fuzz

# ==================================================
# CONFIGURAÇÕES GLOBAIS
# ==================================================

app = FastAPI(
    title="PDF Similarity Checker with Citation Awareness",
    description="Sentence-level PDF similarity detection with citation identification",
)

origins = [
    "http://localhost",
    "http://localhost:5173",
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
SENTENCE_CHUNK_SIZE = 3

# ==================================================
# REGEX E HEURÍSTICAS
# ==================================================

SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.?!])\s+')
CLEANUP_REGEX = re.compile(r'[\n\r\t]+|\s{2,}')

REFERENCE_SECTION_REGEX = re.compile(
    r'^\s*(REFERÊNCIAS|Referências|REFERENCES).*',
    re.DOTALL | re.MULTILINE
)

# --- CITAÇÕES BIBLIOGRÁFICAS ---

AUTHOR_YEAR_REGEX = re.compile(
    r'\((?:[A-ZÁ-Ú][A-Za-zÁ-ú]+(?:\s+et\s+al\.)?,?\s*\d{4}[a-z]?)\)'
)

AUTHOR_YEAR_NARRATIVE_REGEX = re.compile(
    r'\b[A-ZÁ-Ú][a-zá-ú]+\s*\(\d{4}[a-z]?\)'
)

NARRATIVE_CITATION_REGEX = re.compile(
    r'(?:Segundo|Conforme|De acordo com)\s+[A-ZÁ-Ú][a-zá-ú]+(?:\s+et\s+al\.)?\s*\(\d{4}[a-z]?\)',
    re.IGNORECASE
)

NUMERIC_CITATION_REGEX = re.compile(
    r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]'
)

CITATION_VERBS = [
    "segundo", "conforme", "de acordo com",
    "apud", "et al", "doi"
]

# ==================================================
# EXTRAÇÃO DE TEXTO
# ==================================================

def extract_pdf_text(pdf_bytes: bytes) -> str:
    text = ""

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )
            if page_text:
                text += page_text + " "

    return text

# ==================================================
# DETECÇÃO E NORMALIZAÇÃO DE CITAÇÕES
# ==================================================

def detect_citation(text: str) -> bool:
    if (
        AUTHOR_YEAR_REGEX.search(text)
        or AUTHOR_YEAR_NARRATIVE_REGEX.search(text)
        or NARRATIVE_CITATION_REGEX.search(text)
        or NUMERIC_CITATION_REGEX.search(text)
    ):
        return True

    lower = text.lower()
    return any(v in lower for v in CITATION_VERBS)


def normalize_citations(text: str) -> str:
    text = AUTHOR_YEAR_REGEX.sub(" [CITATION] ", text)
    text = AUTHOR_YEAR_NARRATIVE_REGEX.sub(" [CITATION] ", text)
    text = NARRATIVE_CITATION_REGEX.sub(" [CITATION] ", text)
    text = NUMERIC_CITATION_REGEX.sub(" [CITATION] ", text)
    return text

# ==================================================
# PARTICIONAMENTO EM BLOCOS DE 3 SENTENÇAS
# ==================================================

def chunk_sentences(sentences: list[str], chunk_size: int) -> list[str]:
    chunks = []
    buffer = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        buffer.append(sentence)

        if len(buffer) == chunk_size:
            chunks.append(" ".join(buffer))
            buffer = []

    if buffer:
        chunks.append(" ".join(buffer))

    return chunks


def extract_text_and_split(pdf_bytes: bytes) -> list[dict]:
    try:
        raw_text = extract_pdf_text(pdf_bytes)

        cleaned = CLEANUP_REGEX.sub(" ", raw_text).strip()
        cleaned = REFERENCE_SECTION_REGEX.sub("", cleaned)

        normalized_full = normalize_citations(cleaned)

        sentences_original = SENTENCE_SPLIT_REGEX.split(cleaned)
        sentences_normalized = SENTENCE_SPLIT_REGEX.split(normalized_full)

        chunks_original = chunk_sentences(sentences_original, SENTENCE_CHUNK_SIZE)
        chunks_normalized = chunk_sentences(sentences_normalized, SENTENCE_CHUNK_SIZE)

        partitions = []

        for idx, (orig, norm) in enumerate(
            zip(chunks_original, chunks_normalized),
            start=1
        ):
            if len(orig) < MIN_PARTITION_LENGTH:
                continue

            partitions.append({
                "partition_index": idx,
                "content": orig,
                "normalized_content": norm,
                "contains_citation": detect_citation(orig)
            })

        return partitions

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro ao processar PDF: {str(e)}"
        )

# ==================================================
# ENDPOINT PRINCIPAL
# ==================================================

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

    partitions1 = extract_text_and_split(content1)
    partitions2 = extract_text_and_split(content2)

    choices = [p["normalized_content"] for p in partitions2]
    content_map_2 = {
        p["normalized_content"]: p
        for p in partitions2
    }

    similar_partitions = []

    for p1 in partitions1:
        if not choices:
            break

        best_match = process.extractOne(
            query=p1["normalized_content"],
            choices=choices,
            processor=lambda x: x.lower(),
            scorer=fuzz.token_set_ratio
        )

        if not best_match:
            continue

        match_text, similarity_score = best_match
        matched_p2 = content_map_2.get(match_text)

        if similarity_score >= SIMILARITY_CUTOFF and matched_p2:
            similar_partitions.append({
                "doc1": {
                    "partition_index": p1["partition_index"],
                    "content": p1["content"],
                    "contains_citation": p1["contains_citation"]
                },
                "doc2": {
                    "partition_index": matched_p2["partition_index"],
                    "content": matched_p2["content"],
                    "contains_citation": matched_p2["contains_citation"]
                },
                "similarity_score": similarity_score,
                "similarity_metric": "token_set_ratio (TheFuzz)"
            })

    return {
        "message": "Comparação concluída com fragmentação por 3 sentenças e detecção de citações.",
        "similarity_cutoff": f"{SIMILARITY_CUTOFF}%",
        "minimum_partition_length": f"{MIN_PARTITION_LENGTH} caracteres",
        "summary": {
            "total_partitions_file1": len(partitions1),
            "total_partitions_file2": len(partitions2),
            "matching_pairs_count": len(similar_partitions)
        },
        "plagiarized_paragraphs": similar_partitions
    }

# ==================================================
# ENDPOINT ROOT
# ==================================================

@app.get("/")
def read_root():
    return {
        "message": (
            "API de similaridade textual em PDFs com fragmentação por três "
            "sentenças e identificação de citações bibliográficas."
        )
    }
