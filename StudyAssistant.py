# StudyAssistant_Pro2.py
# AI STUDY ASSISTANT (Pro)
# Lead: Sandesh Raj | Team InnoVision | Technova Hackathon 2025
# Pure-Python Streamlit app — single input -> smart Summary / Questions / MCQ Quiz / Flashcards

import streamlit as st
import re, random, textwrap
from collections import Counter

# Optional PDF support
try:
    from PyPDF2 import PdfReader
    _PDF_AVAILABLE = True
except Exception:
    _PDF_AVAILABLE = False

# ---------- Page config ----------
st.set_page_config(page_title="AI STUDY ASSISTANT", page_icon="🎓", layout="wide")

# ---------- Header ----------
st.title("🎓 AI STUDY ASSISTANT")
st.caption("Single input → Smart Summary, Domain-aware Questions, Creative MCQs & Editable Flashcards")
st.markdown("---")

# ---------- Sidebar input ----------
st.sidebar.header("📥 Input (paste or upload)")
text_input = st.sidebar.text_area("Paste your notes or a topic paragraph here:", height=240)
uploaded_file = st.sidebar.file_uploader("Upload .txt or .pdf (optional)", type=["txt", "pdf"])
if uploaded_file and uploaded_file.name.lower().endswith(".pdf") and not _PDF_AVAILABLE:
    st.sidebar.error("Install PyPDF2 to enable PDF uploads: pip install PyPDF2")

def read_uploaded(u):
    if not u:
        return ""
    name = u.name.lower()
    try:
        if name.endswith(".txt") or u.type == "text/plain":
            raw = u.read()
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="ignore")
            return str(raw)
        if name.endswith(".pdf") and _PDF_AVAILABLE:
            reader = PdfReader(u)
            pages = []
            for p in reader.pages:
                txt = p.extract_text()
                if txt:
                    pages.append(txt)
            return "\n".join(pages)
    except Exception:
        return ""
    return ""

if uploaded_file:
    file_text = read_uploaded(uploaded_file)
    if file_text:
        text_input = file_text

# ---------- Utilities ----------
def clean_text(t):
    if not t:
        return ""
    t = re.sub(r'\r\n', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def split_sentences(t):
    if not t:
        return []
    s = re.split(r'(?<=[.!?])\s+', t)
    return [seg.strip() for seg in s if seg.strip()]

# Prefer complex / domain-looking words (length + rarity)
COMMON_WORDS = set(["about","which","their","there","these","those","other","using","between","through","under","within","where","while","about","that","this","study","learning","and","the","for","with","is","are","was","be","to","of","in","on","a","an","by"])

# Extra generic/common words to avoid as focus keywords
EXTRA_COMMON_WORDS = set([
    "understanding","application","applications","programming","example","examples","concept","important",
    "system","data","process","model","design","method","methods","results","result","approach","approaches",
    "analysis","study","paper","introduction","conclusion","overview","entertainment","movie","music","games",
    "sport","sports","news","people","person","thing","things","time","day","week","month","year","life",
    "world","social","general","basic","simple","note","notes"
])

def score_keyword(word, text):
    # score longer words, rarer, and frequency-weighted
    base = len(word)
    freq = text.lower().count(word.lower())
    # penalize very common short words
    bonus = 0
    if re.search(r'[A-Z]', word):  # maybe acronym
        bonus += 2
    return base * (1 + 0.3*freq) + bonus

def extract_candidate_keywords(text, n=12):
    # extract alpha/compound tokens
    tokens = re.findall(r'\b[A-Za-z][A-Za-z0-9\-/+]{4,}\b', text)
    # filter trivial/common
    tokens = [t for t in tokens if t.lower() not in COMMON_WORDS and t.lower() not in EXTRA_COMMON_WORDS and len(t) >= 5]
    # dedupe preserving order
    seen = set(); uniq = []
    for t in tokens:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    # technical preference
    difficult_suffixes = (
        "ology","ologies","itis","ase","osis","graphy","metry","dynamics","statics",
        "lysis","genic","phobic","philia","ectomy","emia","algia","pathy","morphism","morphic",
        "synthesis","kinetics","quantum","neural"
    )
    def looks_technical(wl, w):
        return (
            len(w) >= 7 or '-' in w or '/' in w or w.isupper() or any(wl.endswith(s) for s in difficult_suffixes)
        )
    # score and pick with filtering
    scored = sorted(uniq, key=lambda w: score_keyword(w, text), reverse=True)
    filtered = []
    for w in scored:
        wl = w.lower()
        if wl in EXTRA_COMMON_WORDS:
            continue
        if looks_technical(wl, w):
            filtered.append(w)
        if len(filtered) >= n:
            break
    # fallback if too strict
    if not filtered:
        filtered = scored[:n]
    return filtered[:n]

# Simple domain detection using keyword lists
CODING_HINTS = {"function","variable","class","algorithm","array","loop","compile","python","java","c++","javascript","pointer","memory","recursion","api","server","client","database"}
MEDICAL_HINTS = {"diagnosis","symptom","disease","therapy","virus","bacteria","pharmacology","cardiac","neural","oncology","pathology","surgery","vaccine","antibiotic","tumor","metastasis","PCR","imaging"}
SCIENCE_HINTS = {"quantum","electron","molecule","thermodynamics","entropy","gravity","cell","photosynthesis","enzyme","reaction","synthesis"}

def detect_domain(text):
    text_l = text.lower()
    c = sum(1 for h in CODING_HINTS if h in text_l)
    m = sum(1 for h in MEDICAL_HINTS if h in text_l)
    s = sum(1 for h in SCIENCE_HINTS if h in text_l)
    # domain priority: coding > medical > science > generic
    if c >= 2:
        return "coding"
    if m >= 2:
        return "medical"
    if s >= 2:
        return "science"
    return "generic"

# ---------- Templates (many, domain-aware) ----------
GENERIC_TEMPLATES = [
    "Summarize the role of '{k}' in the context of this passage.",
    "Why is '{k}' considered important in this topic?",
    "Provide a practical example that demonstrates '{k}'.",
    "What challenges are associated with '{k}' and how can they be mitigated?",
    "How does '{k}' relate to other major concepts mentioned here?",
    "Propose one recommendation to improve outcomes related to '{k}'.",
    "Explain how '{k}' has evolved historically and its current relevance."
]

CODING_TEMPLATES = [
    "Explain how the concept '{k}' affects software design or performance.",
    "Write a short example (in words) showing '{k}' in code or algorithmic context.",
    "What trade-offs are involved when using '{k}' in system implementation?",
    "How would you debug or test issues related to '{k}'?",
    "Compare '{k}' with a related programming concept and state the key difference.",
    "Describe a real-world application where '{k}' improves system behavior."
]

MEDICAL_TEMPLATES = [
    "Define '{k}' clinically and describe its diagnostic significance.",
    "Describe one treatment or management strategy related to '{k}'.",
    "What are common complications or concerns associated with '{k}'?",
    "How would you explain the importance of '{k}' to a patient in simple terms?",
    "Compare '{k}' with a related medical concept and outline differences.",
    "Suggest a basic diagnostic approach or test for '{k}'."
]

SCIENCE_TEMPLATES = [
    "Explain the underlying principle of '{k}' and its significance in this field.",
    "Describe an experiment or observation that demonstrates '{k}'.",
    "What are the main factors that influence '{k}' in this context?",
    "How does '{k}' interact with other scientific concepts discussed here?",
    "Outline practical applications of '{k}' in technology or research."
]

# MCQ distractor templates
DISTRACTOR_PATTERNS = [
    "{} is mainly an example or case, not the core concept.",
    "{} commonly refers to a method rather than the concept itself.",
    "{} often denotes an effect or result, not the definition.",
    "{} is a related concept but not correct in this context."
]

def create_question_templates(domain):
    if domain == "coding":
        return CODING_TEMPLATES + GENERIC_TEMPLATES
    if domain == "medical":
        return MEDICAL_TEMPLATES + GENERIC_TEMPLATES
    if domain == "science":
        return SCIENCE_TEMPLATES + GENERIC_TEMPLATES
    return GENERIC_TEMPLATES

# ---------- Generators ----------
def generate_summary(text):
    if not text:
        return "", ""
    keywords = extract_candidate_keywords(text, n=6)
    if not keywords:
        keywords = ["concept", "principle", "application"]
    main = keywords[0]
    context = ", ".join(keywords[1:4])

    summary = (
        f"The passage explores the idea of **{main}**, focusing on how it shapes understanding and practice. "
        f"It connects {main} with {context}, showing their relevance in real-world learning. "
        f"The explanation builds clarity by relating each idea to familiar examples, helping learners link theory with practice. "
        f"In essence, {main} acts as the foundation that supports deeper insight into the overall topic."
    )
    insight = f"Focus on how {main} relates to {context} — it often forms the key link for exam answers."
    return textwrap.fill(summary, 100), insight


def extract_main_ideas(text, n=4):
    # Use frequency and position to find main ideas
    sentences = split_sentences(text)
    if not sentences:
        return []
    # Score sentences by length and position (first sentences are often important)
    scored = sorted(
        [(i, s, len(s.split())) for i, s in enumerate(sentences)],
        key=lambda x: (x[2] + max(0, 10 - x[0])), reverse=True
    )
    # Take top n sentences as main ideas
    main_ideas = [s for i, s, l in scored[:n]]
    return main_ideas

def extract_good_keywords(text, n=8):
    # Use frequency and ignore common/stop words, but also check for capitalized terms
    words = re.findall(r'\b[A-Za-z][A-Za-z0-9\-/+]{3,}\b', text)
    freq = Counter([w.lower() for w in words if w.lower() not in COMMON_WORDS])
    # Prefer capitalized or mid-text capital words (proper nouns, technical terms)
    capitalized = [w for w in set(words) if w[0].isupper() and w.lower() not in COMMON_WORDS]
    # Combine frequency and capitalized
    ranked = [w for w, c in freq.most_common(n*2) if w not in capitalized]
    result = capitalized + ranked
    # Remove duplicates, keep order
    seen = set()
    filtered = []
    for w in result:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            filtered.append(w)
        if len(filtered) >= n:
            break
    return filtered

def extract_context_patterns(text: str):
    """Lightweight extraction of study-useful patterns from raw text.
    Returns dict: definitions, causes, contrasts, examples, enumerations, processes.
    """
    sentences = split_sentences(text)
    definitions = []   # (term, definition)
    causes = []        # (cause, effect)
    contrasts = []     # (a, b)
    examples = []      # (topic, item)
    enumerations = []  # (topic, [items])
    processes = []     # (label, [steps])

    # Definitions patterns
    for s in sentences:
        m = re.match(r"\s*([A-Z]?[A-Za-z0-9\-/ ]{3,})\s+(is|are|refers to|means)\s+(.*?)[\.]?$", s)
        if m:
            term = m.group(1).strip()
            defin = m.group(3).strip()
            if len(term) >= 2 and len(defin) >= 5:
                definitions.append((term, defin))

    # Cause/effect patterns
    cause_regexes = [
        r"(.*?)\s+(causes|leads to|results in|triggers)\s+(.*)",
        r"(.*?)\s+because\s+(.*)",
        r"(.*?)\s+therefore\s+(.*)",
        r"(.*?)\s+so\s+(.*)",
    ]
    for s in sentences:
        for pat in cause_regexes:
            m = re.search(pat, s, flags=re.IGNORECASE)
            if m:
                left = m.group(1).strip(' ,;:.')
                right = m.group(m.lastindex).strip(' ,;:.') if m.lastindex else ''
                if left and right and len(left) > 2 and len(right) > 2:
                    causes.append((left, right))
                    break

    # Contrasts
    for s in sentences:
        m = re.search(r"(.*?)(?:;\s*however,\s*|\s+but\s+|\s+whereas\s+)(.*)", s, flags=re.IGNORECASE)
        if m:
            a = m.group(1).strip(' ,;:.')
            b = m.group(2).strip(' ,;:.')
            if a and b:
                contrasts.append((a, b))

    # Examples
    for s in sentences:
        m = re.search(r"(.*?)(such as|for example|e\.g\.?|including)\s+(.*)", s, flags=re.IGNORECASE)
        if m:
            topic = m.group(1).strip(' ,;:.')
            rest = m.group(3)
            items = [x.strip() for x in re.split(r",|;| and ", rest) if x.strip()]
            for it in items:
                if topic and it:
                    examples.append((topic, it))

    # Enumerations: topic: item1, item2, ...
    for s in sentences:
        if ':' in s and ',' in s:
            topic, after = s.split(':', 1)
            items = [x.strip() for x in re.split(r",|;| and ", after) if len(x.strip()) >= 2]
            if topic.strip() and len(items) >= 2:
                enumerations.append((topic.strip(), items[:6]))

    # Processes: detect numbered steps on separate lines
    numbered = re.findall(r"(?m)^(\d+)[\).]\s*([A-Za-z].+)$", text)
    if numbered:
        steps = [x[1].strip() for x in numbered][:6]
        processes.append(("Steps", steps))

    return {
        "definitions": definitions,
        "causes": causes,
        "contrasts": contrasts,
        "examples": examples,
        "enumerations": enumerations,
        "processes": processes,
    }

def generate_gpt_style_questions(text, count=6):
    """
    Generate diverse, context-aware, exam-style questions from the input text.
    """
    if not text or len(text.strip()) < 20:
        return ["Provide more content to generate meaningful questions."], []

    main_ideas = extract_main_ideas(text, n=3)
    keywords = extract_good_keywords(text, n=8)
    patterns = extract_context_patterns(text)
    sentences = split_sentences(text)
    questions = []
    used = set()

    # Question templates, but more dynamic and context-aware
    def q_define(term): return f"What is '{term}'? Explain in your own words."
    def q_significance(term): return f"Why is '{term}' significant in the context of this topic?"
    def q_application(term): return f"Describe a real-world application or example of '{term}'."
    def q_compare(term1, term2): return f"Compare and contrast '{term1}' and '{term2}'."
    def q_explain_sentence(sent): return f"Explain the meaning of the following statement: \"{sent}\""
    def q_process(term): return f"Describe the process or steps involved in '{term}'."
    def q_problem(term): return f"What problems or challenges are associated with '{term}'?"
    def q_why(sent): return f"Why is the following point important: \"{sent}\""
    def q_how(term): return f"How does '{term}' contribute to the overall understanding of the topic?"

    # Priority 1: pattern-based questions for deeper understanding
    for term, defin in patterns.get("definitions", [])[:2]:
        q = f"Define '{term}' in simple terms and give one key point."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords
    for cause, effect in patterns.get("causes", [])[:2]:
        q = f"How does '{cause}' lead to '{effect}'? Explain the reasoning."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords
    for a, b in patterns.get("contrasts", [])[:2]:
        q = f"Contrast '{a}' and '{b}' with one real-world difference."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords
    for topic, ex in patterns.get("examples", [])[:2]:
        q = f"Give two examples of '{topic}' and state why they fit."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords
    for topic, items in patterns.get("enumerations", [])[:1]:
        q = f"List three items under '{topic}' and explain each in one line."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords
    for label, steps in patterns.get("processes", [])[:1]:
        q = f"Outline the main steps of the process and the goal of each step."
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords

    # Priority 2: main idea prompts
    for sent in main_ideas:
        q = q_explain_sentence(sent) if len(questions) % 2 == 0 else q_why(sent)
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords

    # Priority 3: keyword-based diverse prompts
    qtypes = [q_define, q_significance, q_application, q_process, q_problem, q_how]
    for i, term in enumerate(keywords):
        q = qtypes[i % len(qtypes)](term)
        if q not in used:
            questions.append(q); used.add(q)
            if len(questions) >= count: return questions, keywords

    # Fallbacks
    while len(questions) < count:
        q = "Summarize the main points of the passage in your own words."
        if q not in used:
            questions.append(q); used.add(q)
        else:
            break

    return questions, keywords

def generate_mcqs(text, min_q=5):
    # determine number of questions: at least min_q, increase with content length
    words = extract_candidate_keywords(text, n=20)
    num = max(min_q, min(12, max(0, len(words)//2)))
    domain = detect_domain(text)
    templates = create_question_templates(domain)
    mcqs = []
    keys = words[:num]
    if not keys:
        keys = ["ConceptA","ConceptB","ConceptC","ConceptD","ConceptE"]
    for key in keys:
        question = random.choice(templates).format(k=key)
        # correct answer: short context-based line
        correct = f"{key} refers to a central concept that explains an important idea or role in this topic."
        # build distractors
        pool = [k for k in keys if k != key]
        wrongs = []
        # smart distractor 1: pattern with key (but wrong)
        wrongs.append(DISTRACTOR_PATTERNS[0].format(key))
        # distractor 2: use random other key if available
        if pool:
            other = random.choice(pool)
            wrongs.append(f"{other} — a related term that may be confused with {key}.")
        else:
            wrongs.append(DISTRACTOR_PATTERNS[1].format(key))
        # distractor 3: generic misleading statement
        wrongs.append(DISTRACTOR_PATTERNS[2].format(key))
        options = [correct] + wrongs
        # make sure all options are distinct
        unique_opts = []
        for o in options:
            o = o.strip()
            if o not in unique_opts:
                unique_opts.append(o)
        # if less than 4 unique, add filler
        fillers = ["A specific example rather than a definition.", "A method or procedure unrelated to the concept."]
        while len(unique_opts) < 4:
            unique_opts.append(fillers.pop(0))
        random.shuffle(unique_opts)
        mcqs.append({
            "question": question,
            "options": unique_opts,
            "answer": correct,
            "concept": key
        })
    return mcqs

def generate_exam_style_mcqs(text, min_q=5):
    """
    Generate MCQs that are more exam-relevant, using main ideas and good keywords.
    """
    main_ideas = extract_main_ideas(text, n=5)
    keywords = extract_good_keywords(text, n=10)
    patterns = extract_context_patterns(text)
    mcqs = []
    used_questions = set()
    used_terms = set()
    # Question stems
    stems = [
        lambda k, s: f"What is the best definition of '{k}'?",
        lambda k, s: f"Which statement best describes the significance of '{k}'?",
        lambda k, s: f"In the context of the passage, what is a key application of '{k}'?",
        lambda k, s: f"Which of the following is most accurate about '{k}'?",
        lambda k, s: f"Based on the passage, which is true regarding '{k}'?",
        lambda k, s: f"According to the text, what is a challenge related to '{k}'?",
        lambda k, s: f"Which option best explains the following statement: \"{s}\"",
    ]
    # Helper to build plausible, professional distractors
    def make_distractors(correct: str, keyword: str, pool_terms, pool_ideas, needed=3):
        d = []
        # 1) Partial truth but incomplete
        d.append(f"{keyword}: a related aspect mentioned indirectly, but not the full meaning.")
        # 2) Confuser using another term
        if pool_terms:
            d.append(f"{random.choice(pool_terms)} — closely related but not the same as {keyword}.")
        # 3) Opposite/negation or common misconception
        d.append(f"A common misconception about {keyword}, not supported by the passage.")
        # 4) Borrow a different main idea snippet
        if pool_ideas:
            idea = pool_ideas[0]
            d.append(idea if len(idea) < 120 else idea[:117] + "...")
        # Trim to needed count and ensure uniqueness
        uniq = []
        for x in d:
            if x and x != correct and x not in uniq:
                uniq.append(x)
        return uniq[:needed]

    # 1) Definition-based MCQs
    for term, defin in patterns.get("definitions", [])[:2]:
        q = f"Which option best defines '{term}'?"
        if q in used_questions: continue
        used_questions.add(q)
        correct = defin if len(defin) <= 140 else defin[:137] + "..."
        pool_terms = [t for t, _ in patterns.get("definitions", []) if t != term]
        pool_ideas = main_ideas
        distractors = make_distractors(correct, term, pool_terms, pool_ideas, needed=3)
        options = [correct] + distractors[:3]
        random.shuffle(options)
        mcqs.append({"question": q, "options": options, "answer": correct, "concept": term})
        if len(mcqs) >= min_q: return mcqs

    # 2) Cause-effect MCQs
    for cause, effect in patterns.get("causes", [])[:2]:
        q = f"According to the passage, '{cause}' most directly leads to which outcome?"
        if q in used_questions: continue
        used_questions.add(q)
        correct = effect
        distractors = make_distractors(correct, cause, keywords, main_ideas, needed=3)
        options = [correct] + distractors
        random.shuffle(options)
        mcqs.append({"question": q, "options": options, "answer": correct, "concept": cause})
        if len(mcqs) >= min_q: return mcqs

    # 3) Contrast MCQs
    for a, b in patterns.get("contrasts", [])[:2]:
        q = f"Which option correctly distinguishes '{a}' from '{b}'?"
        if q in used_questions: continue
        used_questions.add(q)
        correct = f"{a} differs from {b} in purpose or behavior as described."
        distractors = make_distractors(correct, f"{a} vs {b}", keywords, main_ideas, needed=3)
        options = [correct] + distractors
        random.shuffle(options)
        mcqs.append({"question": q, "options": options, "answer": correct, "concept": f"{a} vs {b}"})
        if len(mcqs) >= min_q: return mcqs

    # 4) Enumeration MCQs
    for topic, items in patterns.get("enumerations", [])[:1]:
        q = f"Which of the following is listed as part of '{topic}' in the passage?"
        if q in used_questions: continue
        used_questions.add(q)
        correct = items[0]
        distractors = items[1:3]
        while len(distractors) < 3:
            distractors.append("A plausible but unlisted item from the same category")
        options = [correct] + distractors[:3]
        random.shuffle(options)
        mcqs.append({"question": q, "options": options, "answer": correct, "concept": topic})
        if len(mcqs) >= min_q: return mcqs

    # 5) Fallback: main-idea/keyword based
    for i in range(max(min_q, 5)):
        k = keywords[i] if i < len(keywords) else (keywords[0] if keywords else "the main concept")
        s = main_ideas[i] if i < len(main_ideas) else ""
        stem = stems[i % len(stems)]
        question = stem(k, s) if s else stem(k, "")
        if question in used_questions: continue
        used_questions.add(question)
        correct = (f"{k}: {s[:80]}..." if s and len(s) > 80 else (f"{k}: {s}" if s else f"{k} is a key concept discussed."))
        distractors = [f"{k} is unrelated to the topic.", f"{k} is not mentioned.", f"{k} means the opposite."]
        options = [correct] + distractors
        random.shuffle(options)
        mcqs.append({"question": question, "options": options, "answer": correct, "concept": k})
        if len(mcqs) >= min_q: break
    return mcqs

# ---------- Flashcards ----------
def default_flashcards(text, n=5):
    # Start with neutral placeholders so user decides the content
    return [{"term": f"Topic {i+1}", "definition": "Add your own definition.", "note": ""} for i in range(n)]

# ---------- Session State ----------
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "mcq_sel" not in st.session_state:
    st.session_state.mcq_sel = {}   # idx -> selection
if "mcqs_cache" not in st.session_state:
    st.session_state.mcqs_cache = []
if "mcq_submitted" not in st.session_state:
    st.session_state.mcq_submitted = False
if "last_text" not in st.session_state:
    st.session_state.last_text = ""

content = clean_text(text_input)
if content and content != st.session_state.last_text:
    st.session_state.mcq_sel = {}
    st.session_state.mcq_submitted = False
    st.session_state.last_text = content
    st.session_state.flashcards = default_flashcards(content, n=5)
    # regenerate MCQs once per content to keep options stable across reruns
    st.session_state.mcqs_cache = generate_exam_style_mcqs(content, min_q=5)

# ---------- Main UI ----------
if not content:
    st.info("Paste or upload notes (txt/pdf) in the left sidebar. The app will generate Summary, Questions, MCQs and Flashcards from the same content.")
else:
    st.success("Content loaded — generating outputs...")
    st.markdown("---")

    tabs = st.tabs(["🧠 Summary", "❓ Questions", "📝 Quiz (MCQs)", "🎴 Flashcards"])

    # SUMMARY
    with tabs[0]:
        st.header("🧠 Smart Summary")
        summary, insight = generate_summary(content)
        st.subheader("Summary")
        st.write(summary)
        st.info(f"Insight: {insight}")
        kws = extract_candidate_keywords(content, n=8)
        if kws:
            st.write("Top candidate keywords:", ", ".join(kws))

    # QUESTIONS (varied)
    with tabs[1]:
        st.header("❓ GPT-Style Exam Questions")
        qlist, keys = generate_gpt_style_questions(content, count=6)
        st.write("These questions are generated in a GPT-style, focusing on exam relevance and deeper understanding.")
        for i, q in enumerate(qlist, 1):
            st.markdown(f"**Q{i}.** {q}")

    # ---------- QUIZ ----------
    with tabs[2]:
        st.header("📝 Exam-Style MCQ Quiz")
        st.write("Attempt each question by selecting the most appropriate answer. Press **Submit** to check your score.")

        # Use cached MCQs to avoid option reshuffle on reruns
        if not st.session_state.mcqs_cache:
            st.session_state.mcqs_cache = generate_exam_style_mcqs(content, min_q=5)
        mcqs = st.session_state.mcqs_cache

        for idx, item in enumerate(mcqs):
            st.markdown(f"**Q{idx+1}.** {item['question']}")

            # Keep a stable option order; no reshuffle on rerun
            options = item.get("options", []).copy() or ["No options available"]

            # Ensure no default selection: include placeholder at top, persist user choice
            placeholder = "— Select an answer —"
            options_with_placeholder = [placeholder] + options
            current = st.session_state.mcq_sel.get(idx, placeholder)
            sel = st.selectbox("", options_with_placeholder, index=options_with_placeholder.index(current) if current in options_with_placeholder else 0, key=f"mcq_{idx}")

            st.session_state.mcq_sel[idx] = sel
            st.markdown("")

        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("Submit"):
                st.session_state.mcq_submitted = True
        with c2:
            if st.button("Reset Quiz"):
                st.session_state.mcq_sel = {}
                st.session_state.mcq_submitted = False
                st.experimental_rerun()

        if st.session_state.mcq_submitted:
            total = len(mcqs)
            score = 0
            st.markdown("---")
            st.subheader("Results")
            for i, item in enumerate(mcqs):
                chosen = st.session_state.mcq_sel.get(i, None)
                correct = item["answer"]
                st.markdown(f"**Q{i+1}.** {item['question']}")
                if chosen == correct:
                    st.success(f"Your answer: {chosen} — ✅ Correct")
                    score += 1
                else:
                    if not chosen:
                        st.warning("No selection made.")
                    else:
                        st.error(f"Your answer: {chosen} — ❌ Incorrect")
                    st.info(f"✔ Correct answer: {correct}")
                st.markdown("")
            st.info(f"**Final Score: {score} / {total}**")



    # FLASHCARDS
    with tabs[3]:
        st.header("🎴 Flashcards — Edit & Add")
        if not st.session_state.flashcards:
            st.session_state.flashcards = default_flashcards(content, n=5)

        left, right = st.columns([1, 2])
        with left:
            st.subheader("Cards")
            for i, c in enumerate(st.session_state.flashcards):
                st.write(f"{i+1}. {c['term']}")
            if st.button("Add Flashcard"):
                st.session_state.flashcards.append({"term": f"Topic {len(st.session_state.flashcards)+1}", "definition": "Add your own definition.", "note": ""})
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
            if st.button("Reset Flashcards"):
                st.session_state.flashcards = default_flashcards(content, n=5)
                st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()

        with right:
            st.subheader("Edit / Review")
            for idx, card in enumerate(st.session_state.flashcards):
                with st.expander(f"🔹 {card['term']}", expanded=False):
                    new_term = st.text_input("Term:", value=card.get("term",""), key=f"term_{idx}")
                    new_def = st.text_area("Definition:", value=card.get("definition",""), key=f"def_{idx}", height=90)
                    new_note = st.text_area("Your personal note:", value=card.get("note",""), key=f"note_{idx}", height=80)
                    # save back
                    st.session_state.flashcards[idx]["term"] = new_term.strip() if new_term.strip() else card["term"]
                    st.session_state.flashcards[idx]["definition"] = new_def.strip() if new_def.strip() else card["definition"]
                    st.session_state.flashcards[idx]["note"] = new_note.strip()
                    c1, c2, c3 = st.columns([1,1,1])
                    if c1.button("Save", key=f"save_{idx}"):
                        st.success("Saved in session.")
                    if c2.button("Delete", key=f"del_{idx}"):
                        st.session_state.flashcards.pop(idx)
                        st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
                    if c3.button("Mark Reviewed", key=f"rev_{idx}"):
                        st.info(f"Marked '{st.session_state.flashcards[idx]['term']}' as reviewed.")

# ---------- Footer ----------
st.markdown("---")
st.caption("Developed by Sandesh Raj | Team InnoVision | Technova Hackathon 2025")
