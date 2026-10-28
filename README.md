# Payment Reconciliation Automation

🌐 **[Leia isto em Português (Brasil)](https://github.com/vagner-lcf/payment-reconciliation-automation/blob/master/README.pt-br.md).**

A Python project developed to address a real operational need: reviewing payment receipts, locating the corresponding accounts payable in Tiny/Olist ERP, and, when authorized, performing financial settlements in a controlled manner.

The solution combines receipt data extraction, deterministic reconciliation rules, Tiny/Olist ERP API integration, and local persistence to reduce repetitive manual checks and mitigate the risk of duplicate processing.

> **Current status — October 28, 2026:** the MVP has been in production since October 26, 2026, when the first authorized financial settlement was completed through Telegram. On October 28, improvements to Tiny authentication failure handling and a user-operated reauthorization shortcut were deployed. **202 automated tests passed on the client's computer**, and the new authorization procedure was validated.

## Implemented Features

- **Receipt processing:** native text extraction from PDFs using `pypdf` and OCR for PNG/JPG/JPEG images using Google Cloud Vision.
- **Structured data extraction:** identification of payment provider, payment type, amount, date, beneficiary document number, and transaction identifiers when available.
- **Payment slip image validation:** for eligible Mercado Pago layouts, the amount extracted through OCR must match the amount encoded in the barcode.
- **ERP integration:** OAuth 2.0 authentication, token refresh, and paginated accounts payable retrieval through the Tiny/Olist API v3.
- **Deterministic matching:** matching based on the complete Brazilian CPF/CNPJ identifier, outstanding balance equal to the paid amount, and a due date within **±10 calendar days** of the payment date. Only a single, unambiguous match may proceed.
- **Duplicate prevention:** SQLite records and verification using file hashes and financial transaction identifiers when available.
- **Uncertainty handling:** ambiguous, incomplete, or remotely inconclusive transactions are routed to manual review or verification, without automatically repeating a settlement.
- **Structured results:** the main function returns a dictionary containing status, message, and diagnostic fields for operational interfaces.
- **Telegram integration:** long-polling bot, authorized group and senders, PDF/JPG/JPEG/PNG attachments, file validation, 10 MB size limit, and disposable temporary files.
- **Operational responses:** messages with visual indicators, CPF/CNPJ, amount, payment date, and local transaction reference when available, supporting manual verification in Tiny.
- **Configurable operating mode:** financial settlements can be enabled or disabled through the `SETTLEMENT_ENABLED` environment variable.
- **Windows startup:** execution through a `.bat` file, a PowerShell controller, and shortcuts.
- **Single-instance protection:** exclusive file locking prevents simultaneous executions started through the Windows launcher.
- **Automatic startup after login:** execution through a shortcut in the Windows Startup folder, validated locally.

## MVP Scope and Limitations

Automatic processing is restricted to explicitly recognized receipt types and layouts. **Mercado Pago** was prioritized as the initial MVP scope based on the receipt workflow observed in the real operation.

This decision allows the reconciliation logic and financial controls to be validated before expanding support to other issuers. The current implementation does not provide generic support for documents from other banks or payment providers.

For images, the `mp_pag_bol` and `mp_pix_bol` payment slip layouts require barcode validation.

**Pix transfer images (`mp_pix_tra`) are intentionally routed to manual review.** In these receipts, beneficiary identification numbers are often masked, and the amount presentation does not provide the same validation available in payment slips with barcodes. Therefore, extracted data alone is not considered sufficient to authorize an automatic settlement.

Unrecognized layouts and receipts missing required information are also routed to manual review.

The project **does not create missing accounts payable** in the ERP. When no matching account exists, the result is `no_match`. It also does not automate tax processes, accounting classification, cards, or the company's entire accounts payable workflow.

### MVP Engineering Criteria

The objective is to deliver a solution that is **sufficiently safe and reliable for everyday use**, prioritizing plausible risks of incorrect or duplicate settlements, operational unavailability, and recovery difficulties.

Additional security measures and technical complexity must be justified by actual risk, impact, and implementation cost. Protecting the application against every theoretically possible failure is not an objective of this MVP.

## Architecture and Processing Flow

```text
Payment receipt (PDF / image)
          |
          v
Text extraction (pypdf / Google Cloud Vision)
          |
          v
Receipt parsing and validation
          |
          v
Identification and deduplication (SQLite)
          |
          +--> Ineligible / insufficient data --> manual review
          |
          v
Accounts payable retrieval (Tiny API v3)
          |
          v
Deterministic matching
          |
          +--> No matching account ------------> no_match
          |
          +--> Ambiguous match ----------------> manual review
          |
          v
Single eligible match
          |
          +--> Safe mode (settlement_enabled=False) --> dry_run
          |
          +--> Settlement explicitly enabled
                       |
                       v
                 Request to Tiny
                       |
                       v
                 Confirmation query
                       |
                       v
                 Local state update
```

Orchestration is implemented in `src/main.py`. The Telegram adapter is implemented in `src/telegram_bot.py` and does not duplicate reconciliation business rules.

Account retrieval and financial settlement are separate operations: a successful HTTP response to a settlement request does not replace subsequent verification of the account's status in Tiny.

### Windows Startup Flow

For local Windows deployment, the execution flow is:

```text
Windows shortcut
       |
       v
scripts/windows/start_bot.bat
       |
       v
scripts/windows/run_bot.ps1
       |
       +--> Exclusive lock unavailable
       |           |
       |           v
       |      Existing-instance warning
       |
       v
Exclusive lock acquired
       |
       v
.venv/Scripts/python.exe -m src.telegram_bot
       |
       v
Telegram bot running
```

The startup mechanism does not modify the financial rules implemented in the reconciliation core.

## Technologies and Applied Concepts

| Technology | Purpose |
| --- | --- |
| Python | Orchestration and business rules |
| `pypdf` | Native PDF text extraction |
| Google Cloud Vision | OCR for receipt images |
| `requests` | HTTP communication with OAuth and the Tiny API |
| Tiny/Olist ERP API v3 | Accounts payable retrieval and financial integration |
| SQLAlchemy + SQLite | Local persistence, transaction states, and duplicate prevention |
| `python-dotenv` | Local configuration loading |
| `python-telegram-bot` | Receiving and responding to receipts in a private Telegram group |
| `pytest` | Automated testing |
| Windows Batch + PowerShell | Startup, instance control, and local operation |

Matching and eligibility decisions are implemented through **explicit rules**, not through an AI model autonomously deciding whether an account should be settled.

## Installation and Configuration

**Prerequisites:** a Python version compatible with the dependencies in `requirements.txt`, authorized access to the Tiny/Olist ERP API v3, and valid Google Cloud Vision credentials for image processing.

Clone the repository:

```bash
git clone https://github.com/vagner-lcf/payment-reconciliation-automation.git
cd payment-reconciliation-automation
```

Create a virtual environment on Windows (PowerShell) and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Using the virtual environment's Python executable directly eliminates the need to activate it manually.

Alternatively, activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Copy `.env.example` to `.env` and configure the required variables:

```dotenv
OLIST_CLIENT_ID=<your_client_id>
OLIST_CLIENT_SECRET=<your_client_secret>
OLIST_REDIRECT_URI=http://localhost:8000/callback

TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_ALLOWED_CHAT_ID=<private_group_id>
TELEGRAM_ALLOWED_USER_IDS=<user_id_1>,<user_id_2>

SETTLEMENT_ENABLED=false
```

The redirect URI must match the URI registered in the OAuth application and the local callback configuration, which uses port `8000`.

For image OCR, configure Google Cloud Vision authentication in the execution environment. PDFs containing native text do not depend on this service.

To authorize Tiny access for the first time or reauthorize it when necessary:

```powershell
.\.venv\Scripts\python.exe -m src.authorize_tiny
```

A browser will open for authorization. The returned tokens are stored locally in `data/tiny_tokens.json`, which is ignored by Git.

The system automatically refreshes access tokens when needed. Temporary connection failures or authentication service unavailability are handled separately and do not, by themselves, require manual reauthorization. In these cases, processing stops safely and can be attempted again after connectivity is restored. Manual reauthorization remains necessary when valid credentials are unavailable or Tiny rejects token renewal.

> **Security:** tokens stored in files are not encrypted by the project. Access to the computer and execution directory must be restricted. `.env.example` contains only placeholder values; `.env` and `data/` are ignored by Git.

### Google Cloud Vision Configuration

Image OCR uses Google Cloud Vision and requires **Application Default Credentials (ADC)** on the Windows account that runs the bot. PDFs with selectable native text do not require this service.

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project managed by the responsible organization, link a billing account, and enable the **Cloud Vision API**.
2. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) on the computer running the application.
3. In PowerShell, sign in for ADC and associate the quota/billing project:

   ```powershell
   gcloud auth application-default login
   gcloud auth application-default set-quota-project PROJECT_ID
   ```

   Replace `PROJECT_ID` with the actual Google Cloud project ID. This is **ADC authentication**, which is separate from the regular `gcloud auth login` session.
4. Verify that the Python process can initialize the Vision client:

   ```powershell
   .\.venv\Scripts\python.exe -c "from google.cloud import vision; vision.ImageAnnotatorClient(); print('Vision client initialized')"
   ```

   **Client initialization alone does not confirm** that OCR requests, API enablement, permissions, and billing work. Test a real, authorized image using the project's `src.image_text_extractor.extract_text_from_image()` function and verify the extracted text against the receipt.
5. Configure budget alerts in Google Cloud Billing and monitor actual usage. **Budget alerts are not a spending cap.** Restrict access to the Windows account and local ADC credentials; never commit or share tokens, credential files, or financial receipts.

The client's Google Cloud project, billing, Vision API, ADC, quota project, and a real OCR request were configured and validated during deployment on **October 26, 2026**. The client subsequently confirmed successful automatic startup after Windows login. OCR was validated during deployment; a separate post-login OCR retest has not been reported.

Official references: [Vision authentication](https://cloud.google.com/vision/docs/authentication) and [ADC for local development](https://cloud.google.com/docs/authentication/set-up-adc-local-dev).

## Operating Modes

### Safe Mode

The reconciliation core exposes the following programmatic interface:

```python
main(file_path: str, settlement_enabled: bool = False)
```

The default value remains `False`, regardless of the Telegram configuration.

To execute it directly:

```python
from src.main import main

result = main(
    file_path="data/input/sample_receipt.pdf",
    settlement_enabled=False,
)

print(result["status"])
print(result["message"])
```

The path above is illustrative: replace it with an existing, authorized receipt.

In `dry_run` mode, the system **does not request a financial settlement**, but it may still query the Tiny API, incur paid OCR usage for images, and store information in the local SQLite database.

### Telegram Settlement Configuration

The Telegram adapter uses the `SETTLEMENT_ENABLED` environment variable:

| Configuration | Behavior |
| --- | --- |
| Variable not set | Safe mode (`False`) |
| `SETTLEMENT_ENABLED=false` | Reconciliation without requesting financial settlement |
| `SETTLEMENT_ENABLED=true` | Allows automatic settlement for eligible receipts, subject to core validations |
| Invalid value | The bot will not start until the configuration is corrected |

The values `true` and `false` are accepted regardless of letter case.

**Configuration is loaded when the bot starts.** Therefore, changes to `.env` require restarting the process.

Setting `SETTLEMENT_ENABLED=true` should occur only after acceptance testing and authorization by the person responsible for financial operations.

Once production mode is enabled, authorized users submit receipts normally. Individual manual approval is not required for each eligible settlement.

**Real-world validation:** historical real-receipt testing was complemented by deployment on the client's computer on October 26, 2026. New and duplicate receipts behaved as expected in safe mode, and the first production settlement was completed through Telegram with the financial operator's authorization. This is initial operational validation, not proof that every exception or recovery scenario has been tested.

## Telegram Operation

Run the application from the project root after configuring `.env` and completing the initial Tiny authorization:

```powershell
.\.venv\Scripts\python.exe -m src.telegram_bot
```

The bot uses **long polling**. Keep **only one instance** running.

Access requires both:

- The private group configured in `TELEGRAM_ALLOWED_CHAT_ID`.
- A sender ID included in `TELEGRAM_ALLOWED_USER_IDS`.

The bot accepts photos and PDF, JPG, JPEG, and PNG documents. Other message types are not processed, and instructions included in receipt captions do not change reconciliation rules.

The adapter enforces a **10 MB** file size limit, checks document extensions and MIME types, and validates file signatures after downloading.

Files are stored temporarily and discarded after processing. The reconciliation core runs in a worker thread, with a lock ensuring that receipts are processed one at a time.

### Operational Messages

Responses use three visual indicators:

| Indicator | Meaning |
| --- | --- |
| ✅ | Confirmation of processing or a previously recorded settlement |
| ⚠️ | Warning, test mode, or manual verification required |
| ❌ | Negative result or processing failure |

When available, messages include:

- **CPF/CNPJ:** digits only, making it easier to copy and search in Tiny.
- **Amount:** Brazilian currency format, such as `R$ 1.179,06`.
- **Payment date:** `DD/MM/YYYY` format.
- **Reference:** local transaction identifier, useful for locating its record and correlating it with logs.

The reference identifies a transaction in the **local database**, not the account number in Tiny. It appears only when a transaction identifier is available.

This information helps locate the account in the ERP without manually transcribing data from the original receipt image.

Responses also distinguish financial outcomes. For example:

**Confirmed settlement**

```text
✅ Settlement successfully completed in Tiny.

CPF/CNPJ: 12345678000190
Amount: R$ 1.179,06
Payment date: 15/10/2026
Reference: 21
```

**Ambiguous match**

```text
⚠️ More than one matching account found.
No settlement performed. Check Tiny.

CPF/CNPJ: 12345678000190
Amount: R$ 1.179,06
Payment date: 15/10/2026
```

**Ineligible Pix transfer**

```text
⚠️ Pix transfer identified.
This receipt type is not eligible for
automatic settlement. Review it manually in Tiny.
No settlement performed.

Payment date: 13/10/2026
```

**Tiny reauthorization required**

```text
⚠️ Tiny authorization needs to be renewed.
On the computer, open the 'Autorizar Tiny'
shortcut and complete the authorization in your browser.
Then, resubmit the receipt.
No settlement was performed.
```

Temporary connection failures are handled separately and do not require immediate reauthorization.


The examples above are English translations for documentation purposes. **The application's actual Telegram messages remain in Brazilian Portuguese.**

Messages are adapted to the data actually extracted. Missing fields are not populated with fabricated values.

The specific classification of Pix transfers uses the reason returned by the reconciliation core, without confusing this situation with other manual review cases.

**Important:** OCR-extracted data may require visual verification. The message makes searching easier but does not replace checking the receipt and the corresponding entry in Tiny when intervention is required.

### Bot Availability

The computer running the application must remain powered on, connected to the internet, and have an active bot process for continuous operation.

During operational testing, receipts sent while the bot was offline were processed after it restarted. This behavior does not guarantee message recovery under all circumstances.

The MVP does not use its own persistent queue, webhooks, or multiple bot instances.

## Windows Startup and Operation

For deployment on a Windows computer, startup files were created so the application can run without opening VS Code or entering Python commands.

### Files Used

```text
scripts/
└── windows/
    ├── start_bot.bat
    └── run_bot.ps1
```

`start_bot.bat` displays the application header and operational instructions.

`run_bot.ps1` manages the single-instance lock and starts the project's Python environment.

Startup uses the executable:

```text
.venv\Scripts\python.exe
```

with the module:

```text
src.telegram_bot
```

### Single-Instance Protection

The PowerShell controller uses a file named `bot.lock`, located in the project root.

On startup, it attempts to open this file with exclusive access.

- **First execution:** the lock is acquired and the bot starts.
- **Second execution:** acquiring the lock fails, and a warning informs the user that the application is already running.
- **Shutdown:** the lock is released when the controller closes the file or its process terminates.

The `bot.lock` file may remain on disk after shutdown. Its existence alone does not mean the application is running.

The file is ignored by Git because it is a local runtime artifact.

**Limitation:** this protection applies to instances started through the `run_bot.ps1` controller. Running the Python module directly does not use this lock and should be avoided while the bot is already active.

### Desktop Shortcuts

The client's computer has two desktop shortcuts for operation.

**1. Main shortcut — Payment Reconciliation Automation**

Points to:

```text
scripts\windows\start_bot.bat
```

The project's custom icon is located at:

```text
assets\payment_reconciliation.ico
```

This shortcut starts the bot. If it is already running, an existing-instance warning is displayed without launching another instance.

**The shortcut starts the application; it does not restart an already running process.**

**2. Reauthorization shortcut — Autorizar Tiny**

Points to:

```text
scripts\windows\authorize_tiny.bat
```

When Telegram requests Tiny reauthorization, the user opens the **Autorizar Tiny** shortcut, signs in if prompted, and completes authorization in the browser.

After the message **"Autorização do Tiny concluída com sucesso."** appears, the user presses any key to close the authorization window and resubmits the receipt through Telegram.

**The main bot remains running.** Reauthorization does not automatically reprocess the previous receipt.

### Automatic Startup

Automatic startup was configured and validated using the Windows Startup folder:

1. Press `Win + R`.
2. Enter `shell:startup`.
3. Create a shortcut pointing to `scripts\windows\start_bot.bat`.
4. Sign out of Windows and sign in again.

After login, Windows executes the shortcut and starts the bot.

During local testing, automatic startup worked, and the application successfully responded to a new receipt sent through Telegram.

**Important limitation:** the application does not start while Windows remains at the login screen. After a computer restart, someone must sign in before the Startup shortcut is executed.

The computer must also be configured not to enter sleep mode during periods when the bot is expected to remain available.

### Shutting Down the Application

To stop the bot:

1. Wait for the response to the most recently submitted receipt.
2. Confirm that no processing is underway.
3. Press `Ctrl+C` in the application window.
4. If Windows displays `Terminate batch job (Y/N)?`, enter `Y` and press Enter. On a Portuguese-language Windows installation, the prompt may use `S/N`; in that case, enter `S`.

Closing the window using the `X` button may also terminate the process but should be avoided during financial operations.

Stopping the application during a settlement request may leave the result inconclusive, requiring verification in Tiny before any further attempt.

### Manual Restart

There is currently no automated safe-restart command.

The procedure is:

1. Wait for any receipt processing to finish.
2. Stop the application as described above.
3. Open the **Payment Reconciliation Automation** shortcut again.

This avoids introducing forced restarts that could interrupt financial operations.

## Processing Results and States

The main function returns a dictionary containing `status`, `message`, `reason`, `transaction_id`, `id_tiny`, `beneficiary_document`, `payment_date`, and `amount`.

| Status | Meaning |
| --- | --- |
| `dry_run` | A match was identified without requesting financial settlement |
| `processed` | Settlement confirmed in Tiny and local state updated |
| `already_processed` | Transaction previously recorded as processed |
| `already_in_review` | Transaction previously routed to manual review |
| `review_required` | Ineligible receipt or situation requiring manual verification |
| `no_match` | No matching account found |
| `ambiguous_match` | More than one possible match |
| `verification_pending` | Financial outcome or local update requires verification before proceeding |
| `error` | Processing or integration failure identified |

The `reason` field distinguishes situations sharing the same `status`.

For example, `unsupported_payment_type` identifies an ineligible Pix transfer, while `ineligible_receipt` identifies other receipts that do not meet automation requirements.

This distinction allows Telegram to display specific guidance without modifying the reconciliation business rules.

## Security and Failure Handling

The MVP's financial controls include:

- **Settlement disabled by default:** `settlement_enabled=False` remains the safe default for the main function.
- **Financial identity:** file hashes and transaction identifiers help prevent repeated processing of the same payment.
- **Persistent states:** `processing`, `processed`, and `review_required` distinguish pending, completed, and manually reviewed transactions.
- **Duplicate settlement prevention:** pending transactions associated with the same Tiny account are considered before a new attempt.
- **Remote confirmation:** a settlement is considered confirmed only after querying the account's status again in the ERP.
- **Inconclusive failures:** a timeout or error after requesting settlement does not prove that the operation failed. Recovery requires verification without automatically repeating the financial POST request.
- **Telegram access control:** only messages from the authorized group and senders are processed.
- **Single-instance Windows launcher:** attempts to start another instance through the same controller are blocked.

The Windows instance-control mechanism is an additional operational safeguard. It does not replace the financial reconciliation core's idempotency mechanisms.

### Manual Recovery of an Inconclusive Settlement

If the system returns `verification_pending` or an interruption during settlement is suspected:

1. **Do not automatically repeat the settlement**, and do not resend the receipt expecting another financial attempt.
2. Locate the account in Tiny using the receipt information and verify whether the payment has already been settled.
3. Review the local transaction record and logs with the technical maintainer.
4. Resolve the pending state only after determining the actual financial outcome. If uncertainty remains, keep the operation blocked for verification.

The recovery procedure above remains the reference for exceptional or inconclusive financial outcomes. Specific recovery scenarios not encountered during deployment should be validated when they arise; this is not a blocker for the completed MVP.

### Basic Maintenance

If the bot stops responding, check:

- Whether the computer is powered on, a user is signed in, and the system is not sleeping.
- Whether the internet connection is available.
- Whether the application window remains open.
- Whether Telegram, Tiny, and Google Cloud credentials are valid.
- Whether the logs show relevant errors.

After resolving the problem, start the application again using the Windows shortcut.

**Temporary Tiny authentication failure:** check the internet connection and retry processing after connectivity is restored. Immediate manual reauthorization is not required.

**Invalid or unavailable authorization:** when Telegram requests reauthorization, the user should open the **Autorizar Tiny** desktop shortcut and follow the instructions. For technical maintenance, the same procedure can be executed directly using the command below:

```powershell
.\.venv\Scripts\python.exe -m src.authorize_tiny
```

The installation procedure must identify who is responsible for running the bot and safeguarding local files, including the SQLite database, tokens, and logs.

Backups must be performed in a manner appropriate for the project's local operation, without exposing credentials or financial data.

### Updating the Application

Before updating the code:

1. Wait for all processing to finish.
2. Stop the bot.
3. Back up relevant local data, especially the SQLite database.
4. Preserve `.env`, tokens, and local configuration.
5. Update the project files.
6. Install any updated dependencies.
7. Run the automated tests.
8. Restart the application and validate its operation.

**Do not delete the `data/` directory during updates without reviewing and preserving the files required for operation.**

The `.venv` virtual environment must be created or configured on the target computer because it is not included in the repository.

## Testing and Validation

The automated test suite uses `pytest`. Run it from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**202 automated tests passed on the client's computer on October 28, 2026***, after the Tiny authentication failure-handling update.

The suite covers components such as data extraction, parsing, matching, persistence, simulated Tiny integration, eligibility rules, financial state handling, attachment validation, Telegram authorization, message formatting, and settlement mode configuration.

### Functional Validation Using Real Receipts

In addition to automated testing, a validation batch containing **62 real historical payment receipts** was processed.

The recorded results were:

| Result | Count |
| --- | ---: |
| New settlements completed | 14 |
| Receipts already processed | 8 |
| No matching account in the ERP | 24 |
| Previously recorded for manual review | 7 |
| New manual review cases | 4 |
| Ineligible Pix transfers | 4 |
| Error requiring further verification or a controlled retry | 1 |
| **Total** | **62** |

The results demonstrated the reconciliation rules working within the implemented scope.

However, **calculating an overall automation rate from this batch would be technically misleading**, because some historical receipts did not have corresponding accounts previously registered in Tiny.

The absence of an account in the ERP prevents automatic settlement even when the receipt has been interpreted correctly.

Historical functional testing was supplemented by testing and an authorized real settlement in the client's production environment. Individual settlements and exceptional outcomes still require verification in Tiny when appropriate.

### Windows Operational Tests

The following were also validated locally:

- Starting the bot through `start_bot.bat`.
- Running Python through the `run_bot.ps1` controller.
- Blocking a second instance started through the same mechanism.
- Displaying the visual duplicate-instance warning.
- Manual shutdown using `Ctrl+C`.
- Automatic startup after Windows login.
- Receiving and responding to a receipt after automatic startup.

**Client deployment (October 26, 2026):** installed on the company's computer; 198 automated tests passed there, Tiny authorization and Google Cloud Vision OCR were verified, the desktop launcher worked, and a first authorized real settlement was performed. The client subsequently confirmed successful automatic startup after Windows login. **The MVP is delivered and operating in production**, with routine monitoring and support for exceptional cases.

**Operational update (October 28, 2026):** improvements to temporary authentication failure classification and Tiny reauthorization were deployed. The **Autorizar Tiny** shortcut was validated on the client's computer, including browser authorization while the bot remained running. All 202 automated tests passed in that environment.

## Project Structure

```text
payment-reconciliation-automation/
├── assets/
│   └── payment_reconciliation.ico    # Windows shortcut icon
├── scripts/
│   └── windows/
│       ├── start_bot.bat             # Startup script with application header
│       |── run_bot.ps1               # Instance control and execution
|       └── authorize_tiny.bat        # Tiny reauthorization
├── src/
│   ├── main.py                       # Processing orchestration
│   ├── telegram_bot.py               # Telegram operational interface
│   ├── receipt_parser.py             # Structured data extraction
│   ├── pdf_text_extractor.py         # PDF text extraction
│   ├── image_text_extractor.py       # Image OCR
│   ├── receipt_hash_extractor.py     # File hash identification
│   ├── matching.py                   # Matching rules
│   ├── tiny_client.py                # ERP API integration
│   ├── auth.py                       # OAuth flows
│   ├── authorize_tiny.py             # Manual authorization
│   ├── callback.py                   # Local OAuth callback
│   ├── token_manager.py              # Token refresh
│   ├── token_store.py                # Token persistence
│   └── tratoray_transactions_db.py   # Transaction persistence
├── tests/                            # Automated tests
├── data/                             # Local data (ignored by Git)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md                         # English documentation
└── README.pt-br.md                   # Portuguese documentation
```

The structure highlights the main components rather than providing an exhaustive file listing. Data files, receipts, SQLite databases, and locally stored tokens must not be committed.

The `bot.lock` file, generated at runtime by the Windows controller, is also ignored by Git.

## MVP Delivery Status and Maintenance

**Status: MVP completed and deployed to production (October 26, 2026).** The application is installed on the client's computer, its integrations and automated tests were validated there, the financial operator authorized live settlements, and the first real settlement was completed through Telegram. The client subsequently confirmed automatic startup after Windows login.

The MVP's agreed scope is delivered. Day-to-day operation remains subject to normal financial controls: verify inconclusive outcomes in Tiny, resolve ineligible cases manually, preserve the local SQLite history, and maintain appropriate access and backups. Responsibilities for ongoing maintenance and backup routines should be kept clear; this is operational stewardship, not unfinished development scope.

Persistent queues, Redis, Celery, multiple instances, sophisticated monitoring, dashboards, and new integrations are not requirements of the delivered MVP. Future improvements will be evaluated if recurring operational exceptions or additional business needs justify them.

Any publication of this repository as a professional case study remains subject to confidentiality review and appropriate authorization. This documentation records the client's authorization for the deployed operation; it is **not** general authorization to enable financial settlements in other environments.

---

**Developed by Vagner Fonseca.**

**Repository:** https://github.com/vagner-lcf/payment-reconciliation-automation
