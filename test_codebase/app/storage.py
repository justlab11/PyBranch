import asyncio
import json


class Store:
    def __init__(self, path):
        self.path = path
        self._cache = {}

    def _key(self, ident):
        return str(ident)

    def save(self, ident, payload):
        self._cache[self._key(ident)] = payload
        self._flush()

    def _flush(self):
        with open(self.path, "w") as f:
            json.dump(self._cache, f)


async def save_async(store, ident, payload):
    await asyncio.sleep(0)
    store.save(ident, payload)
