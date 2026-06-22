from config import settings
from storage import get_session, Transaction, Category
from itertools import batched
import anthropic
import json

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def get_uncategorized_transactions() -> list[Transaction]:
    with get_session() as session:
        transactions = session.query(Transaction).filter(Transaction.category.is_(None)).all()
        session.expunge_all()

    return transactions


def categorize_batch(transactions: list[Transaction]) -> dict[str, str]: 
    all_results = {}

    with open("src/prompts/categorization_system_prompt.txt", "r") as f:
        system_prompt = f.read()

    for batch in batched(transactions, 50):
        user_message = {}

        for tr in batch:
            entry = {"remittance_information": tr.remittance_information, 
                     "credit_debit_indicator": tr.credit_debit_indicator,
                     "transaction_code": tr.transaction_code
                     }
            user_message[tr.id] = entry

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": json.dumps(user_message)}
            ]
        )

        text_block = next(block for block in response.content if block.type == "text")
        batch_result = json.loads(text_block.text)
        all_results.update(batch_result)

    return all_results


def update_categories(category_dict: dict[str, str]):
    with get_session() as session:
        for id, cat in category_dict.items():
            tr = session.get(Transaction, id)
            if tr:
                tr.category = cat
        
        session.commit()


def run_categorization():
    uncat_tr = get_uncategorized_transactions()
    categories = categorize_batch(transactions=uncat_tr)
    update_categories(category_dict=categories)

if __name__ == "__main__":
    run_categorization()