"""
Supabase REST client — replaces SQLAlchemy + psycopg2.
Uses the Supabase PostgREST HTTP API which works over HTTPS (port 443).
No database password needed — uses the anon JWT key.
"""
import httpx
from typing import Any, Dict, List, Optional
from app.config import settings

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_ANON_KEY = settings.SUPABASE_ANON_KEY

# Prefer the service-role key when available; fall back to the legacy service key or anon key.
SUPABASE_SERVICE_KEY = settings.supabase_service_key_value

REST_URL = f"{SUPABASE_URL}/rest/v1"

def _headers(use_service_key: bool = True) -> Dict[str, str]:
    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


class SupabaseTable:
    """Thin wrapper around a single PostgREST table endpoint."""
    
    def __init__(self, table: str, use_service_key: bool = True):
        self.table = table
        self.url = f"{REST_URL}/{table}"
        self.use_service_key = use_service_key
    
    def _h(self) -> Dict[str, str]:
        return _headers(self.use_service_key)

    @staticmethod
    def _normalize_filter_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            if value in {"is.null", "is.not.null", "not.null"}:
                return value
            if value.startswith(("eq.", "neq.", "lt.", "lte.", "gt.", "gte.", "like.", "ilike.", "in.", "cs.", "cd.", "ov.", "sl.", "sr.", "nx.", "adj.", "not.", "is.")):
                return value
            return f"eq.{value}"
        return f"eq.{value}"
    
    def select(self, columns: str = "*", **filters) -> List[Dict]:
        params = {"select": columns}
        for k, v in filters.items():
            normalized = self._normalize_filter_value(v)
            if normalized:
                params[k] = normalized
        with _client() as c:
            r = c.get(self.url, headers=self._h(), params=params)
            r.raise_for_status()
            return r.json()
    
    def select_raw(self, query_params: Dict[str, str], columns: str = "*") -> List[Dict]:
        params = {"select": columns, **query_params}
        with _client() as c:
            r = c.get(self.url, headers=self._h(), params=params)
            r.raise_for_status()
            return r.json()
    
    def get_one(self, **filters) -> Optional[Dict]:
        results = self.select(**filters)
        return results[0] if results else None
    
    def insert(self, data: Dict) -> Dict:
        with _client() as c:
            r = c.post(self.url, headers=self._h(), json=data)
            r.raise_for_status()
            result = r.json()
            return result[0] if isinstance(result, list) else result
    
    def insert_many(self, data: List[Dict]) -> List[Dict]:
        with _client() as c:
            r = c.post(self.url, headers=self._h(), json=data)
            r.raise_for_status()
            return r.json()
    
    def update(self, filters: Dict[str, str], data: Dict) -> List[Dict]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        with _client() as c:
            r = c.patch(self.url, headers=self._h(), params=params, json=data)
            r.raise_for_status()
            return r.json()
    
    def delete(self, **filters) -> List[Dict]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        with _client() as c:
            r = c.delete(self.url, headers=self._h(), params=params)
            r.raise_for_status()
            return r.json()
    
    def rpc(self, func_name: str, params: Dict = {}) -> Any:
        url = f"{SUPABASE_URL}/rest/v1/rpc/{func_name}"
        with _client() as c:
            r = c.post(url, headers=self._h(), json=params)
            r.raise_for_status()
            return r.json()


def execute_sql_via_rpc(sql: str) -> Any:
    """Execute raw SQL via a stored procedure (only if exec_sql is set up)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    with _client() as c:
        r = c.post(url, headers=_headers(), json={"query": sql})
        r.raise_for_status()
        return r.json()


# Convenience table instances
users_table = SupabaseTable("users")
locations_table = SupabaseTable("locations")
products_table = SupabaseTable("products")
inventory_table = SupabaseTable("inventory")
orders_table = SupabaseTable("orders")
order_items_table = SupabaseTable("order_items")
delivery_routes_table = SupabaseTable("delivery_routes")
route_stops_table = SupabaseTable("route_stops")
low_stock_alerts_table = SupabaseTable("low_stock_alerts")
