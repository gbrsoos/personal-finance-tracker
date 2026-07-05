from config import settings
from storage import get_session, Transaction
from embedder import find_similar_examples
from itertools import batched
import anthropic
import json

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_uncategorized_transactions() -> list[Transaction]:
    """Fetch all transactions that have not yet been assigned a category."""
    with get_session() as session:
        transactions = session.query(Transaction).filter(Transaction.category.is_(None)).all()
        session.expunge_all()

    return transactions


def categorize_batch(transactions: list[Transaction]) -> dict[str, str]:
    """
    Send transactions to Claude in batches of 50 and return a mapping of
    transaction ID → assigned category.

    For each batch, retrieves semantically similar categorization examples via
    vector search and passes them as few-shot context to the LLM.
    """
    all_results = {}

    with open("src/prompts/categorization_system_prompt.txt", "r") as f:
        system_prompt = f.read()

    for batch in batched(transactions, 50):
        remittance_strings: list[str] = [
            tr.remittance_information if tr.remittance_information else f"[No description] bank:{tr.bank_name} code:{tr.transaction_code} amount:{float(tr.amount)}"
            for tr in batch
        ]

        relevant_examples: dict[str, list] = find_similar_examples(remittance_strings=remittance_strings)

        user_message = {
            "examples": relevant_examples,
            "transactions": {}
        }

        for tr in batch:
            entry = {"remittance_information": tr.remittance_information if tr.remittance_information else f"[No description] bank:{tr.bank_name} code:{tr.transaction_code} amount:{float(tr.amount)}",
                     "credit_debit_indicator": tr.credit_debit_indicator,
                     "transaction_code": tr.transaction_code
                     }
            user_message["transactions"][tr.id] = entry

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": json.dumps(user_message)}
            ]
        )

        text_block = next(block for block in response.content if block.type == "text")
        batch_result = json.loads(text_block.text)
        all_results.update(batch_result)

    return all_results


def update_categories(category_dict: dict[str, str]) -> None:
    """Persist the LLM-assigned categories to the database."""
    with get_session() as session:
        for id, cat in category_dict.items():
            tr = session.get(Transaction, id)
            if tr and tr.category is None:
                tr.category = cat

        session.commit()


def run_categorization() -> int:
    """
    Run the full categorization pipeline: fetch uncategorized transactions,
    classify them with the LLM, and persist the results.

    Returns the number of transactions that were processed.
    """
    uncat_tr = get_uncategorized_transactions()
    categories = categorize_batch(transactions=uncat_tr)
    update_categories(category_dict=categories)

    return len(uncat_tr)

if __name__ == "__main__":
    run_categorization()
