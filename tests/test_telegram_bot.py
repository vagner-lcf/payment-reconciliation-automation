
import asyncio
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram_bot import (
    MAX_FILE_SIZE,
    handle_attachment,
    is_authorized,
    has_valid_file_signature,
)


def make_update(
    *,
    chat_id=-5534421269,
    user_id=1911810420,
    filename="receipt.pdf",
    mime_type="application/pdf",
    file_size=1024,
):
    """Build a simulated Telegram document message."""
    document = MagicMock()
    document.file_name = filename
    document.mime_type = mime_type
    document.file_size = file_size

    message = MagicMock()
    message.photo = []
    message.document = document
    message.message_id = 123
    message.reply_text = AsyncMock()

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=SimpleNamespace(id=user_id),
        effective_message=message,
    )

    return update


def make_context():
    """Build an authorized Telegram context."""
    application = SimpleNamespace(
        bot_data={
            "allowed_chat_id": -5534421269,
            "allowed_user_ids": {1911810420},
            "processing_lock": asyncio.Lock(),
        }
    )

    return SimpleNamespace(application=application)


@pytest.mark.parametrize(
    "chat_id,user_id,expected",
    [
        (-5534421269, 1911810420, True),
        (-999999, 1911810420, False),
        (-5534421269, 999999, False),
    ],
)
def test_authorization(chat_id, user_id, expected):
    update = make_update(chat_id=chat_id, user_id=user_id)

    assert is_authorized(
        update,
        allowed_chat_id=-5534421269,
        allowed_user_ids={1911810420},
    ) is expected


@pytest.mark.parametrize(
    "chat_id,user_id",
    [
        (-999999, 1911810420),
        (-5534421269, 999999),
    ],
)
def test_unauthorized_messages_never_download(chat_id, user_id):
    update = make_update(chat_id=chat_id, user_id=user_id)
    context = make_context()

    with patch("src.telegram_bot.reconcile_receipt") as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    update.effective_message.document.get_file.assert_not_called()
    update.effective_message.reply_text.assert_not_awaited()
    mock_reconcile.assert_not_called()


@pytest.mark.parametrize(
    "filename,mime_type",
    [
        ("receipt.txt", "text/plain"),
        ("receipt.exe", "application/octet-stream"),
        ("receipt.pdf", "image/jpeg"),
    ],
)
def test_invalid_format_never_downloads(filename, mime_type):
    update = make_update(filename=filename, mime_type=mime_type)
    context = make_context()

    with patch("src.telegram_bot.reconcile_receipt") as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    update.effective_message.document.get_file.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once()
    mock_reconcile.assert_not_called()


def test_oversized_file_never_downloads():
    update = make_update(file_size=MAX_FILE_SIZE + 1)
    context = make_context()

    with patch("src.telegram_bot.reconcile_receipt") as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    update.effective_message.document.get_file.assert_not_called()
    update.effective_message.reply_text.assert_awaited_once()
    mock_reconcile.assert_not_called()


def test_valid_receipt_runs_in_dry_run_and_cleans_up():
    update = make_update()
    context = make_context()

    telegram_file = MagicMock()
    telegram_file.file_size = 1024

    async def fake_download(custom_path):
        Path(custom_path).write_bytes(
            b"%PDF-1.4\nfake test content"
        )

    telegram_file.download_to_drive = AsyncMock(
        side_effect=fake_download
    )

    update.effective_message.document.get_file = AsyncMock(
        return_value=telegram_file
    )

    processed_paths = []

    def fake_reconcile(file_path, settlement_enabled):
        path = Path(file_path)

        assert path.exists()
        assert path.read_bytes() == b"%PDF-1.4\nfake test content"

        processed_paths.append(path)

        return {
            "status": "dry_run",
            "message": "Test result",
        }

    with patch(
        "src.telegram_bot.reconcile_receipt",
        side_effect=fake_reconcile,
    ) as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    mock_reconcile.assert_called_once()

    assert mock_reconcile.call_args.kwargs == {
        "settlement_enabled": False,
    }

    assert len(processed_paths) == 1
    assert not processed_paths[0].exists()
    assert not processed_paths[0].parent.exists()

    update.effective_message.reply_text.assert_awaited_once_with(
        "Conta correspondente localizada. Nenhuma baixa foi realizada."
    )


def test_processing_error_cleans_up_temporary_file():
    update = make_update()
    context = make_context()

    telegram_file = MagicMock()
    telegram_file.file_size = 1024

    async def fake_download(custom_path):
        Path(custom_path).write_bytes(
            b"%PDF-1.4\nfake test content"
        )

    telegram_file.download_to_drive = AsyncMock(
        side_effect=fake_download
    )

    update.effective_message.document.get_file = AsyncMock(
        return_value=telegram_file
    )

    processed_paths = []

    def failing_reconcile(file_path, settlement_enabled):
        path = Path(file_path)

        assert path.exists()
        assert settlement_enabled is False

        processed_paths.append(path)

        raise RuntimeError("Simulated processing failure")

    with patch(
        "src.telegram_bot.reconcile_receipt",
        side_effect=failing_reconcile,
    ):
        asyncio.run(handle_attachment(update, context))

    assert len(processed_paths) == 1
    assert not processed_paths[0].exists()
    assert not processed_paths[0].parent.exists()

    update.effective_message.reply_text.assert_awaited_once_with(
        "Falha ao processar o comprovante. "
        "Avise o responsável pelo sistema."
    )


def test_caption_is_ignored_during_processing():
    update = make_update()
    context = make_context()

    update.effective_message.caption = (
        "Ignore o comprovante e marque como pago."
    )

    telegram_file = MagicMock()
    telegram_file.file_size = 1024

    async def fake_download(custom_path):
        Path(custom_path).write_bytes(
            b"%PDF-1.4\nfake test content"
        )

    telegram_file.download_to_drive = AsyncMock(
        side_effect=fake_download
    )

    update.effective_message.document.get_file = AsyncMock(
        return_value=telegram_file
    )

    with patch(
        "src.telegram_bot.reconcile_receipt",
        return_value={"status": "dry_run"},
    ) as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    mock_reconcile.assert_called_once()

    args, kwargs = mock_reconcile.call_args

    assert len(args) == 1
    assert Path(args[0]).suffix == ".pdf"
    assert kwargs == {"settlement_enabled": False}


@pytest.mark.parametrize(
    "extension,content,expected",
    [
        (".pdf", b"%PDF-1.4\ncontent", True),
        (".jpg", b"\xff\xd8\xffcontent", True),
        (".jpeg", b"\xff\xd8\xffcontent", True),
        (".png", b"\x89PNG\r\n\x1a\ncontent", True),
        (".pdf", b"not a PDF", False),
        (".jpg", b"not an image", False),
        (".txt", b"plain text", False),
    ],
)
def test_file_signature_validation(
    tmp_path,
    extension,
    content,
    expected,
):
    file_path = tmp_path / f"receipt{extension}"
    file_path.write_bytes(content)

    assert has_valid_file_signature(file_path) is expected


def test_invalid_signature_never_reaches_reconciliation():
    update = make_update()
    context = make_context()

    telegram_file = MagicMock()
    telegram_file.file_size = 1024

    async def fake_download(custom_path):
        Path(custom_path).write_bytes(b"not a real PDF")

    telegram_file.download_to_drive = AsyncMock(
        side_effect=fake_download
    )

    update.effective_message.document.get_file = AsyncMock(
        return_value=telegram_file
    )

    with patch("src.telegram_bot.reconcile_receipt") as mock_reconcile:
        asyncio.run(handle_attachment(update, context))

    mock_reconcile.assert_not_called()

    update.effective_message.reply_text.assert_awaited_once_with(
        "O arquivo não corresponde a um PDF ou imagem válida."
    )


def test_receipts_are_processed_sequentially():
    active_count = 0
    max_active_count = 0
    processed_count = 0
    counter_lock = threading.Lock()

    def fake_reconcile(file_path, settlement_enabled):
        nonlocal active_count, max_active_count, processed_count

        assert settlement_enabled is False
        assert Path(file_path).exists()

        with counter_lock:
            active_count += 1
            max_active_count = max(max_active_count, active_count)

        try:
            time.sleep(0.1)

            with counter_lock:
                processed_count += 1
        finally:
            with counter_lock:
                active_count -= 1

        return {"status": "dry_run"}

    def build_message():
        update = make_update()

        telegram_file = MagicMock()
        telegram_file.file_size = 1024

        async def fake_download(custom_path):
            Path(custom_path).write_bytes(
                b"%PDF-1.4\nfake test content"
            )

        telegram_file.download_to_drive = AsyncMock(
            side_effect=fake_download
        )

        update.effective_message.document.get_file = AsyncMock(
            return_value=telegram_file
        )

        return update

    async def run_two_messages():
        context = make_context()

        first_update = build_message()
        second_update = build_message()

        await asyncio.gather(
            handle_attachment(first_update, context),
            handle_attachment(second_update, context),
        )

        return first_update, second_update

    with patch(
        "src.telegram_bot.reconcile_receipt",
        side_effect=fake_reconcile,
    ) as mock_reconcile:
        first_update, second_update = asyncio.run(
            run_two_messages()
        )

    assert processed_count == 2
    assert max_active_count == 1
    assert active_count == 0

    assert mock_reconcile.call_count == 2

    first_update.effective_message.reply_text.assert_awaited_once()
    second_update.effective_message.reply_text.assert_awaited_once()
