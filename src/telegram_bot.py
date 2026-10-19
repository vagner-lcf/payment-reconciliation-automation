
import asyncio
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.logging_config import configure_logging
from src.main import main as reconcile_receipt


logger = logging.getLogger("payment_reconciliation")

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

RESULT_MESSAGES = {
    "dry_run": "Conta correspondente localizada. Nenhuma baixa foi realizada.",
    "already_processed": "Transação já processada anteriormente.",
    "already_in_review": "Transação já registrada para revisão manual.",
    "review_required": "Comprovante encaminhado para revisão manual.",
    "no_match": "Nenhuma conta correspondente foi localizada.",
    "ambiguous_match": "Múltiplas contas encontradas. Conferência manual necessária.",
    "verification_pending": "Não foi possível confirmar o estado da transação. Verificação manual necessária.",
    "processed": "Transação identificada como processada.",
    "error": "O processamento não pôde ser concluído.",
}


def load_access_config() -> tuple[int, set[int]]:
    """Load the authorized Telegram chat and users."""

    chat_id = int(os.environ["TELEGRAM_ALLOWED_CHAT_ID"])

    user_ids = {
        int(value.strip())
        for value in os.environ["TELEGRAM_ALLOWED_USER_IDS"].split(",")
        if value.strip()
    }

    if not user_ids:
        raise ValueError("No allowed Telegram users configured.")

    return chat_id, user_ids


def is_authorized(
    update: Update,
    allowed_chat_id: int,
    allowed_user_ids: set[int],
) -> bool:
    """Require both an authorized chat and sender."""

    chat = update.effective_chat
    user = update.effective_user

    return (
        chat is not None
        and user is not None
        and chat.id == allowed_chat_id
        and user.id in allowed_user_ids
    )


def get_attachment_info(message):
    """Return an attachment and extension, using None for missing or invalid data."""

    if message.photo:
        return message.photo[-1], ".jpg"

    document = message.document

    if document is None:
        return None, None

    extension = Path(document.file_name or "").suffix.lower()

    if ALLOWED_MIME_TYPES.get(extension) != document.mime_type:
        return document, None

    return document, extension


def has_valid_file_signature(file_path: Path) -> bool:
    """Check whether the file header matches its extension."""

    signatures = {
        ".pdf": (b"%PDF-",),
        ".jpg": (b"\xff\xd8\xff",),
        ".jpeg": (b"\xff\xd8\xff",),
        ".png": (b"\x89PNG\r\n\x1a\n",),
    }

    expected_signatures = signatures.get(file_path.suffix.lower())

    if expected_signatures is None:
        return False

    with file_path.open("rb") as file:
        header = file.read(8)

    return any(
        header.startswith(signature)
        for signature in expected_signatures
    )


async def handle_attachment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Validate, download, and reconcile one receipt without financial settlement."""

    message = update.effective_message

    if message is None:
        return

    allowed_chat_id = context.application.bot_data["allowed_chat_id"]
    allowed_user_ids = context.application.bot_data["allowed_user_ids"]

    if not is_authorized(
        update,
        allowed_chat_id,
        allowed_user_ids,
    ):
        logger.warning("telegram_unauthorized_message")
        return

    attachment, extension = get_attachment_info(message)

    if attachment is None:
        return

    if extension is None:
        await message.reply_text(
            "Formato não suportado. Envie PDF, JPG, JPEG ou PNG."
        )
        return

    if (
        attachment.file_size is None
        or attachment.file_size > MAX_FILE_SIZE
    ):
        await message.reply_text(
            "Arquivo sem tamanho verificável ou maior que 10 MB."
        )
        return

    processing_lock = context.application.bot_data["processing_lock"]

    async with processing_lock:
        try:
            with tempfile.TemporaryDirectory(
                prefix="tratoray_telegram_"
            ) as temporary_directory:
                file_path = (
                    Path(temporary_directory)
                    / f"receipt{extension}"
                )

                telegram_file = await attachment.get_file()

                if (
                    telegram_file.file_size is None
                    or telegram_file.file_size > MAX_FILE_SIZE
                ):
                    await message.reply_text(
                        "Arquivo excede o limite permitido."
                    )
                    return

                await telegram_file.download_to_drive(
                    custom_path=file_path
                )

                if file_path.stat().st_size > MAX_FILE_SIZE:
                    await message.reply_text(
                        "Arquivo excede o limite permitido."
                    )
                    return

                if not has_valid_file_signature(file_path):
                    logger.warning(
                        "telegram_attachment_rejected reason=invalid_signature"
                    )
                    await message.reply_text(
                        "O arquivo não corresponde a um PDF ou imagem válida."
                    )
                    return

                logger.info(
                    "telegram_processing_started message_id=%s",
                    message.message_id,
                )

                result = await asyncio.to_thread(
                    reconcile_receipt,
                    str(file_path),
                    settlement_enabled=False,
                )

            status = result.get("status", "error")

            logger.info(
                "telegram_processing_finished status=%s",
                status,
            )

            await message.reply_text(
                RESULT_MESSAGES.get(
                    status,
                    "Resultado não reconhecido. Verifique o sistema.",
                )
            )

        except Exception as exc:
            logger.error(
                "telegram_processing_failed message_id=%s error_type=%s",
                message.message_id,
                type(exc).__name__,
            )

            await message.reply_text(
                "Falha ao processar o comprovante. "
                "Avise o responsável pelo sistema."
            )


def main() -> None:
    """Start the authorized Telegram bot in polling mode."""

    load_dotenv()
    configure_logging()

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    allowed_chat_id, allowed_user_ids = load_access_config()

    application = ApplicationBuilder().token(token).build()

    application.bot_data["allowed_chat_id"] = allowed_chat_id
    application.bot_data["allowed_user_ids"] = allowed_user_ids
    application.bot_data["processing_lock"] = asyncio.Lock()

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            handle_attachment,
        )
    )

    logger.info("telegram_bot_started")
    application.run_polling()


if __name__ == "__main__":
    main()
