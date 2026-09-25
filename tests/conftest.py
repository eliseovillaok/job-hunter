import pytest

from web import persist


@pytest.fixture(autouse=True)
def memory_store():
    """Cada test arranca con cuentas y datos vacíos, en memoria (sin Supabase ni red)."""
    store = persist.MemoryStore()
    persist.use(store)
    yield store
    persist.use(None)
