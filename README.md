# ING Personal Voice Assistant ("Leo")

> **Developed by Team 3** for the **ING Challenge at the AI Accelerate Hack (October 2025)**.

This project is a **proof-of-concept** voice-first personal banking assistant, **"Leo"**, that provides **secure, personalized, and accurate** answers to customer questions.

The core of the project is a sophisticated **Retrieval-Augmented Generation (RAG)** pipeline combined with a **hybrid calculation toolkit**.  
This design ensures **mathematical accuracy** (which LLMs often struggle with) and **prevents hallucinations**, creating a **trustworthy user experience**.

---
# ING Voice Assistant - Technical Summary

## 1. Problem Statement

**Challenge:** Traditional banking support systems rely on rigid IVR menus and keyword-based chatbots that frustrate customers and limit self-service capabilities. Customers must navigate multiple menu levels and cannot ask questions naturally.

**Customer Pain Points:**
- Rigid menu navigation (Press 1 for X, Press 2 for Y...)
- No natural language understanding
- Repetitive authentication steps
- No conversation memory
- Limited query flexibility

**Business Impact:**
- High call center costs (€15-30 per call)
- Low customer satisfaction
- No conversation data for insights
- Limited scalability

## 2. Solution Architecture

### High-Level Architecture
```
┌──────────────────────────────────────────────────────────────┐
│  VOICE INTERFACE (Speech Input/Output)                       │
│  • Google Cloud Speech-to-Text   
│  • Google Cloud Text-to-Speech
└────────────────────┬─────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│  AI LAYER (Natural Language Processing)                      │
│  • Google Gemini 1.5-flash LLM                               │
│  • Category detection (95% accuracy)                         │
│  • Context-aware response generation                         │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│  CHATBOT ROUTING LAYER                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Query Analyzer & Router                            │    │
│  │  • Detect query type (personal data vs knowledge)   │    │
│  │  • Identify functional category from intent         │    │
│  │  • Route to appropriate specialized chatbot         │    │
│  └────────────┬────────────────────────────────────────┘    │
│               │                                               │
│      ┌────────┴────────┬──────────────┬──────────────┐      │
│      ▼                 ▼              ▼              ▼      │
│  ┌────────┐    ┌──────────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Admin  │    │ Daily Banking│  │ Savings │  │  Loans  │ │
│  │Chatbot │    │   Chatbot    │  │ Chatbot │  │ Chatbot │ │
│  │(Personal)   │  (Knowledge) │  │(Knowledge) │(Knowledge)│
│  └───┬────┘    └──────┬───────┘  └────┬────┘  └────┬────┘ │
└──────┼────────────────┼───────────────┼─────────────┼──────┘
       │                │               │             │
       ▼                ▼               ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│              APPLICATION LAYER                                │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  Authentication  │    │ Conversation Mgmt │               │
│  │     System       │    │   & State        │               │
│  └──────────────────┘    └──────────────────┘               │
│         │                        │                            │
│         └────────┬───────────────┘                            │
└──────────────────┼──────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│          DATA LAYER                                           │
│                                                               │
│  ┌──────────────┐  ┌────────────────────────────────────┐  │
│  │  Personal    │  │  Functional Knowledge Databases    │  │
│  │  Banking     │  │                                    │  │
│  │  Database    │  │  ┌──────────────┬──────────────┐  │  │
│  │              │  │  │ Daily Banking│   Savings    │  │  │
│  │ • Customers  │  │  │ • Fees       │ • Accounts   │  │  │
│  │ • Products   │  │  │ • Accounts   │ • Interest   │  │  │
│  │ • Transactions│ │  │ • Payments   │ • Terms      │  │  │
│  │              │  │  └──────────────┴──────────────┘  │  │
│  │              │  │  ┌──────────────┬──────────────┐  │  │
│  │              │  │  │    Loans     │  Insurance   │  │  │
│  │              │  │  │ • Mortgages  │ • Policies   │  │  │
│  │              │  │  │ • Personal   │ • Coverage   │  │  │
│  └──────────────┘  │  └──────────────┴──────────────┘  │  │
│                    │                                    │  │
│  ┌──────────────┐  │  Source: ING website URL chunks   │  │
│  │  Dialogue    │  │  Categorized by URL structure     │  │
│  │  Storage     │  └────────────────────────────────────┘  │
│  └──────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

### Key Components

**1. Voice Processing Pipeline**
- **Input:** Microphone → VAD → STT → Text (200-500ms latency)
- **Output:** Text → TTS → SSML → Audio → Speaker (500-1000ms latency)
- **Quality:** 16kHz sample rate, noise reduction, automatic punctuation

**2. Conversation State Machine**
```
GREETING → IDENTIFY → AUTHENTICATE → VERIFY → 
  PERSONAL_DATA_QUERY → ASK_MORE → END
```

**3. Dialogue Storage System**
- **4 Database Tables:** Conversations, Dialogue Turns, Analytics, Audio Files
- **Real-time Logging:** Every turn stored with metadata (timestamps, confidence scores, intents)
- **Audio Storage:** Cloud storage (GCS/S3) with encryption
- **Retention:** Configurable (30-90 days default, GDPR compliant)

## 3. AI Implementation Details

### Functional Chatbot Routing System

**Concept:** Split knowledge base by URL structure and route queries to specialized chatbots

**URL Structure Analysis:**
```
https://www.ing.be/en/individuals/daily-banking/statement-of-fees
                          ↓            ↓              ↓
                      audience    category        topic
```

**Functional Categories (from URLs):**
- **daily-banking/** → DailyBankingChatbot (fees, accounts, payments)
- **savings/** → SavingsChatbot (savings accounts, interest rates)
- **loans/** → LoansChatbot (mortgages, personal loans)
- **investments/** → InvestmentsChatbot (portfolios, stocks)
- **insurance/** → InsuranceChatbot (policies, coverage)

**Routing Flow:**
```
1. User Query: "What are the fees for international transfers?"
   ↓
2. INTENT DETECTION
   Keywords: "fees", "international", "transfers"
   → Detected Category: daily-banking
   ↓
3. ROUTE TO SPECIALIZED CHATBOT
   → DailyBankingChatbot selected
   ↓
4. KNOWLEDGE BASE SEARCH
   Search in: daily-banking database
   Found: "statement-of-fees" chunk
   ↓
5. CONTEXT BUILDING
   Relevant chunk: International transfer fees section
   URL: .../daily-banking/statement-of-fees
   ↓
6. LLM GENERATION
   Prompt: Use daily-banking knowledge + customer query
   Response: "International transfers cost €12.50 standard..."
```

**Database Structure per Category:**

```python
# Each functional area has its own database
FunctionalDatabases = {
    'daily-banking': {
        'statement-of-fees': KnowledgeEntry(...),
        'current-accounts': KnowledgeEntry(...),
        'payments': KnowledgeEntry(...),
        'cards': KnowledgeEntry(...)
    },
    'savings': {
        'savings-accounts': KnowledgeEntry(...),
        'interest-rates': KnowledgeEntry(...)
    },
    'loans': {
        'home-loans': KnowledgeEntry(...),
        'personal-loans': KnowledgeEntry(...)
    }
}
```



**Example - Multi-Category Query:**
```
Query: "Can I use my savings to pay off my loan?"

1. DETECT MULTIPLE CATEGORIES
   Categories: [savings, loans]

2. ROUTE TO MULTIPLE CHATBOTS
   → SavingsChatbot: Get savings info
   → LoansChatbot: Get loan info

3. AGGREGATE RESPONSES
   Combine answers from both chatbots

4. GENERATE UNIFIED RESPONSE
   "Yes, you can transfer from your Savings Plus 
   account to pay your home loan..."
```

### Google Gemini LLM Integration

**Model:** gemini-1.5-flash
- **Temperature:** 0.3 (consistent, factual responses)
- **Max Tokens:** 2048
- **Top-p:** 0.8 (nucleus sampling)
- **Cost:** ~$0.01 per conversation

### Query Processing Pipeline with Functional Routing

```
1. CATEGORY DETECTION (10ms)
   Input: "What are the fees for international transfers?"
   Analysis: Keywords [fees, international, transfers]
   Output: {category: "daily-banking", confidence: 0.95}

2. CHATBOT ROUTING (5ms)
   Selected: DailyBankingChatbot
   Knowledge Base: daily-banking database (4 chunks)

3. KNOWLEDGE SEARCH (15ms)
   Search in: daily-banking database only
   Query: "fees international transfers"
   Found: statement-of-fees chunk (98% relevance)

4. DATA RETRIEVAL (50ms)
   Personal Data: Customer balance, transaction history
   Knowledge: Fees from statement-of-fees

5. CONTEXT BUILDING (20ms)
   Format: Personal data + Relevant knowledge chunk
   Structure:
   ```
   **CUSTOMER:** John Doe, €17,243.50 total balance
   
   **RELEVANT INFO FROM ING.BE:**
   International Transfers (from daily-banking/statement-of-fees)
   - SEPA zone: Free (online)
   - Outside SEPA (standard): €12.50
   - Outside SEPA (express): €25.00
   ```

6. PROMPT ENGINEERING
   System: "You are ING daily-banking assistant..."
   Context: [personal data + knowledge chunk above]
   Query: "What are the fees for international transfers?"
   Instructions: "Answer using provided info, mention source URL..."

7. LLM GENERATION (1500ms)
   API Call: Gemini with structured prompt
   Response: Natural language answer with source

8. RESPONSE FORMATTING (30ms)
   Add: Currency symbols, source URL, visual elements
   Output: "International transfers cost €12.50 for standard 
           or €25.00 for express delivery outside SEPA zone.
           
           Source: ing.be/daily-banking/statement-of-fees"
```

