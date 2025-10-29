#!/usr/bin/env python
# coding: utf-8

# --- 1. All Imports ---
import pandas as pd
import chromadb
from collections import Counter
import requests
import time
from datetime import datetime, timedelta

# --- 2. Load Data Files ---
print("Loading data files...")
try:
    customers = pd.read_csv("data/Syntheticdata/customers.csv")
    products = pd.read_csv("data/Syntheticdata/products.csv")
    products_closed = pd.read_csv("data/Syntheticdata/products_closed.csv")
    transactions = pd.read_csv("data/Syntheticdata/transactions.csv")
except FileNotFoundError as e:
    print(
        f"CRITICAL ERROR: Could not find data files. Make sure the 'data/Syntheticdata' folder is correct."
    )
    print(e)
    exit()

# --- 3. Data Wrangling (As per your notebook) ---
print("Wrangling data...")
# Drop specific rows
customers = customers.drop(customers.index[30])
customers.reset_index(inplace=True, drop=True)

transactions = transactions.drop(transactions.index[65])
transactions.reset_index(inplace=True, drop=True)

# Convert data types
transactions[["transaction_id", "product_id"]] = transactions[
    ["transaction_id", "product_id"]
].astype(int)
transactions["amount"] = transactions["amount"].astype(float)
transactions["date"] = pd.to_datetime(transactions["date"], errors="coerce")

customers["birthdate"] = pd.to_datetime(customers["birthdate"], errors="coerce")
customers["customer_id"] = customers["customer_id"].astype(int)

products[["customer_id", "product_id"]] = products[
    ["customer_id", "product_id"]
].astype(int)
products["opened_date"] = pd.to_datetime(products["opened_date"], errors="coerce")
print("Data loading and wrangling complete.")

# --- 4. Vector DB Setup (Build Once Logic) ---
language_configs = {
    "en": "data/chunks/500_750_processed_be_en_2025_09_23/detailed_en_chunks.xlsx",
    "fr": "data/chunks/500_750_processed_be_fr_2025_09_23/detailed_fr_chunks.xlsx",
    "nl": "data/chunks/500_750_processed_be_nl_2025_09_23/detailed_nl_chunks.xlsx",
}
DB_PATH = "./chroma_db"
COLLECTION_NAME = "ing_knowledge_base"

# Use PersistentClient to save the database to disk
client = chromadb.PersistentClient(path=DB_PATH)

try:
    collection = client.get_collection(name=COLLECTION_NAME)
    if collection.count() > 0:
        print(f"✅ Connected to existing database with {collection.count()} documents.")
    else:
        raise Exception("Collection is empty, rebuilding.")

except Exception:
    print(f"Database not found or is empty. Building it now at {DB_PATH}...")
    try:
        if COLLECTION_NAME in [c.name for c in client.list_collections()]:
            client.delete_collection(name=COLLECTION_NAME)
        collection = client.create_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"Error creating collection: {e}")
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

    all_documents = []
    all_metadatas = []
    all_ids = []

    for lang_code, manifest_path in language_configs.items():
        print(f"--- Processing language: {lang_code.upper()} ---")
        # Ensure you have 'openpyxl' installed (via requirements.txt)
        df_manifest = pd.read_excel(manifest_path)
        for index, row in df_manifest.iterrows():
            document_content = row["chunk_content"]
            original_id = row["chunk_id"]
            unique_id = f"{lang_code}_{original_id}"

            chunk_metadata = {
                "language": lang_code,
                "chunk_name": row["chunk_name"],
                "chunk_url": row["chunk_url"],
                "chunk_number": row["chunk_number"],
            }

            all_documents.append(document_content)
            all_metadatas.append(chunk_metadata)
            all_ids.append(unique_id)

    print(f"Processed a total of {len(all_documents)} documents.")

    id_counts = Counter(all_ids)
    duplicates = [item for item, count in id_counts.items() if count > 1]

    if duplicates:
        print(
            f"\n❌ ERROR: Found {len(duplicates)} duplicated IDs in the final list before adding to DB."
        )
        print(
            "This means there are duplicate 'chunk_id' values within one of your Excel files."
        )
        print("Here are the first 10 problematic IDs:", duplicates[:10])
    else:
        print("\n✅ No duplicates found in the final prepared list.")
        if all_documents:
            collection.add(
                documents=all_documents, metadatas=all_metadatas, ids=all_ids
            )
            print("✅ Successfully built and saved the vector database!")


# --- 5. RAG System Setup ---

# --- Global API Key Configuration ---
API_KEY = ""
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"

# --- Create copies of the DataFrames for the RAG system to use ---
# This matches the logic from your original script
customers_df = customers.copy()
products_df = products.copy()
transactions_df = transactions.copy()

# --- The Master Prompt ---
MASTER_PROMPT = """
You are "Leo," an expert AI banking assistant for ING. Your personality is helpful, professional, and empathetic. Your primary goal is to provide secure and accurate assistance.
You must follow these four rules at all times:
RULE 1: STRICTLY USE PROVIDED CONTEXT
You will answer the customer's question ONLY using the information within the [Public Knowledge], [Customer's Personal Information], and [Pre-computed Data] sections. Do not use any outside knowledge.
RULE 2: NO HALLUCINATION OR GUESSING
If the information needed to answer the question is not in the provided context, you MUST respond with: "That's a great question. I can't seem to find that specific information in your records, but a human colleague can certainly help." and then suggest escalation. NEVER make up information or guess.
RULE 3: PRIVACY AND SECURITY IS PARAMOUNT
You are forbidden from discussing any customer other than the one in the context. Do not reveal sensitive personal details (like full addresses or account numbers) unless the user explicitly asks for them.
RULE 4: KNOW WHEN TO ESCALE
If the customer expresses strong negative emotions (e.g., anger, distress), mentions closing their account, reports a serious security issue like a stolen card, or asks for complex financial advice (e.g., "should I invest in stocks?"), you must immediately suggest an escalation by saying: "I understand this is an important matter. I will connect you with a human colleague who is best equipped to handle this for you."
---
[Public Knowledge from ING Website]
{public_context}
---
[Customer's Personal Information]
{personal_context}
---
[Pre-computed Data / Calculation Results]
{pre_computed_result}
---
[Customer's Question]
{question}
Based strictly on the rules and context above, provide a concise and helpful answer in a natural, spoken tone. If you see an opportunity, offer a proactive suggestion based on their data.
"""


# --- 6. Python Toolkit (Calculations) ---
def get_total_spending(customer_id, time_period="month", category=None):
    try:
        today = pd.Timestamp("2025-10-29")
        if time_period == "month":
            start_date = today.replace(day=1)
        elif time_period == "last_month":
            first_of_current_month = today.replace(day=1)
            start_date = (first_of_current_month - timedelta(days=1)).replace(day=1)
        elif time_period == "week":
            start_date = today - timedelta(days=today.dayofweek + 1)
        else:
            start_date = today.replace(day=1)

        active_products = products_df[products_df["customer_id"] == customer_id]

        customer_transactions = transactions_df[
            (transactions_df["product_id"].isin(active_products["product_id"]))
            & (transactions_df["transaction_type"] == "Debit")
            & (transactions_df["date"] >= start_date)
            & (transactions_df["date"] <= today)
        ]

        if category:
            customer_transactions = customer_transactions[
                customer_transactions["description"].str.contains(category, case=False)
            ]

        total_spent = customer_transactions["amount"].sum()

        time_str = (
            "this " + time_period if time_period != "last_month" else "last month"
        )
        category_str = f"on '{category}'" if category else ""

        return (
            f"The total amount spent {category_str} {time_str} is €{total_spent:.2f}."
        )
    except Exception as e:
        print(f"Error in get_total_spending: {e}")
        return "Error: Could not calculate spending."


# --- 7. Context Retrievers ---
def retrieve_public_context(question, language="en", n_results=2):
    try:
        results = collection.query(
            query_texts=[question], n_results=n_results, where={"language": language}
        )
        context = "\n".join(results["documents"][0])
        return context
    except Exception as e:
        print(f"Error retrieving from Vector DB: {e}")
        return "No public context found."


def retrieve_personal_context(customer_id, include_transactions=True):
    """
    Retrieves customer data. Can optionally exclude the recent transactions.
    """
    try:
        customer_info = customers_df[customers_df["customer_id"] == customer_id].iloc[0]
        active_products = products_df[products_df["customer_id"] == customer_id]

        context = f"""Customer Profile:
- Name: {customer_info['name']}
- Segment: {customer_info['segment_code']}

Owned Products (Active):
{active_products[['product_name', 'status']].to_string(index=False) if not active_products.empty else "No active products."}
"""

        if include_transactions:
            product_ids = active_products["product_id"]
            recent_transactions = transactions_df[
                transactions_df["product_id"].isin(product_ids)
            ].sort_values(by="date", ascending=False)
            context += f"""
Recent Transactions:
{recent_transactions[['date', 'description', 'amount', 'currency']].to_string(index=False) if not recent_transactions.empty else "No recent transactions."}
"""
        return context
    except IndexError:
        return f"Error: Customer with ID '{customer_id}' not found."
    except Exception as e:
        print(f"Error retrieving personal context: {e}")
        return "Error: Could not retrieve customer data."


# --- 8. Query Router ---
def route_query(question, customer_id):
    question_lower = question.lower()
    pre_computed_result = ""
    if "how much" in question_lower and "spend" in question_lower:
        category = None
        time_period = "month"

        if "groceries" in question_lower or "grocery" in question_lower:
            category = "Grocery"
        elif "transport" in question_lower:
            category = "Transport"

        if "this week" in question_lower:
            time_period = "week"
        elif "last month" in question_lower:
            time_period = "last_month"

        pre_computed_result = get_total_spending(customer_id, time_period, category)
        print(f"Pre-computed result: {pre_computed_result}")

    return pre_computed_result


# --- 9. Gemini API Call ---
def call_gemini_api(prompt):
    """
    Sends the completed prompt to the Gemini API using the simple API Key.
    """
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    max_retries = 3
    delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text
            else:
                return (
                    "I'm sorry, I wasn't able to generate a response. Please try again."
                )

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 429 and attempt < max_retries - 1:
                print(f"Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"HTTP error occurred: {http_err} - {response.text}")
                return "I'm sorry, I'm facing a technical issue and can't respond right now."
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            time.sleep(delay)
            delay *= 2

    return "I'm sorry, I'm currently overloaded. Please try again."


# --- 10. Main Orchestrator ---
def get_bot_response(user_question, customer_id, language="en"):
    print(f"\n--- New Query ---")
    print(f"User ({customer_id}): {user_question}")

    # 1. Route query to check for calculations
    pre_computed_result = route_query(user_question, customer_id)

    # 2. Retrieve public context
    public_context = retrieve_public_context(user_question, language)

    # 3. Retrieve personal context
    # If we have a pre-computed result, don't include the confusing "Recent Transactions" list.
    include_tx = not bool(pre_computed_result)
    personal_context = retrieve_personal_context(
        customer_id, include_transactions=include_tx
    )

    # 4. Assemble final prompt
    final_prompt = MASTER_PROMPT.format(
        public_context=public_context,
        personal_context=personal_context,
        pre_computed_result=pre_computed_result,
        question=user_question,
    )

    # 5. Call LLM for final answer
    final_answer = call_gemini_api(final_prompt)
    return final_answer


# --- 11. Example Usage (for testing) ---
if __name__ == "__main__":
    print("\n--- Running ing_assistant.py as main script for testing ---")

    # Make sure customers_df is not empty before trying to get a user
    if not customers_df.empty:
        example_customer_id = customers_df["customer_id"].iloc[0]  # This should be 1001

        # --- Example 1: A calculation query ---
        question_1 = "How much did I spend on groceries this month?"
        answer_1 = get_bot_response(question_1, example_customer_id)
        print(f"Bot: {answer_1}\n")

        # --- Example 2: A simple RAG query ---
        question_2 = "which account do i have?"
        answer_2 = get_bot_response(question_2, example_customer_id)
        print(f"Bot: {answer_2}\n")

        # --- Example 3: An escalation query ---
        question_3 = "My card was stolen! What do I do?"
        answer_3 = get_bot_response(question_3, example_customer_id)
        print(f"Bot: {answer_3}\n")
    else:
        print("Error: customers_df is empty, cannot run tests.")
