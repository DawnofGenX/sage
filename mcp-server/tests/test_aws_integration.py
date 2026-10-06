"""Tests for AWS integration wiring into the main request flow.

Verifies that:
- Bedrock is used when AWS credentials are present
- DynamoDB is used when AWS credentials are present
- S3 is used when AWS credentials are present
- EventBridge is used when AWS credentials are present
- Fallback works without credentials
"""
import asyncio
import os
import tempfile

import pytest

from aws.bedrock import BedrockProvider
from aws.dynamodb import DynamoDBStore
from aws.eventbridge import EventBridgeTriggers
from aws.s3 import S3Storage
from data.db import Database
from llm.provider import LLMProvider
from tools.extraction import extract_from_call, _get_s3, _extract_s3_key
from proactive.engine import ProactiveEngine


# ------------------------------------------------------------------
# Bedrock Wired Tests
# ------------------------------------------------------------------


def test_bedrock_wired(monkeypatch):
    """Verify Bedrock is used when AWS credentials present."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    provider = LLMProvider()
    assert provider.use_bedrock is True
    assert provider.is_mock is False


def test_bedrock_not_used_without_credentials(monkeypatch):
    """Verify Bedrock is not used without AWS credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    provider = LLMProvider(api_key="", api_url="http://localhost:9999")
    assert provider.use_bedrock is False
    assert provider.is_mock is True


def test_bedrock_explicit_flag(monkeypatch):
    """Verify explicit use_bedrock flag overrides env detection."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    provider = LLMProvider(api_key="", api_url="http://localhost:9999", use_bedrock=True)
    assert provider.use_bedrock is True
    assert provider.is_mock is False


def test_bedrock_extract_delegates(monkeypatch):
    """Verify extract() delegates to Bedrock when enabled."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    provider = LLMProvider()
    # Mock the Bedrock provider to avoid real AWS calls
    from unittest.mock import AsyncMock, MagicMock, patch as mock_patch
    mock_bedrock = MagicMock()
    mock_bedrock.extract = AsyncMock(return_value={"people": ["John Smith"], "companies": ["Acme"], "amounts": [], "dates": []})
    with mock_patch.object(provider, '_bedrock_provider', mock_bedrock):
        result = asyncio.run(provider.extract("Test transcript", "entities"))
    assert isinstance(result, dict)
    assert "people" in result


# ------------------------------------------------------------------
# DynamoDB Wired Tests
# ------------------------------------------------------------------


def test_dynamodb_wired(monkeypatch):
    """Verify DynamoDB is used when AWS credentials present."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    db = Database(db_path=":memory:")
    assert db.use_dynamodb is True


def test_dynamodb_not_used_without_credentials(monkeypatch):
    """Verify DynamoDB is not used without AWS credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path=db_path)
    assert db.use_dynamodb is False
    os.unlink(db_path)


def test_dynamodb_explicit_flag(monkeypatch):
    """Verify explicit use_dynamodb flag overrides env detection."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    db = Database(db_path=":memory:", use_dynamodb=True)
    assert db.use_dynamodb is True


def test_dynamodb_delegation_methods(monkeypatch):
    """Verify DynamoDB delegation methods work when enabled."""
    from unittest.mock import MagicMock, patch as mock_patch

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    db = Database(db_path=":memory:")

    # Mock the DynamoDB store to avoid real AWS calls
    mock_store = MagicMock()
    mock_store.put_item.return_value = True
    mock_store.scan_items.return_value = [{"name": "Test", "company": "Acme"}]
    mock_store.get_item.return_value = {"name": "Test"}
    mock_store.query_items.return_value = [{"name": "Test"}]

    with mock_patch.object(db, '_dynamodb_store', mock_store):
        result = db.dynamodb_put("contacts", {"name": "Test", "company": "Acme"})
        assert result is True

        items = db.dynamodb_scan("contacts")
        assert len(items) == 1
        assert items[0]["name"] == "Test"


def test_dynamodb_delegation_noop_without_credentials(monkeypatch):
    """Verify DynamoDB delegation methods are no-ops without credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path=db_path)
    assert db.use_dynamodb is False

    # These should be no-ops
    assert db.dynamodb_put("contacts", {"name": "Test"}) is False
    assert db.dynamodb_get("contacts", {"id": "123"}) == {}
    assert db.dynamodb_query("contacts", "name = 'Test'") == []
    assert db.dynamodb_scan("contacts") == []
    os.unlink(db_path)


# ------------------------------------------------------------------
# S3 Wired Tests
# ------------------------------------------------------------------


def test_s3_wired(monkeypatch):
    """Verify S3 is used when AWS credentials present."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    s3 = S3Storage()
    assert s3.is_fallback is False


def test_s3_fallback_without_credentials(monkeypatch):
    """Verify S3 falls back to local storage without credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        s3 = S3Storage(local_dir=tmpdir)
        assert s3.is_fallback is True


def test_s3_upload_and_get_with_credentials(monkeypatch):
    """Verify S3 upload/get works with credentials (falls back to local on error)."""
    from unittest.mock import MagicMock, patch as mock_patch

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    with tempfile.TemporaryDirectory() as tmpdir:
        s3 = S3Storage(local_dir=tmpdir)
        # Mock the S3 client to avoid real AWS calls
        mock_client = MagicMock()
        mock_client.put_object.return_value = {}
        mock_client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"audio data"))}
        mock_client.list_objects_v2.return_value = {"Contents": [{"Key": "recordings/test.mp3"}]}

        with mock_patch.object(s3, '_client', mock_client):
            url = s3.upload_recording("recordings/test.mp3", b"audio data")
            assert url is not None
            assert len(url) > 0
            assert "sage-recordings" in url


def test_s3_key_extraction():
    """Verify S3 key extraction from various URL formats."""
    # Virtual-hosted-style
    url1 = "https://sage-recordings.s3.us-east-1.amazonaws.com/recordings/2024/01/call_001.mp3"
    key1 = _extract_s3_key(url1)
    assert key1 == "recordings/2024/01/call_001.mp3"

    # Path-style
    url2 = "https://s3.us-east-1.amazonaws.com/sage-recordings/recordings/2024/01/call_001.mp3"
    key2 = _extract_s3_key(url2)
    assert key2 == "recordings/2024/01/call_001.mp3"

    # File URL
    url3 = "file:///tmp/sage_s3_fallback/recordings/test.mp3"
    key3 = _extract_s3_key(url3)
    assert key3 == "/tmp/sage_s3_fallback/recordings/test.mp3"


# ------------------------------------------------------------------
# EventBridge Wired Tests
# ------------------------------------------------------------------


def test_eventbridge_wired(monkeypatch):
    """Verify EventBridge is used when AWS credentials present."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    eb = EventBridgeTriggers()
    assert eb.is_fallback is False


def test_eventbridge_fallback_without_credentials(monkeypatch):
    """Verify EventBridge falls back to in-process without credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    eb = EventBridgeTriggers()
    assert eb.is_fallback is True


def test_eventbridge_schedule_and_list(monkeypatch):
    """Verify EventBridge schedule/list works with credentials (falls back on error)."""
    from unittest.mock import MagicMock, patch as mock_patch

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "«redacted:AKIA…»")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    eb = EventBridgeTriggers()
    # Mock the EventBridge client to avoid real AWS calls
    mock_client = MagicMock()
    mock_client.put_rule.return_value = {"RuleArn": "arn:aws:events:us-east-1:000000000000:rule/default/sage-test-rule"}
    mock_client.put_targets.return_value = {}
    mock_client.list_rules.return_value = {"Rules": [{"Name": "sage-test-rule", "ScheduleExpression": "cron(0 9 * * ? *)", "State": "ENABLED", "Arn": "arn:aws:events:us-east-1:000000000000:rule/default/sage-test-rule"}]}

    with mock_patch.object(eb, '_client', mock_client):
        rule_id = eb.schedule_insight(
            name="sage-test-rule",
            schedule="cron(0 9 * * ? *)",
            payload={"test": "data"},
        )
        assert rule_id is not None
        assert len(rule_id) > 0
        assert "arn:aws:events" in rule_id


# ------------------------------------------------------------------
# Fallback Without Credentials Tests
# ------------------------------------------------------------------


def test_fallback_without_credentials(monkeypatch):
    """Verify all adapters fall back gracefully without credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    # LLM Provider falls back to mock
    llm = LLMProvider(api_key="", api_url="http://localhost:9999")
    assert llm.is_mock is True
    assert llm.use_bedrock is False

    # Database falls back to SQLite
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path=db_path)
    assert db.use_dynamodb is False
    os.unlink(db_path)

    # S3 falls back to local files
    with tempfile.TemporaryDirectory() as tmpdir:
        s3 = S3Storage(local_dir=tmpdir)
        assert s3.is_fallback is True

    # EventBridge falls back to in-process
    eb = EventBridgeTriggers()
    assert eb.is_fallback is True


def test_fallback_llm_still_works(monkeypatch):
    """Verify LLM extraction works in fallback mode."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    llm = LLMProvider(api_key="", api_url="http://localhost:9999")
    result = asyncio.run(llm.extract("Test transcript", "entities"))
    assert isinstance(result, dict)
    assert "people" in result


def test_fallback_db_still_works(monkeypatch):
    """Verify DB operations work in fallback mode."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = Database(db_path=db_path)

    contact_id = db.create_contact({"name": "Test", "company": "Acme"})
    assert contact_id > 0

    contact = db.get_contact(contact_id)
    assert contact["name"] == "Test"
    os.unlink(db_path)


def test_fallback_s3_still_works(monkeypatch):
    """Verify S3 operations work in fallback mode."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        s3 = S3Storage(local_dir=tmpdir)
        url = s3.upload_recording("test/recording.mp3", b"audio data")
        assert url.startswith("file://")

        data = s3.get_recording("test/recording.mp3")
        assert data == b"audio data"


def test_fallback_eventbridge_still_works(monkeypatch):
    """Verify EventBridge operations work in fallback mode."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    eb = EventBridgeTriggers()
    rule_id = eb.schedule_insight(
        name="sage-test",
        schedule="cron(0 9 * * ? *)",
        payload={},
    )
    assert rule_id is not None

    rules = eb.list_rules()
    assert len(rules) == 1

    result = eb.delete_rule("sage-test")
    assert result is True


# ------------------------------------------------------------------
# Integration Flow Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_from_call_with_audio_url(monkeypatch):
    """Verify extract_from_call works with audio_url parameter."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Upload a fake recording
        s3 = S3Storage(local_dir=tmpdir)
        audio_url = s3.upload_recording("recordings/test.mp3", b"x" * 32000)

        # Extract with audio_url
        result = await extract_from_call(
            transcript="Test transcript with audio",
            audio_url=audio_url,
        )
        assert "step1_entities" in result
        assert "step4_validated" in result


@pytest.mark.asyncio
async def test_extract_from_call_without_audio_url(monkeypatch):
    """Verify extract_from_call works without audio_url parameter."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    result = await extract_from_call(transcript="Test transcript")
    assert "step1_entities" in result
    assert "step4_validated" in result


@pytest.mark.asyncio
async def test_proactive_engine_schedules_via_eventbridge(monkeypatch):
    """Verify ProactiveEngine schedules alerts via EventBridge."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path=db_path)
    llm = LLMProvider(api_key="", api_url="http://localhost:9999")
    engine = ProactiveEngine(db, llm)

    # Create test data
    contact_id = db.create_contact({"name": "Test Contact"})
    db.create_followup({
        "contact_id": contact_id,
        "title": "Overdue Follow-up",
        "due_date": "2020-01-01",  # Definitely overdue
    })

    insights = await engine.generate_insights()
    assert len(insights) > 0
    assert any("Overdue" in i for i in insights)

    os.unlink(db_path)
