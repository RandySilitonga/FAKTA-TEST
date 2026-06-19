# Arsitektur Sistem FAKTA — Fact-Checking AI berbasis Hybrid Model
> **Tujuan:** Dokumen arsitektur lengkap untuk sistem pendeteksi hoax Bahasa Indonesia

## 1. Gambaran Umum
pake 2 pipeline, 1 nya indobert sebagai klasifikasi, wikipedia sebagai verifikator. Googl e
FAKTA adalah sistem deteksi hoax **hybrid** yang menggabungkan tiga pendekatan:

| Komponen | Peran |
|---|---|
| **IndoBERT** | Klasifikasi pola linguistik per klaim | Pakai LSTM aja, lebih ringan. Karena jalannya 1 per 1
| **LLM (Claim Extractor + Reasoning)** | Ekstraksi klaim utama, reasoning berbasis evidence |, untuk fine tune nya freeze layer terakhir
| **Evidence Retrieval (RAG)** | Pencarian bukti dari sumber kredibel |

Keputusan final diambil melalui **weighted decision fusion** — bukan dari satu model tunggal.

---

## 2. Diagram Arsitektur

```
┌─────────────────────────────────────────────┐
│              USER INPUT                       │
│  (Judul + Isi Teks / Postingan / URL)        │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         NLP PREPROCESSING MODULE             │
│  • Lowercase, hapus URL/emoji               │
│  • Normalisasi slang (gk→tidak, bgt→banget) │
│  • Tokenisasi, stemming, stopword removal   │
│  • Ekstraksi metadata features               │ NLTK, TensorFlow
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         LLM CLAIM EXTRACTION                 │
│  Input: teks yang sudah dibersihkan          │
│  Output: daftar klaim terstruktur (1-N)      │
│  Contoh:                                     │
│    Claim 1: "Vaksin menyebabkan gagal ginjal" │
│    Claim 2: "Banyak korban meninggal"        │
└──────────────────┬──────────────────────────┘
                   ↓
        ┌──────────┴──────────┐
        ↓                     ↓
┌───────────────────┐ ┌──────────────────────┐
│  CLASSIFIER MODEL  │ │ EVIDENCE RETRIEVAL   │
│  per claim         │ │  per claim           │
│                   │ │                      │
│  A. IndoBERT (utama) │  • BM25 (keyword)   │
│  B. BiLSTM (baseline)│  • Sentence-Transformer │
│                     │    (semantic search)  │
│  Input: claim text  │  • Hybrid ranking     │
│  Output:            │  • Top-3 evidence     │
│    hoax_proba       │  • Source credibility │
│    valid_proba      │    score              │
│    uncertain_proba  │                      │
└────────┬──────────┘ └──────────┬──────────┘
         ↓                       ↓
┌─────────────────────────────────────────────┐
│         LLM EVIDENCE JUDGE                   │
│  Input: claim + top-3 evidence              │
│  Output: verdict (Supported/Refuted/NEI)    │
│          + confidence + reasoning singkat   │
│  Constraint: hanya gunakan evidence yang    │
│  diberikan, tidak mengarang sumber baru      │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         DECISION FUSION ENGINE               │
│  Weighted scoring per claim:                 │
│    final = w1·BERT + w2·evidence            │
│          + w3·LLM + w4·source_cred          │
│          + w5·linguistic_features           │
│                                              │
│  Threshold:                                  │
│    > 0.70 → Hoax (Refuted)                  │
│    < 0.30 → Tidak Hoax (Supported)          │
│    0.30–0.70 → Tidak Cukup Bukti (NEI)      │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│         ARTICLE-LEVEL AGGREGATION            │
│  Per-claim verdict → article verdict:       │
│    • Jika ada 1+ klaim Refuted → Hoax       │
│    • Semua Supported → Tidak Hoax           │
│    • Sisanya → Tidak Cukup Bukti            │
│                                              │
│  Output terstruktur:                         │
│    { verdict, confidence, claims[],          │
│      evidence[], explanation, sources[] }    │
└─────────────────────────────────────────────┘
```

---

## 3. Detail Per Modul

### 3.1 NLP Preprocessing Module

**Tujuan:** Membersihkan dan menormalisasi teks Bahasa Indonesia sebelum diproses lebih lanjut.

#### 3.1.1 Text Cleaning Pipeline

```
Raw Text
  ↓
1. Case folding → lowercase
2. Hapus URL (http://, https://, www.)
3. Hapus mention (@username) dan hashtag (#...)
4. Hapus emoji berlebihan (sisakan maksimal 1 per kalimat)
5. Hapus karakter khusus yang tidak informatif
6. Normalisasi tanda baca berlebihan (!!!, ???) → (!, ?)
7. Hapus spasi ganda dan trim
```

#### 3.1.2 Normalisasi Slang / Bahasa Tidak Baku

Mapping menggunakan dictionary lookup:

| Slang | Normal |
|---|---|
| gk, ga, gak, ngga, nggak | tidak |
| bgt | banget |
| yg | yang |
| dg | dengan |
| krn | karena |
| jgn | jangan |
| udh, udah | sudah |
| klo, klo | kalau |
| sm | sama |
| dr | dari |
| sy, gua, gw | saya |
| bkn | bukan |
| tp | tapi |
| dpt | dapat |
| nge- | me- (prefix) |
| di- | di- (prefix) |
| ke- | ke- (prefix) |

Library yang dipakai: **Sastrawi** (stemmer Bahasa Indonesia).

#### 3.1.3 Metadata Feature Extraction

Fitur linguistik dan stilistik yang diekstrak dari teks mentah:

| Fitur | Tipe | Contoh |
|---|---|---|
| `text_length` | int | jumlah karakter |
| `word_count` | int | jumlah kata |
| `sentence_count` | int | jumlah kalimat |
| `avg_word_length` | float | rata-rata panjang kata |
| `caps_ratio` | float | proporsi huruf kapital |
| `exclamation_count` | int | jumlah tanda seru |
| `question_count` | int | jumlah tanda tanya |
| `provocative_word_count` | int | kata-kata provokatif (viral, heboh, geger, gempar, dll) |
| `clickbait_score` | float | skor berdasarkan pola clickbait |
| `sentiment_score` | float | dari sentiment analyzer (-1 s/d +1) |
| `has_source_mention` | bool | apakah ada nama institusi sumber |
| `has_date_mention` | bool | apakah ada tanggal/waktu spesifik |
| `has_data_mention` | bool | apakah ada angka/statistik |
| `urgency_words` | int | kata-kata mendesak (segera, sebelum terlambat, dll) |

Fitur ini di-normalisasi (MinMax / StandardScaler) lalu concat ke output model.

---

### 3.2 LLM Claim Extraction Module

**Tujuan:** Mengekstrak klaim-klaim faktual yang dapat diverifikasi dari teks.

#### 3.2.1 Input & Output

**Input:** Teks yang sudah dibersihkan dari Preprocessing Module.

**Output:** JSON terstruktur:

```json
{
  "claims": [
    {
      "claim_id": 1,
      "claim_text": "Vaksin menyebabkan gagal ginjal massal",
      "claim_type": "causal",
      "original_sentence": "Vaksin yang diberikan pemerintah menyebabkan gagal ginjal massal di Indonesia.",
      "entities": ["vaksin", "gagal ginjal", "Indonesia"]
    },
    {
      "claim_id": 2,
      "claim_text": "Banyak korban meninggal akibat vaksin",
      "claim_type": "factual",
      "original_sentence": "Sudah banyak korban meninggal akibat vaksin ini.",
      "entities": ["korban meninggal", "vaksin"]
    }
  ]
}
```

#### 3.2.2 Claim Types

| Tipe | Keterangan | Contoh |
|---|---|---|
| `causal` | Klaim sebab-akibat | "A menyebabkan B" |
| `factual` | Klaim fakta | "Terjadi X di tempat Y" |
| `statistical` | Klaim statistik/angka | "80% orang mengalami X" |
| `attribution` | Klaim atribusi | "Menurut WHO, X benar" |
| `opinion` | Opini / bukan fakta | "Menurut saya X buruk" |

**Note:** Klaim tipe `opinion` tidak masuk ke pipeline verifikasi — langsung dikembalikan sebagai "tidak dapat diverifikasi (opini)".

#### 3.2.3 Prompt Template

```
Kamu adalah asisten ekstraksi klaim untuk sistem fact-checking.

Dari teks berikut, ekstrak SEMUA klaim faktual yang dapat diverifikasi.
Jangan masukkan opini, saran, atau pernyataan subjektif.

Untuk setiap klaim, tentukan:
- claim_text: klaim dalam 1 kalimat singkat
- claim_type: causal / factual / statistical / attribution
- original_sentence: kalimat asli tempat klaim berasal
- entities: entitas kunci yang disebut

Teks:
{cleaned_text}

Output dalam format JSON yang valid. Jangan tambahkan teks lain.
```

#### 3.2.4 Model yang Digunakan

Untuk versi MVP: **LLM API (OpenAI/Gemini)** atau **local LLM (Ollama)**.

Untuk versi lanjutan: fine-tune **IndoBERT** untuk task claim extraction (sequence labeling).

---

### 3.3 Classifier Model Module

**Tujuan:** Mengklasifikasikan setiap klaim sebagai hoax / valid / uncertain berdasarkan pola linguistik.

#### 3.3.1 Model A: IndoBERT (Model Utama)

**Arsitektur:**

```
Input: claim_text (tokenized)
  ↓
IndoBERT-base (pre-trained, fine-tuned)
  ↓
[CLS] token representation (768-dim)
  ↓
Dropout (0.3)
  ↓
Dense (256, ReLU)
  ↓
Dropout (0.2)
  ↓
Dense (128, ReLU)
  ↓
Dense (3, Softmax) → [hoax, valid, uncertain]
```

**Alasan:** Transformer-based model terbukti lebih kuat dari LSTM untuk fake news detection Bahasa Indonesia. Penelitian menunjukkan akurasi ~90% pada dataset TurnBackHoax gabungan.

**Training Setup:**
- Optimizer: AdamW (lr=2e-5)
- Batch size: 16
- Epochs: 5-10
- Loss: Cross-Entropy (dengan class weights untuk handle imbalance)
- Max sequence length: 256 tokens
- Framework: Hugging Face Transformers

#### 3.3.2 Model B: BiLSTM + Attention (Baseline)

**Arsitektur:**

```
Input: claim_text (tokenized)
  ↓
Embedding Layer (vocab_size x 300)
  Word2Vec / FastText Indonesia pre-trained
  ↓
Bidirectional LSTM (hidden=128, return_sequences=True)
  ↓
Attention Layer
  ↓
Dense (64, ReLU)
  ↓
Dropout (0.3)
  ↓
Dense (32, ReLU)
  ↓
Dense (3, Softmax) → [hoax, valid, uncertain]
```

**Alasan:** Sebagai baseline akademis untuk menunjukkan improvement dari model sequence-based ke Transformer.

**Training Setup:**
- Embedding: FastText Indonesia (cc.id.300.bin)
- Optimizer: Adam (lr=0.001)
- Batch size: 64
- Epochs: 20 (dengan early stopping patience=5)
- Max sequence length: 200 tokens

#### 3.3.3 Feature Fusion Branch

Linguistic features dari Preprocessing Module digabung ke classifier:

```
IndoBERT/BiLSTM output → 128-dim vector
                                    CONCAT → Dense(64) → Dense(3, Softmax)
Linguistic features    → 14-dim vector (normalized)
```

Jadi model tidak hanya belajar dari teks tapi juga dari ciri-ciri stilistik.

#### 3.3.4 Output per Claim

```json
{
  "claim_id": 1,
  "bert_proba": { "hoax": 0.82, "valid": 0.12, "uncertain": 0.06 },
  "bilstm_proba": { "hoax": 0.75, "valid": 0.18, "uncertain": 0.07 }
}
```

---

### 3.4 Evidence Retrieval Module

**Tujuan:** Mencari bukti yang relevan untuk setiap klaim dari sumber kredibel.

#### 3.4.1 Arsitektur Retrieval — Hybrid Search

```
Claim Text
    ↓
┌───────────────────┐  ┌──────────────────────────┐
│  BM25 (Keyword)   │  │  Sentence-Transformer     │
│  • Token-based    │  │  (Semantic)               │
│  • Exact match    │  │  • Embedding similarity   │
│  • TF-IDF weighted│  │  • cos(A, B)              │
└────────┬──────────┘  └────────────┬─────────────┘
         ↓                          ↓
┌──────────────────────────────────────────────┐
│          HYBRID RANKING                       │
│  score = α·BM25_score + (1-α)·Semantic_score │
│  α = 0.4 (prioritaskan semantic)             │
│  Top-K = 5 kandidat                          │
└──────────────────┬───────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│          SOURCE CREDIBILITY FILTER            │
│  Tier 1 (weight 1.0): Kemenkes, WHO, BMKG    │
│  Tier 2 (weight 0.8): Kompas, Tempo, Detik   │
│  Tier 3 (weight 0.6): MAFINDO/TurnBackHoax   │
│  Tier 4 (weight 0.4): Blog/forum/media kecil │
│                                              │
│  Top-3 evidence setelah filter               │
└──────────────────────────────────────────────┘
```

#### 3.4.2 Database / Vector Store

**Pilihan untuk MVP:**
- **ChromaDB** — mudah setup, in-memory, cocok untuk development
- **FAISS** — lebih cepat untuk dataset besar

**Skema dokumen evidence:**

```json
{
  "id": "evidence_001",
  "source": "Kemenkes RI",
  "source_tier": 1,
  "url": "https://kemkes.go.id/...",
  "title": "Fakta tentang Gagal Ginjal",
  "text": "Tidak ada bukti ilmiah bahwa konsumsi matcha...",
  "category": "health",
  "date_published": "2025-03-15",
  "embedding": [0.12, -0.34, ...]
}
```

#### 3.4.3 Sumber Data Evidence

| Sumber | Tipe | Cara Ingest |
|---|---|---|
| TurnBackHoax (MAFINDO) | Database hoax | Scraping + manual entry |
| Kominfo (info.gov.id) | Klarifikasi resmi | Scraping / API |
| Kemenkes / WHO | Sumber kesehatan | Manual curation |
| BMKG | Cuaca/gempa | API / scraping |
| Media kredibel (Kompas, Tempo, dll) | Berita | Scraping + RSS |
| Wikipedia | Referensi umum | API / dump |
| Jurnal akademik | Sumber ilmiah | Google Scholar API |

#### 3.4.4 Output Evidence per Claim

```json
{
  "claim_id": 1,
  "evidence": [
    {
      "source": "Kemenkes RI",
      "source_tier": 1,
      "url": "https://kemkes.go.id/fakta-matcha",
      "text": "Konsumsi matcha dalam batas normal tidak terbukti menyebabkan gagal ginjal.",
      "bm25_score": 0.72,
      "semantic_score": 0.85,
      "hybrid_score": 0.80,
      "credibility_weight": 1.0,
      "final_score": 0.80
    },
    {
      "source": "TurnBackHoax",
      "source_tier": 3,
      "url": "https://turnbackhoax.id/matcha-gagal-ginjal-hoax",
      "text": "Klaim bahwa matcha menyebabkan gagal ginjal tidak benar.",
      "bm25_score": 0.68,
      "semantic_score": 0.78,
      "hybrid_score": 0.74,
      "credibility_weight": 0.6,
      "final_score": 0.44
    }
  ],
  "best_evidence_score": 0.80
}
```

---

### 3.5 LLM Evidence Judge Module

**Tujuan:** Menganalisis klaim bersama evidence dan memberikan verdict berbasis bukti.

#### 3.5.1 Input & Output

**Input:**

```json
{
  "claim": "Minum matcha setiap hari menyebabkan gagal ginjal",
  "evidence": [
    { "source": "Kemenkes RI", "text": "..." },
    { "source": "TurnBackHoax", "text": "..." }
  ]
}
```

**Output:**

```json
{
  "claim_id": 1,
  "verdict": "Refuted",
  "confidence": 0.88,
  "reasoning": "Klaim bahwa konsumsi matcha menyebabkan gagal ginjal dibantah oleh Kementerian Kesehatan RI yang menyatakan tidak ada bukti ilmiah untuk hal tersebut. TurnBackHoax juga telah mengklarifikasi klaim ini sebagai hoaks.",
  "evidence_used": ["Kemenkes RI", "TurnBackHoax"]
}
```

#### 3.5.2 Prompt Template

```
Kamu adalah asisten fact-checking. Tugasmu adalah menganalisis klaim berdasarkan
bukti yang disediakan dan menentukan verdict.

VERDICT YANG MUNGKIN:
1. Supported — bukti kuat mendukung klaim
2. Refuted — bukti kuat membantah klaim
3. NotEnoughEvidence — bukti tidak cukup atau tidak relevan

ATURAN:
- HANYA gunakan evidence yang diberikan. JANGAN membuat fakta baru.
- JANGAN mencari informasi di luar evidence.
- Jika evidence bertentangan, jelaskan konfliknya.
- Jika evidence tidak relevan dengan klaim → NotEnoughEvidence.
- Berikan reasoning singkat (2-3 kalimat) yang merujuk ke evidence spesifik.

KLAIM:
{claim_text}

BUKTI:
{evidence_list}

Output dalam format JSON:
{
  "verdict": "Supported" | "Refuted" | "NotEnoughEvidence",
  "confidence": <0.0-1.0>,
  "reasoning": "..."
}
```

---

### 3.6 Decision Fusion Engine

**Tujuan:** Menggabungkan semua sinyal menjadi keputusan final per klaim.

#### 3.6.1 Weighted Scoring Formula

Untuk setiap klaim, hitung final score:

```
final_score = (w1 × bert_hoax_proba)
            + (w2 × best_evidence_score × contradiction_factor)
            + (w3 × llm_refuted_score)
            + (w4 × (1 - source_credibility_avg))
            + (w5 × linguistic_hoax_score)
```

**Bobot default:**

| Sinyal | Bobot | Alasan |
|---|---|---|
| `bert_hoax_proba` | w1 = 0.20 | Pattern recognition dari Transformer |
| `evidence_contradiction` | w2 = 0.35 | Sinyal terkuat — bukti langsung |
| `llm_refuted_score` | w3 = 0.25 | Reasoning berbasis evidence |
| `source_credibility` | w4 = 0.10 | Kredibilitas sumber evidence |
| `linguistic_features` | w5 = 0.10 | Ciri stilistik hoax |

**Contradiction factor:**
```
Jika evidence mendukung klaim → contradiction_factor = 0.0
Jika evidence membantah klaim  → contradiction_factor = 1.0
Jika evidence mixed            → contradiction_factor = 0.5
```

Ditentukan oleh LLM Evidence Judge berdasarkan perbandingan klaim vs evidence.

#### 3.6.2 Threshold Keputusan

| Final Score | Verdict | Label Output |
|---|---|---|
| > 0.70 | **Refuted** | `Hoax` |
| < 0.30 | **Supported** | `Tidak Hoax` |
| 0.30 — 0.70 | **NotEnoughEvidence** | `Tidak Cukup Bukti` |

#### 3.6.3 Confidence Score

```
confidence = max(final_score, 1 - final_score)

Jika verdict = Hoax → confidence = final_score
Jika verdict = Tidak Hoax → confidence = 1 - final_score
Jika verdict = Tidak Cukup Bukti → confidence = 1 - |2 × final_score - 1|
```

Jadi di area "Tidak Cukup Bukti" (score ~0.5), confidence rendah.

#### 3.6.4 Output per Claim (Final)

```json
{
  "claim_id": 1,
  "claim_text": "Minum matcha setiap hari menyebabkan gagal ginjal",
  "verdict": "Hoax",
  "verdict_raw": "Refuted",
  "confidence": 0.86,
  "score_breakdown": {
    "bert_hoax": 0.82,
    "evidence_contradiction": 0.80,
    "llm_refuted": 0.88,
    "source_credibility_low": 0.10,
    "linguistic_hoax": 0.65,
    "final_score": 0.78
  },
  "reasoning": "Klaim dibantah oleh Kemenkes RI dan telah diklarifikasi oleh TurnBackHoax sebagai informasi tidak benar.",
  "evidence_sources": [
    { "name": "Kemenkes RI", "url": "https://..." },
    { "name": "TurnBackHoax", "url": "https://..." }
  ]
}
```

---

### 3.7 Article-Level Aggregation Module

**Tujuan:** Menggabungkan verdict per-klaim menjadi verdict untuk seluruh artikel.

#### 3.7.1 Aggregation Rules

| Kondisi | Article Verdict | Alasan |
|---|---|---|
| Ada ≥1 klaim `Hoax` | **Hoax** | Satu klaim salah sudah cukup untuk label artikel hoax |
| Semua klaim `Tidak Hoax` | **Tidak Hoax** | Semua klaim terbukti benar |
| Semua klaim `Tidak Cukup Bukti` | **Tidak Cukup Bukti** | Tidak ada yang bisa diverifikasi |
| Campuran `Tidak Hoax` + `Tidak Cukup Bukti` | **Tidak Cukup Bukti** | Sebagian benar, sebagian belum bisa dicek |
| Tidak ada klaim yang bisa diekstrak | **Tidak Cukup Bukti** | Artikel opini / tidak ada klaim faktual |

#### 3.7.2 Article Confidence

```
article_confidence = max(confidence_klaim_hoax) jika ada klaim hoax
article_confidence = min(confidence_semua_klaim) jika semua valid
article_confidence = average(confidence) jika mixed
```

#### 3.7.3 Output Final Sistem

```json
{
  "verdict": "Hoax",
  "confidence": 0.86,
  "article_summary": "Artikel mengandung klaim yang dibantah oleh sumber kredibel.",
  "claims": [
    {
      "claim_id": 1,
      "claim_text": "Minum matcha menyebabkan gagal ginjal",
      "verdict": "Hoax",
      "confidence": 0.86,
      "reasoning": "...",
      "evidence_sources": ["Kemenkes RI", "TurnBackHoax"]
    },
    {
      "claim_id": 2,
      "claim_text": "Banyak korban meninggal akibat matcha",
      "verdict": "Tidak Cukup Bukti",
      "confidence": 0.42,
      "reasoning": "Tidak ditemukan bukti yang cukup...",
      "evidence_sources": []
    }
  ],
  "risk_level": "High",
  "recommendation": "Informasi ini mengandung klaim yang tidak benar. Harap verifikasi dari sumber kredibel.",
  "processing_time_ms": 3450
}
```

---

## 4. Dataset & Training

### 4.1 Dataset Utama (Bahasa Indonesia)

| Dataset | Sumber | Ukuran | Label |
|---|---|---|---|
| **TurnBackHoax** | MAFINDO | 10.000+ | Hoax / Non-hoax |
| **Indonesian Hoax News Detection** | Mendeley Data | ~4.000 | Hoax / Non-hoax |
| **Kaggle CNN Indonesia / Tempo** | Kaggle | ~5.000 | Hoax / Non-hoax |
| **Custom scraped** | TurnBackHoax.id | Scraping langsung | Hoax / Non-hoax |

### 4.2 Dataset Internasional (Opsional — Transfer Learning)

| Dataset | Kegunaan |
|---|---|
| FEVER | Claim verification (Supported/Refuted/NEI) |
| LIAR | Fact-checking dengan metadata |
| FakeNewsNet | Fake news dengan social context |

### 4.3 Data Split

```
Training:   70%
Validation: 15%
Test:       15%
```

**Stratified split** untuk menjaga distribusi kelas.

### 4.4 Class Imbalance Handling

```
• Class weights dalam loss function
• SMOTE oversampling (untuk classical models)
• Data augmentation: synonym replacement, back-translation
```

---

## 5. Evaluasi

### 5.1 Model Classification Metrics

| Metrik | Target | Alasan |
|---|---|---|
| **Accuracy** | > 85% | Overall correctness |
| **Macro-F1** | > 0.80 | Penting karena imbalance |
| **Recall (Hoax)** | > 0.85 | Jangan sampai hoax terlewat |
| **Precision (Hoax)** | > 0.80 | Minimalkan false positive |
| **ROC-AUC** | > 0.90 | Separability antar kelas |
| **Confusion Matrix** | — | Analisis error pattern |

### 5.2 Evidence Retrieval Metrics

| Metrik | Target |
|---|---|
| **Precision@3** | > 0.70 |
| **NDCG@5** | > 0.75 |
| **Mean Reciprocal Rank** | > 0.60 |

### 5.3 Claim Extraction Metrics

| Metrik | Target |
|---|---|
| **Claim F1** | > 0.75 |
| **Claim Recall** | > 0.80 |

### 5.4 End-to-End Metrics

| Metrik | Target |
|---|---|
| **False Positive Rate** | < 10% |
| **False Negative Rate** | < 15% |
| **Average processing time** | < 5 detik |

---

## 6. Tech Stack

### 6.1 Development & ML

```
Python 3.11+
Pandas, NumPy
Scikit-learn (baseline models)
Hugging Face Transformers (IndoBERT)
TensorFlow / PyTorch (BiLSTM)
NLTK + Sastrawi (NLP Indonesia)
Sentence-Transformer (semantic search)
FAISS / ChromaDB (vector store)
LangChain (opsional — orchestrasi RAG)
```

### 6.2 LLM Integration

```
OpenAI API (GPT-4o-mini / GPT-4o) — claim extraction & reasoning
ATAU
Google Gemini API
ATAU
Ollama (local LLM — llama3/llama3.1) — offline mode
```

### 6.3 Backend & API

```
FastAPI (REST API)
Pydantic (request/response validation)
SQLite / PostgreSQL (data storage)
Redis (caching evidence queries)
```

### 6.4 Frontend / UI

```
MVP: Streamlit (cepat, untuk demo/validasi)
Production: Next.js / React + Tailwind CSS
```

### 6.5 DevOps (Opsional)

```
Docker (containerization)
GitHub Actions (CI/CD)
Hugging Face Hub (model hosting)
```

---

## 7. Roadmap MVP

### Fase 1: Baseline (Minggu 1-2)

```
✓ Kumpulkan & bersihkan dataset
✓ Preprocessing pipeline
✓ TF-IDF + SVM / Logistic Regression
✓ Evaluasi baseline metrics
```

**Output:** Model klasifikasi sederhana, akurasi target ~75-80%.

### Fase 2: Deep Learning (Minggu 3-4)

```
✓ BiLSTM + Attention model
✓ IndoBERT fine-tuning
✓ Feature fusion (linguistic features)
✓ Perbandingan BiLSTM vs IndoBERT
```

**Output:** Dua model deep learning dengan perbandingan metrics.

### Fase 3: Claim Extraction (Minggu 5)

```
✓ LLM claim extraction pipeline
✓ Claim type classification
✓ Evaluasi claim extraction quality
```

**Output:** Sistem bisa memecah artikel menjadi klaim-klaim terverifikasi.

### Fase 4: Evidence Retrieval (Minggu 6-7)

```
✓ Setup ChromaDB / FAISS
✓ Ingest evidence dari TurnBackHoax + sumber lain
✓ BM25 + Semantic hybrid search
✓ Source credibility scoring
```

**Output:** Database evidence yang bisa di-query per klaim.

### Fase 5: LLM Reasoning + Fusion (Minggu 8)

```
✓ LLM evidence judge
✓ Decision fusion engine (weighted scoring)
✓ Article-level aggregation
✓ Structured output generation
```

**Output:** Sistem hybrid lengkap dengan verdict + confidence + reasoning.

### Fase 6: UI + Deployment (Minggu 9-10)

```
✓ Streamlit UI
✓ FastAPI backend
✓ End-to-end testing
✓ Dokumentasi & paper
```

**Output:** Aplikasi web yang bisa didemokan.

---

## 8. Struktur Folder Project

```
FAKTA/
├── data/
│   ├── raw/                    # Dataset mentah
│   ├── processed/              # Dataset yang sudah diproses
│   └── evidence/               # Database evidence
│       ├── turnbackhoax/
│       ├── kominfo/
│       └── kemenkes/
├── models/
│   ├── baseline/               # TF-IDF + SVM/LR
│   ├── bilstm/                 # BiLSTM model + weights
│   └── indobert/               # IndoBERT fine-tuned
├── src/
│   ├── __init__.py
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── cleaning.py         # Text cleaning
│   │   ├── slang_normalizer.py # Slang mapping
│   │   └── feature_extractor.py# Linguistic features
│   ├── claim_extraction/
│   │   ├── __init__.py
│   │   └── llm_extractor.py   # LLM claim extraction
│   ├── classifiers/
│   │   ├── __init__.py
│   │   ├── baseline.py         # TF-IDF + SVM
│   │   ├── bilstm.py           # BiLSTM model
│   │   ├── indobert.py         # IndoBERT model
│   │   └── trainer.py          # Training utilities
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── retriever.py        # Hybrid BM25 + Semantic
│   │   ├── indexer.py          # Evidence ingestion
│   │   └── credibility.py      # Source scoring
│   ├── fusion/
│   │   ├── __init__.py
│   │   ├── llm_judge.py        # LLM evidence analysis
│   │   ├── scoring.py          # Weighted fusion
│   │   └── aggregation.py      # Article-level verdict
│   └── api/
│       ├── __init__.py
│       ├── main.py             # FastAPI app
│       └── schemas.py          # Pydantic models
├── notebooks/
│   ├── 01_eda.ipynb            # Exploratory data analysis
│   ├── 02_baseline.ipynb       # Baseline model experiments
│   ├── 03_bilstm.ipynb         # BiLSTM experiments
│   ├── 04_indobert.ipynb       # IndoBERT fine-tuning
│   └── 05_end_to_end.ipynb     # Full pipeline test
├── tests/
│   ├── test_preprocessing.py
│   ├── test_claim_extraction.py
│   ├── test_classifier.py
│   ├── test_evidence.py
│   └── test_fusion.py
├── app/
│   └── streamlit_app.py        # Streamlit UI
├── configs/
│   ├── model_config.yaml       # Hyperparameters
│   ├── fusion_config.yaml      # Fusion weights
│   └── slang_dict.json         # Slang normalization
├── requirements.txt
├── README.md
└── ARsitektur.md               # Dokumen ini
```

---

## 9. API Specification

### 9.1 Endpoint Utama

```
POST /api/v1/check
```

**Request:**

```json
{
  "title": "Vaksin Menyebabkan Gagal Ginjal Massal",
  "content": "Menurut informasi yang beredar, vaksin yang diberikan pemerintah menyebabkan gagal ginjal massal di Indonesia...",
  "url": "https://contoh.com/artikel",
  "source": "user_input"
}
```

**Response:**

```json
{
  "status": "success",
  "data": {
    "verdict": "Hoax",
    "confidence": 0.86,
    "risk_level": "High",
    "article_summary": "Artikel mengandung klaim yang dibantah oleh sumber kredibel.",
    "claims": [
      {
        "claim_id": 1,
        "claim_text": "Vaksin menyebabkan gagal ginjal massal",
        "verdict": "Hoax",
        "confidence": 0.86,
        "reasoning": "Klaim dibantah oleh Kemenkes...",
        "evidence_sources": [
          { "name": "Kemenkes RI", "url": "https://..." }
        ]
      }
    ],
    "recommendation": "Informasi ini mengandung klaim yang tidak benar.",
    "processing_time_ms": 3450
  }
}
```

### 9.2 Endpoint Lainnya

```
GET  /api/v1/evidence/search?q={query}&limit=5
     → Cari evidence manual

GET  /api/v1/stats
     → Statistik sistem (total check, akurasi, dll)

POST /api/v1/feedback
     → Kirim feedback untuk perbaikan model
     {
       "check_id": "...",
       "correct_verdict": "Tidak Hoax",
       "reason": "Klaim ini sebenarnya benar karena..."
     }
```

---

## 10. Design Decisions & Justifikasi

| Keputusan | Alasan |
|---|---|
| **Hybrid bukan single model** | Tidak ada satu model yang sempurna — LSTM lemah di evidence, LLM bisa halusinasi, evidence saja tidak cukup untuk stylistic patterns |
| **Claim-based bukan article-based** | Hoax detection yang benar itu verifikasi klaim individual, bukan classify seluruh artikel sekaligus |
| **IndoBERT > BiLSTM sebagai primary** | Transformer terbukti lebih kuat untuk Bahasa Indonesia; BiLSTM tetap sebagai baseline akademis |
| **3 label bukan 2** | Binary terlalu agresif; "Tidak Cukup Bukti" lebih aman dan ilmiah |
| **Weighted fusion bukan voting** | Evidence lebih penting dari pattern linguistik — perlu bobot berbeda |
| **Article verdict = jika 1+ hoax → hoax** | Konservatif — satu klaim salah sudah cukup untuk menandai seluruh artikel |
| **Hybrid BM25 + Semantic** | BM25 tangkap exact match, semantic tangkap makna — kombinasi lebih robust |
| **LLM dikunci dengan prompt constraint** | Mencegah halusinasi — LLM hanya boleh pakai evidence yang diberikan |

---

## 11. Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Dataset tidak cukup | Model underfit | Augmentasi data, transfer learning, scraping lebih banyak |
| Evidence database kosong | Sistem tidak bisa verifikasi | Mulai dari TurnBackHoax (sudah ada), expand bertahap |
| LLM mahal / rate limit | Biaya operasional tinggi | Cache LLM response, gunakan model kecil (mini), fallback ke local LLM |
| False positive tinggi | Berita valid salah diklasifikasi | Threshold tuning, feedback loop, human review |
| Bahasa slang tidak ter-cover | Preprocessing gagal | Perbaiki slang dictionary iteratif, fine-tune dengan data sosial media |
| Hoax baru yang belum ada di database | Evidence retrieval gagal | Label "Tidak Cukup Bukti", bukan langsung "Hoax" |

---

## 12. Kalimat untuk Paper / Skripsi

> "Penelitian ini mengembangkan sistem deteksi hoaks berbahasa Indonesia berbasis hybrid deep learning dan LLM-assisted fact checking. Model IndoBERT dan BiLSTM digunakan untuk klasifikasi pola linguistik per klaim, sedangkan Large Language Model digunakan untuk ekstraksi klaim dan penjelasan berbasis evidence retrieval. Keputusan final ditentukan melalui weighted decision fusion yang menggabungkan probabilitas model deep learning, skor evidence retrieval, kredibilitas sumber, dan ciri stilistik teks. Sistem ini dirancang untuk mengatasi keterbatasan klasifikasi teks tradisional dengan menambahkan verifikasi berbasis bukti pada setiap klaim yang terdeteksi."
