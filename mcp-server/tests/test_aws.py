"""Tests for AWS integration adapters (Bedrock, DynamoDB, S3, EventBridge)."""

import asyncio
import os
import tempfile

import pytest


from aws.bedrock import BedrockProvider
from aws.dynamodb import DynamoDBStore
from aws.s3 import S3Storage
from aws.eventbridge import EventBridgeTriggers


# ------------------------------------------------------------------
# Bedrock Tests
# ------------------------------------------------------------------


@pytest.fixture
def bedrock_mock():
    """Bedrock provider in mock mode (no AWS credentials)."""
    return BedrockProvider(
        aws_access_key="",
        aws_secret_key="",
        region="us-east-1",
    )


@pytest.fixture
def bedrock_with_creds():
    """Bedrock provider with fake credentials (still mock for testing)."""
    return BedrockProvider(
        aws_access_key="AKIAIOSFODNN7EXAMPLE",
        aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
    )


@pytest.fixture
def sample_transcript():
    """A realistic sales call transcript."""
    return (
        "Hi, this is John Smith from Acme Corp. I spoke with Sarah Johnson "
        "at Globex Inc last week. She's very interested in our enterprise "
        "solution and mentioned a budget of $50,000. We should follow up "
        "with her on January 15th. She's excited about the demo and ready "
        "to move forward. The decision timeline is urgent."
    )


def test_bedrock_mock_mode(bedrock_mock):
    """Verify Bedrock provider falls back to mock mode without credentials."""
    assert bedrock_mock.is_mock is True


def test_bedrock_mock_mode_no_env(monkeypatch):
    """Verify mock mode when env vars are not set."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    provider = BedrockProvider()
    assert provider.is_mock is True


def test_bedrock_credentials_detection(monkeypatch):
    """Verify real mode when credentials are provided via env."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    provider = BedrockProvider()
    assert provider.is_mock is False


def test_bedrock_invoke_model_mock(bedrock_mock):
    """Verify invoke_model returns mock response."""
    result = asyncio.run(bedrock_mock.invoke_model("Extract entities from this transcript"))
    assert isinstance(result, str)
    assert len(result) > 0


def test_bedrock_extract_entities_mock(bedrock_mock, sample_transcript):
    """Verify extract returns structured entities in mock mode."""
    result = asyncio.run(bedrock_mock.extract(sample_transcript, "entities"))
    assert isinstance(result, dict)
    assert "people" in result
    assert "companies" in result
    assert "amounts" in result
    assert "dates" in result
    assert len(result["people"]) > 0
    assert len(result["companies"]) > 0


def test_bedrock_extract_sentiment_mock(bedrock_mock, sample_transcript):
    """Verify sentiment extraction in mock mode."""
    result = asyncio.run(bedrock_mock.extract(sample_transcript, "sentiment"))
    assert isinstance(result, dict)
    assert "sentiment" in result
    assert "confidence" in result
    assert result["sentiment"] in ("positive", "negative", "neutral")


def test_bedrock_extract_intent_mock(bedrock_mock, sample_transcript):
    """Verify intent extraction in mock mode."""
    result = asyncio.run(bedrock_mock.extract(sample_transcript, "intent"))
    assert isinstance(result, dict)
    assert "intent" in result
    assert "confidence" in result


def test_bedrock_extract_full_mock(bedrock_mock, sample_transcript):
    """Verify full extraction in mock mode."""
    result = asyncio.run(bedrock_mock.extract(sample_transcript, "full"))
    assert isinstance(result, dict)
    assert "contacts" in result
    assert "deals" in result
    assert "followups" in result
    assert "sentiment" in result
    assert "buying_signals" in result
    assert "risks" in result


def test_bedrock_extract_insights_mock(bedrock_mock, sample_transcript):
    """Verify insights extraction in mock mode."""
    result = asyncio.run(bedrock_mock.extract(sample_transcript, "insights"))
    assert isinstance(result, dict)
    assert "insights" in result
    assert "priority" in result
    assert isinstance(result["insights"], list)
    assert len(result["insights"]) > 0


def test_bedrock_supported_models():
    """Verify all supported model families are defined."""
    assert "nova-lite" in BedrockProvider.SUPPORTED_MODELS
    assert "nova-pro" in BedrockProvider.SUPPORTED_MODELS
    assert "nova-micro" in BedrockProvider.SUPPORTED_MODELS
    assert "claude-3-haiku" in BedrockProvider.SUPPORTED_MODELS
    assert "claude-3-sonnet" in BedrockProvider.SUPPORTED_MODELS
    assert "claude-3-opus" in BedrockProvider.SUPPORTED_MODELS


def test_bedrock_default_model():
    """Verify default model is Nova Lite."""
    assert BedrockProvider.DEFAULT_MODEL == "amazon.nova-lite-v1:0"


# ------------------------------------------------------------------
# DynamoDB Tests
# ------------------------------------------------------------------


@pytest.fixture
def dynamodb_fallback():
    """DynamoDB store in fallback mode (no AWS credentials)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    store = DynamoDBStore(
        aws_access_key="",
        aws_secret_key="",
        db_path=db_path,
    )
    yield store
    os.unlink(db_path)


def test_dynamodb_fallback(dynamodb_fallback):
    """Verify DynamoDB store falls back to SQLite without credentials."""
    assert dynamodb_fallback.is_fallback is True


def test_dynamodb_put_and_get(dynamodb_fallback):
    """Verify put_item and get_item work in fallback mode."""
    item = {
        "name": "Alice Johnson",
        "company": "Acme Corp",
        "email": "alice@acme.com",
        "phone": "555-0100",
        "title": "CTO",
    }
    result = dynamodb_fallback.put_item("contacts", item)
    assert result is True

    # Retrieve by ID
    item_id = item.get("id", "")
    retrieved = dynamodb_fallback.get_item("contacts", {"id": item_id})
    assert retrieved is not None
    assert retrieved["name"] == "Alice Johnson"
    assert retrieved["company"] == "Acme Corp"


def test_dynamodb_scan_items(dynamodb_fallback):
    """Verify scan_items returns all items."""
    # Insert multiple items
    dynamodb_fallback.put_item("contacts", {"name": "Alice", "company": "Acme"})
    dynamodb_fallback.put_item("contacts", {"name": "Bob", "company": "Globex"})
    dynamodb_fallback.put_item("contacts", {"name": "Charlie", "company": "Initech"})

    items = dynamodb_fallback.scan_items("contacts")
    assert len(items) == 3
    names = {item["name"] for item in items}
    assert names == {"Alice", "Bob", "Charlie"}


def test_dynamodb_query_items(dynamodb_fallback):
    """Verify query_items filters correctly."""
    dynamodb_fallback.put_item("contacts", {"name": "Alice", "company": "Acme"})
    dynamodb_fallback.put_item("contacts", {"name": "Bob", "company": "Globex"})
    dynamodb_fallback.put_item("contacts", {"name": "Charlie", "company": "Acme"})

    items = dynamodb_fallback.query_items("contacts", "company = 'Acme'")
    assert len(items) == 2
    names = {item["name"] for item in items}
    assert names == {"Alice", "Charlie"}


def test_dynamodb_deals(dynamodb_fallback):
    """Verify deals table operations."""
    deal = {
        "contact_id": "contact-123",
        "title": "Enterprise License",
        "value": 50000.0,
        "stage": "negotiation",
        "sentiment": "positive",
    }
    result = dynamodb_fallback.put_item("deals", deal)
    assert result is True

    items = dynamodb_fallback.scan_items("deals")
    assert len(items) == 1
    assert items[0]["title"] == "Enterprise License"
    assert items[0]["value"] == 50000.0


def test_dynamodb_call_logs(dynamodb_fallback):
    """Verify call_logs table with JSON fields."""
    log = {
        "contact_id": "contact-123",
        "transcript": "Call transcript text...",
        "summary": "Discussed enterprise pricing",
        "duration_seconds": 300,
        "sentiment": "positive",
        "buying_signals": ["budget", "timeline"],
        "risks": ["competitor"],
    }
    result = dynamodb_fallback.put_item("call_logs", log)
    assert result is True

    items = dynamodb_fallback.scan_items("call_logs")
    assert len(items) == 1
    assert items[0]["buying_signals"] == ["budget", "timeline"]
    assert items[0]["risks"] == ["competitor"]


def test_dynamodb_get_nonexistent(dynamodb_fallback):
    """Verify get_item returns empty dict for missing items."""
    result = dynamodb_fallback.get_item("contacts", {"id": "nonexistent-id"})
    assert result == {}


# ------------------------------------------------------------------
# S3 Tests
# ------------------------------------------------------------------


@pytest.fixture
def s3_fallback():
    """S3 storage in fallback mode (no AWS credentials)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = S3Storage(
            aws_access_key="",
            aws_secret_key="",
            local_dir=tmpdir,
        )
        yield storage


def test_s3_fallback(s3_fallback):
    """Verify S3 storage falls back to local files without credentials."""
    assert s3_fallback.is_fallback is True


def test_s3_upload_and_get(s3_fallback):
    """Verify upload_recording and get_recording work in fallback mode."""
    key = "recordings/2024/01/call_001.mp3"
    data = b"fake audio data for testing"

    url = s3_fallback.upload_recording(key, data)
    assert url.startswith("file://")
    assert "call_001.mp3" in url

    retrieved = s3_fallback.get_recording(key)
    assert retrieved == data


def test_s3_list_recordings(s3_fallback):
    """Verify list_recordings returns uploaded files."""
    s3_fallback.upload_recording("recordings/2024/01/call_001.mp3", b"audio1")
    s3_fallback.upload_recording("recordings/2024/01/call_002.mp3", b"audio2")
    s3_fallback.upload_recording("recordings/2024/02/call_003.mp3", b"audio3")

    results = s3_fallback.list_recordings("recordings/2024/01/")
    assert len(results) == 2
    assert all("call_00" in r for r in results)


def test_s3_get_nonexistent(s3_fallback):
    """Verify get_recording returns empty bytes for missing files."""
    result = s3_fallback.get_recording("recordings/nonexistent.mp3")
    assert result == b""


def test_s3_upload_returns_url(s3_fallback):
    """Verify upload_recording returns a valid file URL."""
    url = s3_fallback.upload_recording("test/recording.mp3", b"test data")
    assert url.startswith("file://")
    assert os.path.exists(url.replace("file://", ""))


# ------------------------------------------------------------------
# EventBridge Tests
# ------------------------------------------------------------------


@pytest.fixture
def eventbridge_fallback():
    """EventBridge triggers in fallback mode (no AWS credentials)."""
    return EventBridgeTriggers(
        aws_access_key="",
        aws_secret_key="",
    )


def test_eventbridge_fallback(eventbridge_fallback):
    """Verify EventBridge falls back to in-process without credentials."""
    assert eventbridge_fallback.is_fallback is True


def test_eventbridge_schedule_insight(eventbridge_fallback):
    """Verify schedule_insight creates a rule in fallback mode."""
    rule_id = eventbridge_fallback.schedule_insight(
        name="sage-daily-insights",
        schedule="cron(0 9 * * ? *)",
        payload={"target_arn": "arn:aws:lambda:us-east-1:123456789:function:sage-insights"},
    )
    assert rule_id is not None
    assert len(rule_id) > 0


def test_eventbridge_list_rules(eventbridge_fallback):
    """Verify list_rules returns scheduled rules."""
    eventbridge_fallback.schedule_insight(
        name="sage-daily-insights",
        schedule="cron(0 9 * * ? *)",
        payload={},
    )
    eventbridge_fallback.schedule_insight(
        name="sage-overdue-followups",
        schedule="cron(0 */4 * * ? *)",
        payload={},
    )

    rules = eventbridge_fallback.list_rules()
    assert len(rules) == 2
    names = {r["name"] for r in rules}
    assert names == {"sage-daily-insights", "sage-overdue-followups"}


def test_eventbridge_delete_rule(eventbridge_fallback):
    """Verify delete_rule removes a rule."""
    eventbridge_fallback.schedule_insight(
        name="sage-test-rule",
        schedule="cron(0 9 * * ? *)",
        payload={},
    )

    result = eventbridge_fallback.delete_rule("sage-test-rule")
    assert result is True

    rules = eventbridge_fallback.list_rules()
    assert len(rules) == 0


def test_eventbridge_delete_nonexistent(eventbridge_fallback):
    """Verify delete_rule returns False for missing rules."""
    result = eventbridge_fallback.delete_rule("nonexistent-rule")
    assert result is False


def test_eventbridge_schedule_with_payload(eventbridge_fallback):
    """Verify schedule_insight stores payload correctly."""
    payload = {
        "target_arn": "arn:aws:lambda:us-east-1:123456789:function:sage-test",
        "custom_key": "custom_value",
    }
    eventbridge_fallback.schedule_insight(
        name="sage-payload-test",
        schedule="rate(1 hour)",
        payload=payload,
    )

    rules = eventbridge_fallback.list_rules()
    assert len(rules) == 1
    assert rules[0]["payload"]["custom_key"] == "custom_value"


# ------------------------------------------------------------------
# AWS Credentials Detection Tests
# ------------------------------------------------------------------


def test_aws_credentials_detection_env_vars(monkeypatch):
    """Verify all adapters detect AWS credentials from environment."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    bedrock = BedrockProvider()
    dynamodb = DynamoDBStore(db_path=":memory:")
    s3 = S3Storage()
    eventbridge = EventBridgeTriggers()

    assert bedrock.is_mock is False
    assert dynamodb.is_fallback is False
    assert s3.is_fallback is False
    assert eventbridge.is_fallback is False


def test_aws_credentials_detection_no_env(monkeypatch):
    """Verify all adapters fall back when no AWS credentials are set."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    bedrock = BedrockProvider()
    dynamodb = DynamoDBStore(db_path=":memory:")
    s3 = S3Storage()
    eventbridge = EventBridgeTriggers()

    assert bedrock.is_mock is True
    assert dynamodb.is_fallback is True
    assert s3.is_fallback is True
    assert eventbridge.is_fallback is True


def test_aws_credentials_partial(monkeypatch):
    """Verify adapters fall back when only one credential is set."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    bedrock = BedrockProvider()
    assert bedrock.is_mock is True

    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    bedrock2 = BedrockProvider()
    assert bedrock2.is_mock is True
