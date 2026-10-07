"""Tests for the demo flow — chained MCP tool calls with honest halting."""
import os
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
import pytest_asyncio

# Set up temp DB before importing anything
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SAGE_DB_PATH"] = _tmp_db.name

from src.client.chained import SageMCPClient


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    """Start a real uvicorn server on an ephemeral port."""
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "src")
    env["SAGE_DB_PATH"] = _tmp_db.name

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "api.rest:app",
            "--host", "127.0.0.1",
            "--port", str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    url = f"http://127.0.0.1:{port}/mcp"
    for _ in range(50):
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=1)
            if resp.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("Server failed to start")

    yield url

    proc.terminate()
    proc.wait(timeout=5)


# A transcript that produces contacts, deals, and followups in mock mode
FULL_TRANSCRIPT = (
    "Hi, I'm calling about the project. John Smith from Acme Corp is interested "
    "in our solution. The budget is around $50,000. Let's follow up on 12/15/2026."
)

# A transcript with no capitalized name pairs — produces no contacts
NO_CONTACTS_TRANSCRIPT = (
    "Hello, I'm calling about the project. The budget is around $50,000."
)

# A transcript with a contact but no deals (no dollar amounts)
NO_DEALS_TRANSCRIPT = (
    "Hi, John Smith here. Let's talk about the project."
)


@pytest.mark.asyncio
async def test_chain_completes_all_five_steps(server_url):
    """The chain runs all five steps and returns success."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"
    assert result.completed_steps == 5
    assert len(result.steps) == 5
    assert result.synced_record_id is not None


@pytest.mark.asyncio
async def test_contact_id_passed_to_create_deal(server_url):
    """Step 3 (create_deal) uses the contact_id returned by step 2 (create_contact)."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"
    assert len(result.steps) == 5

    # Step 2 is create_contact, step 3 is create_deal
    step2 = result.steps[1]
    step3 = result.steps[2]

    assert step2["name"] == "create_contact"
    assert step3["name"] == "create_deal"

    contact_id_from_step2 = step2["result"]["id"]
    contact_id_in_step3 = step3["arguments"]["contact_id"]

    assert contact_id_in_step3 == contact_id_from_step2


@pytest.mark.asyncio
async def test_deal_id_passed_to_schedule_followup(server_url):
    """Step 4 (schedule_followup) uses the deal_id returned by step 3 (create_deal)."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"
    assert len(result.steps) == 5

    # Step 3 is create_deal, step 4 is schedule_followup
    step3 = result.steps[2]
    step4 = result.steps[3]

    assert step3["name"] == "create_deal"
    assert step4["name"] == "schedule_followup"

    deal_id_from_step3 = step3["result"]["id"]
    deal_id_in_step4 = step4["arguments"]["deal_id"]

    assert deal_id_in_step4 == deal_id_from_step3


@pytest.mark.asyncio
async def test_syncs_to_local_with_real_record_id(server_url):
    """Step 5 syncs to local CRM and returns a real loc_d_ record id."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"
    assert result.synced_record_id is not None
    assert result.synced_record_id.startswith("loc_d_")

    # Verify the sync step has provenance "local"
    step5 = result.steps[4]
    assert step5["name"] == "sync_to_crm"
    assert step5["provenance"] == "local"


@pytest.mark.asyncio
async def test_idempotency_key_uses_deal_id(server_url):
    """Step 5 uses idempotency_key = f'chain-{deal_id}'."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"

    deal_id = result.steps[2]["result"]["id"]
    idempotency_key = result.steps[4]["arguments"]["idempotency_key"]

    assert idempotency_key == f"chain-{deal_id}"


@pytest.mark.asyncio
async def test_halts_when_no_contacts_extracted(server_url):
    """Chain halts at step 1 when extraction yields no contacts."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(NO_CONTACTS_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "incomplete"
    assert result.completed_steps == 1
    assert "no contacts" in result.reason.lower()
    assert len(result.steps) == 1
    assert result.steps[0]["name"] == "extract_from_call"


@pytest.mark.asyncio
async def test_halts_when_no_deals_extracted(server_url):
    """Chain halts at step 3 when extraction yields contacts but no deals."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(NO_DEALS_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "incomplete"
    assert result.completed_steps == 2
    assert "no deals" in result.reason.lower()
    assert len(result.steps) == 2
    assert result.steps[0]["name"] == "extract_from_call"
    assert result.steps[1]["name"] == "create_contact"


@pytest.mark.asyncio
async def test_nothing_hardcoded_ids_match(server_url):
    """Ids in later steps equal ids returned by earlier steps — nothing is hardcoded."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"
    assert len(result.steps) == 5

    # Extract ids from each step
    contact_id = result.steps[1]["result"]["id"]
    deal_id = result.steps[2]["result"]["id"]

    # Step 3 uses contact_id from step 2
    assert result.steps[2]["arguments"]["contact_id"] == contact_id

    # Step 4 uses contact_id from step 2 and deal_id from step 3
    assert result.steps[3]["arguments"]["contact_id"] == contact_id
    assert result.steps[3]["arguments"]["deal_id"] == deal_id

    # Step 5 uses idempotency_key derived from deal_id
    assert result.steps[4]["arguments"]["idempotency_key"] == f"chain-{deal_id}"


@pytest.mark.asyncio
async def test_sync_result_has_local_provenance(server_url):
    """The sync step result has provenance 'local'."""
    from src.client.demo_flow import run_agentic_loop

    result = await run_agentic_loop(FULL_TRANSCRIPT, server=server_url, target="local")

    assert result.status == "success"

    step5 = result.steps[4]
    assert step5["provenance"] == "local"
    assert step5["result"]["status"] == "success"
    assert step5["result"]["target"] == "local"


def teardown_module():
    """Clean up temporary database."""
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass
