from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pypdf import PdfReader
import io
import re
from thefuzz import process, fuzz 

# --- CONFIGURAÇÕES GLOBAIS ---
app = FastAPI(title="PDF Plagiarism/Similarity Checker (Fuzzy Sentence-level)")

SIMILARITY_CUTOFF = 80 # Nível mínimo de similaridade (0 a 100)
MIN_PARTITION_LENGTH = 32 # Partições devem ter no mínimo 32 caracteres

# Regex para quebrar o texto APÓS um dos sinais de pontuação final
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.?!])\s+') 

# Regex para limpar quebras de linha e múltiplos espaços (Artefatos de PDF)
CLEANUP_REGEX = re.compile(r'[\n\r\t]+|\s{2,}')

# Regex para remoção de Referências (ABNT/acadêmicas)
# Busca por SOBRENOME, Inicial. ou linhas que começam com "Acesso em:"
REFERENCE_REGEX = re.compile(
    r"([A-ZÀ-Ú]+,\s*[A-ZÀ-Ú]\.\s*.+?\d{4}\..*?$|Acesso em:.*?$)",
    re.IGNORECASE | re.MULTILINE
)


# --- FUNÇÃO DE PRÉ-PROCESSAMENTO ---

def extract_text_and_split_by_dot(pdf_file: bytes) -> list[dict]:
    """
    Extrai o texto, realiza limpeza agressiva de quebras de linha, remove referências
    e divide em partições com tamanho mínimo.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_file))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() or ""
            full_text += " " # Adiciona espaço entre páginas
        
        # PASSO 1: Limpeza agressiva. Remove quebras de linha e substitui múltiplos espaços.
        cleaned_text_aggressive = CLEANUP_REGEX.sub(" ", full_text).strip()
        
        # PASSO 2: Remoção de Referências. 
        # Opera sobre o texto limpo, onde o padrão ABNT é mais fácil de ser encontrado.
        cleaned_text_no_refs = REFERENCE_REGEX.sub("", cleaned_text_aggressive)
        
        # 3. Quebra do Texto em partições (sentenças)
        # Filtra as strings vazias resultantes da limpeza e do split
        partitions = [p for p in SENTENCE_SPLIT_REGEX.split(cleaned_text_no_refs) if p]
        
        structured_partitions = []
        for i, content in enumerate(partitions):
            content = content.strip()
            
            # 4. FILTRO FINAL: Garante o tamanho mínimo de 32 caracteres
            if len(content) >= MIN_PARTITION_LENGTH: 
                structured_partitions.append({
                    "partition_index": i + 1,
                    "content": content
                })
        
        return structured_partitions
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Não foi possível ler o arquivo PDF ou o formato é inválido. Detalhe: {e}")

# --- ENDPOINT PRINCIPAL DA API ---

@app.post("/compare-pdfs-by-partition")
async def compare_pdfs_by_partition(
    file1: UploadFile = File(..., description="Primeiro arquivo PDF (Texto Fonte a ser verificado)"),
    file2: UploadFile = File(..., description="Segundo arquivo PDF (Base de comparação)"),
):
    """
    Compara cada partição (sentença/parágrafo) do Doc 1 com todas as partições do Doc 2 
    para encontrar a melhor correspondência (plágio/similaridade) usando TheFuzz.
    """
    # 1. Validação e Leitura
    if not file1.filename.lower().endswith(".pdf") or not file2.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Ambos os arquivos devem ser do formato PDF (.pdf)")

    content1 = await file1.read()
    content2 = await file2.read()

    # 2. Extração e Quebra do Texto (Partições)
    partitions1 = extract_text_and_split_by_dot(content1)
    partitions2 = extract_text_and_split_by_dot(content2)
    
    # 3. Preparação para TheFuzz
    choices = [p["content"] for p in partitions2]
    content_to_index2 = {p["content"]: p["partition_index"] for p in partitions2}

    # 4. Comparação usando TheFuzz.process.extractOne
    similar_partitions = []
    
    for p1 in partitions1:
        text_to_check = p1["content"]
        
        # Se a lista de escolhas (Doc 2) estiver vazia, não há o que comparar.
        if not choices:
             break
        
        # Encontra a melhor correspondência no Doc 2.
        best_match_tuple = process.extractOne(
            query=text_to_check, 
            choices=choices, 
            processor=lambda x: x.lower(), # Normaliza para minúsculas
            scorer=fuzz.token_set_ratio # Ignora ordem e palavras extras
        )

        if best_match_tuple:
            match_content = best_match_tuple[0]
            similarity_score = best_match_tuple[1]
            
            # 5. Filtragem e Estrutura de Retorno
            if similarity_score >= SIMILARITY_CUTOFF:
                
                match_index_doc2 = content_to_index2.get(match_content, "Desconhecido")
                
                # Adiciona o par encontrado à lista de resultados
                similar_partitions.append({
                    "doc1": {
                        "partition_index": p1["partition_index"],
                        "content": p1["content"]
                    },
                    "doc2": {
                        "partition_index": match_index_doc2,
                        "content": match_content
                    },
                    "similarity_score": similarity_score,
                    "similarity_metric": "token_set_ratio (TheFuzz)"
                })

    # 6. Resultado Final
    result = {
        "message": "Comparação de similaridade de partições concluída usando TheFuzz (Limpeza e filtragem avançada).",
        "similarity_cutoff": f"{SIMILARITY_CUTOFF}%",
        "minimum_partition_length": f"{MIN_PARTITION_LENGTH} caracteres",
        "summary": {
            "total_partitions_file1": len(partitions1),
            "total_partitions_file2": len(partitions2),
            "matching_pairs_count": len(similar_partitions),
        },
        "plagiarized_paragraphs": similar_partitions
    }

    return result

# --- ENDPOINT DE TESTE ---
@app.get("/")
def read_root():
    return {"message": "PDF Plagiarism/Similarity API (TheFuzz) está rodando. Acesse /docs para a documentação e teste."}