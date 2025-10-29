# ING Personal Voice Assistant ("Leo")

This project is a **proof-of-concept** for the **ING Challenge at the AI Accelerate Hack (October 2025)**.  
It is a **voice-first personal banking assistant**, "Leo," that provides **secure, personalized, and accurate** answers to customer questions.

The core of the project is a sophisticated **Retrieval-Augmented Generation (RAG)** pipeline combined with a **hybrid calculation toolkit**.  
This design ensures **mathematical accuracy** (which LLMs struggle with) and **prevents hallucinations**, providing a trustworthy user experience.

---

## ✨ Core Features

- **Voice-first Interface:**  
  Users interact by voice. The app uses **Google's high-quality Speech-to-Text (STT)** and **Text-to-Speech (TTS)** for natural-sounding conversations.

- **Multilingual Support:**  
  Works with **English (en)**, **French (fr)**, and **Dutch (nl)**, as required by the challenge.

- **Deep Personalization:**  
  Answers are personalized using a **synthetic dataset** of customer profiles, active products, and transaction histories.

- **Hybrid Calculation Engine:**  
  Detects math-related queries (e.g., "How much did I spend on groceries?") and performs the calculations in **Python** before sending the factual result to the LLM — eliminating mathematical hallucinations.

- **Anti-Hallucination & Safety:**  
  A strict **MASTER_PROMPT** enforces strong rules, ensuring:
  - The LLM only answers from the provided context.
  - User privacy is maintained.
  - Escalation to a human agent when necessary.

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|-------------|
| **Frontend** | Streamlit |
| **Backend & Orchestration** | Python, LangChain (principles) |
| **Generative AI** | Google Gemini API |
| **Speech Services** | Google Cloud Speech-to-Text, Google Cloud Text-to-Speech |
| **Data Retrieval** | ChromaDB (Persistent Vector Database) |
| **Data Handling** | Pandas |

---

## 🏗️ Project Architecture

The system is designed for **safety, accuracy, and contextual awareness**.

1. **Input (Speech):**  
   The user records a question in the Streamlit app.

2. **STT (Google):**  
   The audio is converted to text.

3. **Backend (ing_assistant.py):**
   - **Router (`route_query`)**  
     Checks if the query involves calculations (e.g., "how much," "total," "sum").
   - **Python Toolkit (if needed)**  
     For numeric tasks, runs a Python function (e.g., `get_total_spending`) on Pandas DataFrames to get accurate results.
   - **RAG Pipeline (always):**  
     - **Personal Context:**  
       `retrieve_personal_context` fetches user profiles, accounts, and transactions from `customers_df`, `products_df`, and `transactions_df`.  
     - **Public Context:**  
       `retrieve_public_context` embeds the user query and searches the **ChromaDB** vector store for relevant public ING info.
   - **Prompt Assembly:**  
     Combines Personal + Public Context + Calculation results into the **MASTER_PROMPT**.
   - **LLM (Gemini):**  
     The **Gemini API** generates the final, factual response.

4. **TTS (Google):**  
   Converts the answer into natural-sounding speech.

5. **Output (UI):**  
   Displays both text and a playable “voice note” (`st.audio`) in Streamlit.

---

## ⚙️ Setup & Installation

### 1. Google Cloud Setup (for Speech)

This project uses **Google Cloud's** STT and TTS services.

- **Enable APIs:**  
  Ensure these APIs are enabled in your project (`involuted-fold-476612-k6`):
  - Cloud Speech-to-Text API  
  - Cloud Text-to-Speech API  

- **Service Account:**  
  Place your `service_account.json` key in the project root (`AIAccHack/`).

- **Set Environment Variable:**
  ```bash
  # macOS/Linux
  export GOOGLE_APPLICATION_CREDENTIALS="service_account.json"

  # Windows (cmd)
  set GOOGLE_APPLICATION_CREDENTIALS=service_account.json
