# Personal Finance Tracker

A self-hosted personal finance tracker that connects to your bank accounts via PSD2 open banking, automatically categorizes transactions using Claude AI, and exposes your financial data through a natural language MCP interface and a read-only web dashboard.

> **Status:** Early-stage personal project. Works with any European bank supported by [Enable Banking](https://enablebanking.com). Tested with Erste Bank (Hungary) and Revolut (Lithuanian & Hungarian IBAN).

---

## Demo

<!-- TODO: Add screenshot or GIF of the dashboard and Claude MCP interface -->

---

## How it works

```
Enable Banking API (PSD2)
  └── fetcher.py         — pulls transactions and balances daily
      └── processor.py   — normalizes and stores to SQLite
          └── categorization_agent.py — Claude AI assigns categories
              └── mcp_server.py  — natural language interface via Claude desktop
              └── dashboard.py   — read-only web dashboard
```

**The intelligence layer:** Each transaction's remittance information is embedded using OpenAI's `text-embedding-3-small` and compared against a growing library of categorization examples via `sqlite-vec` vector similarity search. Claude uses these as few-shot context to assign categories. Every manual correction you make teaches the system — future similar transactions are categorized correctly automatically.

---

## Features

- **PSD2 bank connection** via Enable Banking — supports 2,700+ European banks
- **Automatic categorization** using Claude AI with vector similarity search
- **Learning from corrections** — recategorize once, remember forever
- **Natural language interface** via Claude desktop MCP integration
- **Read-only web dashboard** with spending/income donut charts and a transaction list showing category per transaction
- **Multi-bank, multi-currency** support
- **Incremental sync** — only fetches new transactions on each run

---

## Prerequisites

- Python 3.12+
- [Conda](https://docs.conda.io) or `venv`
- [mkcert](https://github.com/FiloSottile/mkcert) — for local HTTPS (OAuth callback)
- [Claude desktop app](https://claude.ai/download) — for the MCP interface
- An [Enable Banking](https://enablebanking.com) account (free, restricted mode)
- An [Anthropic API key](https://console.anthropic.com)
- An [OpenAI API key](https://platform.openai.com) (for embeddings — costs < $0.01/month)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/gbrsoos/personal-finance-tracker.git
cd personal-finance-tracker
```

### 2. Create the Python environment

```bash
conda create -n finance-tracker python=3.12
conda activate finance-tracker
poetry install
```

### 3. Generate RSA keys

Used to authenticate with Enable Banking's API:

```bash
mkdir -p secrets
openssl genrsa -out secrets/private.pem 2048
openssl req -new -x509 -key secrets/private.pem -out secrets/certificate.pem -days 365 -subj "/CN=personal-finance-tracker"
```

### 4. Generate local SSL certificate

Required for the OAuth callback during bank authentication:

```bash
brew install mkcert
mkcert -install
mkcert localhost 127.0.0.1
mv localhost+1.pem secrets/
mv localhost+1-key.pem secrets/
```

### 5. Set up Enable Banking

1. Sign up at [enablebanking.com](https://enablebanking.com)
2. Create a new **Restricted** application (free, personal use)
3. Upload the contents of `secrets/certificate.pem` as the application certificate
4. Set the redirect URL to `https://localhost:8000/callback`
5. Note your **Application ID**

### 6. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env` with your credentials:

```
ENABLE_BANKING_APP_ID=your-application-id
ENABLE_BANKING_KEY_PATH=./secrets/private.pem
REDIRECT_URL=https://localhost:8000/callback
SSL_CERT_PATH=./secrets/localhost+1.pem
SSL_KEY_PATH=./secrets/localhost+1-key.pem
SESSIONS_INFO_PATH=./secrets/sessions.json
DATABASE_URL=sqlite:///./data/finance.db
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
CURRENCIES=["HUF","EUR","USD"]
DEPLOY_CWD=/absolute/path/to/personal-finance-tracker
```

> `DEPLOY_CWD` is only needed on the Pi, where it tells `deploy_watcher.py` which directory to run `git pull`, `poetry install`, and migrations in.

### 7. Configure your banks

Edit `src/config.py` and set the banks you want to connect:

```python
BANKS = {
    "Erste Bank": "HU",
    "Revolut": "HU",
}
```

Use the exact ASPSP name from Enable Banking's bank list.

### 8. Initialize the database

```bash
mkdir -p data
python src/storage.py
```

### 9. Mark the database as up to date with Alembic

This tells Alembic that the database is already at the latest schema version (since `storage.py` just created it fresh):

```bash
alembic stamp head
```

> **Note:** Only run this on a fresh database. If you're upgrading an existing installation, use `alembic upgrade head` instead — it will apply any new migrations without touching your data.

### 10. Authenticate with your banks

This opens a browser for each bank to complete PSD2 authentication (one-time setup per bank, valid for 180 days):

```bash
python src/bank_client.py
```

### 11. Run the first sync

```bash
python src/scheduler.py
```

This fetches transactions, normalizes them, and runs AI categorization.

---

## Running the dashboard

```bash
PYTHONPATH=src uvicorn src.dashboard:app --reload --port 8080
```

Open `http://localhost:8080` in your browser.

---

## Connecting to Claude desktop (MCP)

Add the following to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "personal_finance_tracker": {
      "command": "/path/to/conda/envs/finance-tracker/bin/python",
      "args": ["/path/to/personal-finance-tracker/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/personal-finance-tracker/src",
        "ENABLE_BANKING_APP_ID": "your-app-id",
        "ENABLE_BANKING_KEY_PATH": "/absolute/path/to/secrets/private.pem",
        "REDIRECT_URL": "https://localhost:8000/callback",
        "SSL_CERT_PATH": "/absolute/path/to/secrets/localhost+1.pem",
        "SSL_KEY_PATH": "/absolute/path/to/secrets/localhost+1-key.pem",
        "SESSIONS_INFO_PATH": "/absolute/path/to/secrets/sessions.json",
        "DATABASE_URL": "sqlite:////absolute/path/to/data/finance.db",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "OPENAI_API_KEY": "sk-...",
        "CURRENCIES": "[\"HUF\",\"EUR\",\"USD\"]"
      }
    }
  }
}
```

Restart Claude desktop. You can now ask Claude things like:
- *"How much did I spend on groceries last month?"*
- *"Show me all my Irregular transactions from June"*
- *"Recategorize the Netflix transaction to Subscriptions"*

---

## Automating the daily sync (cron)

```bash
crontab -e
```

Add:

```
0 8 * * * cd /path/to/personal-finance-tracker && /path/to/conda/envs/finance-tracker/bin/python src/scheduler.py
```

---

## Automatic deployment

On the Raspberry Pi, `deploy_watcher.py` runs as a `systemd` service and polls the GitHub releases API every 10 minutes. When the latest release tag differs from the version in the deployed `pyproject.toml`, it automatically pulls the latest changes, reinstalls dependencies with Poetry, runs pending Alembic migrations, and restarts the scheduler and dashboard services — so shipping a new GitHub release is enough to deploy it, no manual SSH step required.

---

## Updating an existing installation

When a new version introduces schema changes, apply them without losing data:

```bash
git pull
alembic upgrade head
```

---

## Project structure

```
personal-finance-tracker/
├── src/
│   ├── config.py                 # Pydantic settings + bank configuration
│   ├── bank_client.py            # Enable Banking auth + session management
│   ├── fetcher.py                # Transaction and balance fetching
│   ├── processor.py              # Normalization and database writes
│   ├── storage.py                # SQLAlchemy models + SQLite setup
│   ├── categorization_agent.py   # Claude AI categorization
│   ├── embedder.py               # OpenAI embeddings + sqlite-vec search
│   ├── queries.py                # Shared database query functions
│   ├── scheduler.py              # Pipeline orchestrator
│   ├── mcp_server.py             # FastMCP server (Claude desktop interface)
│   ├── dashboard.py              # FastAPI read-only web dashboard
│   ├── dashboard.html            # Dashboard frontend
│   ├── deploy_watcher.py         # Polls GitHub releases, auto-deploys on new tag
│   └── prompts/
│       └── categorization_system_prompt.txt
├── migrations/                   # Alembic database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── secrets/                      # Git-ignored — credentials only
├── data/                         # Git-ignored — SQLite database
├── .env                          # Git-ignored — your credentials
├── .env.example                  # Template for credentials
├── alembic.ini                   # Alembic configuration
├── pyproject.toml                # Poetry project + dependency definitions
└── README.md
```

---

## Spending categories

Default categories (configurable in `src/storage.py`):

| Type | Categories |
|------|-----------|
| Spending | Groceries, Clothes, Utilities, Subscriptions, Eating out, Transport, Sports, Irregular |
| Income | Salary, Ingenium, Other Income |
| Savings | Revolut Spare Change |
| Transfer | Currency Exchange |

---

## License

MIT — see [LICENSE](LICENSE)

---

## Contributing

This project is in early personal use. If you find it useful and want to contribute, open an issue first to discuss what you'd like to change.
