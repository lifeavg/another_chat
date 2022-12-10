from datetime import datetime, timedelta, timezone

import pytest
from models_fixtures import active_user, engine, session


@pytest.mark.asyncio
async def test_user_created_timestamp(active_user):
    start_range = datetime.now(timezone.utc) - timedelta(minutes=1)
    end_range = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert active_user.created_timestamp > start_range
    assert active_user.created_timestamp < end_range
