from datetime import datetime, timedelta, timezone
import pytest
from serverguard.database.storage import Storage

@pytest.mark.asyncio
async def test_expired_and_deleted_are_not_public(tmp_path):
    store = Storage(tmp_path / 'test.sqlite3'); await store.init()
    live = await store.create('Live', 'body', 'Update', None, None)
    await store.create('Expired', 'body', 'Release', None, datetime.now(timezone.utc) - timedelta(days=1))
    deleted = await store.create('Deleted', 'body', 'Security', None, None); assert await store.delete(deleted)
    posts = await store.public_posts()
    assert [post['id'] for post in posts] == [live]

@pytest.mark.asyncio
async def test_future_expiry_is_public(tmp_path):
    store = Storage(tmp_path / 'test.sqlite3'); await store.init()
    post = await store.create('Future', 'body', 'Announcement', None, datetime.now(timezone.utc) + timedelta(days=1))
    assert (await store.public_posts())[0]['id'] == post
