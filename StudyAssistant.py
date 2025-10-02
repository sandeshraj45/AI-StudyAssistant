import streamlit as st
import random
import re

# 🔹 Stopwords list (for cleaning)
stopwords = {"is", "the", "and", "a", "of", "to", "in", "on", "for", "with"}

# 🔹 Extract keywords function
def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text)  # only words
    keywords = [w.capitalize() for w in words if w.lower() not in stopwords]
    return list(set(keywords))  # unique only

# 🔹 Generate questions
def generate_questions(keywords):
    return [f"What do you know about {kw}?" for kw in keywords]

# 🔹 Create MCQs
def generate_mcqs(keywords):
    mcqs = []
    for kw in keywords:
        options = [kw, "Sports", "Food", "Random"]
        random.shuffle(options)
        mcqs.append((kw, options))
    return mcqs

# 🔹 Simple summary (just keywords for now)
def generate_summary(keywords):
    return "Key points: " + ", ".join(keywords)

# 🔹 Streamlit UI
st.set_page_config(page_title="AI Study Assistant", layout="wide")
st.title("📚 AI Study Assistant for Students")

st.sidebar.header("✍️ Input Notes")
text_input = st.sidebar.text_area("Paste your notes here:")
file_upload = st.sidebar.file_uploader("Or upload a .txt file", type=["txt"])

# If file uploaded, read it
if file_upload:
    text_input = file_upload.read().decode("utf-8")

if text_input:
    # Process input
    keywords = extract_keywords(text_input)

    st.subheader("📌 Extracted Keywords")
    st.write(keywords)

    # Tabs for features
    tab1, tab2, tab3, tab4 = st.tabs(["Questions", "Quiz", "Flashcards", "Summary"])

    with tab1:
        st.subheader("📖 Generated Questions")
        for q in generate_questions(keywords):
            st.write("•", q)

    with tab2:
        st.subheader("📝 Quiz Mode")
        score = 0
        mcqs = generate_mcqs(keywords[:5])  # limit 5 questions
        for i, (kw, options) in enumerate(mcqs, 1):
            ans = st.radio(f"Q{i}: {kw} is related to?", options, key=i)
            if ans == kw:
                score += 1
        st.success(f"✅ Your Score: {score}/{len(mcqs)}")

    with tab3:
        st.subheader("📘 Flashcards")
        for i, kw in enumerate(keywords[:5], 1):
            with st.expander(f"Flashcard {i}: {kw}"):
                st.write(f"Definition/Notes about {kw} (add explanation here)")

    with tab4:
        st.subheader("⚡ Quick Summary")
        st.info(generate_summary(keywords))
