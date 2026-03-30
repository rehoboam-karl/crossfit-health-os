"""
Tests for app/db/database.py
Tests connection pool management, get_connection, execute, fetchone, fetchall, init_db.

NOTE: conftest.py has an autouse mock_database fixture that patches db functions.
      We save references to the originals at module-load time (before any test
      runs) so we can test the real logic here.
"""
import pytest
from unittest.mock import patch, MagicMock, call
from contextlib import contextmanager

# ── Save original function references before autouse patching ──────────────
import app.db.database as _db_module

_real_get_pool = _db_module.get_pool
_real_close_pool = _db_module.close_pool
_real_get_connection = _db_module.get_connection
_real_execute = _db_module.execute
_real_fetchone = _db_module.fetchone
_real_fetchall = _db_module.fetchall
_real_init_db = _db_module.init_db


# ── helpers ────────────────────────────────────────────────────────────────

def _make_cursor(fetchone_result=None, fetchall_result=None, rowcount=1):
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = fetchone_result
    cur.fetchall.return_value = fetchall_result or []
    cur.rowcount = rowcount
    return cur


def _make_conn(cursor=None):
    conn = MagicMock()
    conn.cursor.return_value = cursor or _make_cursor()
    return conn


# ── TestGetPool ────────────────────────────────────────────────────────────

class TestGetPool:
    """Test get_pool() original function"""

    def test_creates_pool_with_full_url(self):
        """Test pool is created when DATABASE_URL contains ://"""
        mock_pool = MagicMock()
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = None  # Force re-creation

        try:
            with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@myhost:5433/mydb"}):
                with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool) as cls:
                    result = _real_get_pool()

            assert result is mock_pool
            kw = cls.call_args[1]
            assert kw["host"] == "myhost"
            assert kw["port"] == "5433"
            assert kw["user"] == "user"
            assert kw["password"] == "pass"
            assert kw["database"] == "mydb"
        finally:
            _db_module.connection_pool = original_pool

    def test_creates_pool_with_defaults_when_no_scheme(self):
        """Test pool uses defaults when URL has no :// scheme"""
        mock_pool = MagicMock()
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = None

        try:
            with patch.dict("os.environ", {"DATABASE_URL": "notaurl"}):
                with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool) as cls:
                    result = _real_get_pool()

            assert result is mock_pool
            kw = cls.call_args[1]
            assert kw["user"] == "postgres"
            assert kw["host"] == "127.0.0.1"
            assert kw["port"] == "5432"
        finally:
            _db_module.connection_pool = original_pool

    def test_returns_existing_pool_without_recreating(self):
        """Test get_pool returns existing pool without creating new one"""
        mock_pool = MagicMock()
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = mock_pool

        try:
            with patch("psycopg2.pool.ThreadedConnectionPool") as cls:
                result = _real_get_pool()

            cls.assert_not_called()
            assert result is mock_pool
        finally:
            _db_module.connection_pool = original_pool

    def test_url_without_port_defaults_to_5432(self):
        """Test URL parsing defaults port to 5432 when omitted"""
        mock_pool = MagicMock()
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = None

        try:
            with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pw@host/dbname"}):
                with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool) as cls:
                    _real_get_pool()

            kw = cls.call_args[1]
            assert kw["port"] == "5432"
            assert kw["database"] == "dbname"
        finally:
            _db_module.connection_pool = original_pool


# ── TestClosePool ──────────────────────────────────────────────────────────

class TestClosePool:
    """Test close_pool() original function"""

    def test_closes_pool_and_sets_to_none(self):
        mock_pool = MagicMock()
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = mock_pool

        try:
            _real_close_pool()
            mock_pool.closeall.assert_called_once()
            assert _db_module.connection_pool is None
        finally:
            _db_module.connection_pool = original_pool

    def test_does_nothing_when_no_pool(self):
        original_pool = _db_module.connection_pool
        _db_module.connection_pool = None

        try:
            _real_close_pool()  # Should not raise
            assert _db_module.connection_pool is None
        finally:
            _db_module.connection_pool = original_pool


# ── TestGetConnection ──────────────────────────────────────────────────────

class TestGetConnection:
    """Test get_connection() original context manager"""

    def test_yields_connection_and_commits(self):
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(_db_module, "get_pool", return_value=mock_pool):
            with _real_get_connection() as conn:
                assert conn is mock_conn

        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_rolls_back_on_exception(self):
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(_db_module, "get_pool", return_value=mock_pool):
            with pytest.raises(ValueError):
                with _real_get_connection():
                    raise ValueError("intentional")

        mock_conn.rollback.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_always_returns_connection_to_pool(self):
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch.object(_db_module, "get_pool", return_value=mock_pool):
            try:
                with _real_get_connection():
                    raise RuntimeError("boom")
            except RuntimeError:
                pass

        mock_pool.putconn.assert_called_once_with(mock_conn)


# ── TestExecute ────────────────────────────────────────────────────────────

class TestExecute:
    """Test execute() original function"""

    def test_returns_rowcount(self):
        cur = _make_cursor(rowcount=3)
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            result = _real_execute("DELETE FROM t WHERE x = %s", "val")

        assert result == 3
        cur.execute.assert_called_once_with("DELETE FROM t WHERE x = %s", ("val",))

    def test_passes_empty_args_tuple(self):
        cur = _make_cursor(rowcount=1)
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            _real_execute("TRUNCATE t")

        cur.execute.assert_called_once_with("TRUNCATE t", ())


# ── TestFetchone ───────────────────────────────────────────────────────────

class TestFetchone:
    """Test fetchone() original function"""

    def test_returns_row(self):
        row = (1, "test@example.com")
        cur = _make_cursor(fetchone_result=row)
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            result = _real_fetchone("SELECT * FROM t WHERE e = %s", "test@example.com")

        assert result == row

    def test_returns_none_when_not_found(self):
        cur = _make_cursor(fetchone_result=None)
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            result = _real_fetchone("SELECT * FROM t WHERE id = %s", 999)

        assert result is None


# ── TestFetchall ───────────────────────────────────────────────────────────

class TestFetchall:
    """Test fetchall() original function"""

    def test_returns_multiple_rows(self):
        rows = [(1, "a@b.com"), (2, "c@d.com")]
        cur = _make_cursor(fetchall_result=rows)
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            result = _real_fetchall("SELECT id, email FROM users")

        assert result == rows

    def test_returns_empty_list(self):
        cur = _make_cursor(fetchall_result=[])
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            result = _real_fetchall("SELECT * FROM empty")

        assert result == []

    def test_passes_multiple_args(self):
        cur = _make_cursor(fetchall_result=[])
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            _real_fetchall("SELECT * FROM t WHERE a=%s AND b=%s", "x", "y")

        cur.execute.assert_called_once_with("SELECT * FROM t WHERE a=%s AND b=%s", ("x", "y"))


# ── TestInitDb ─────────────────────────────────────────────────────────────

class TestInitDb:
    """Test init_db() original function"""

    def test_creates_users_table(self):
        cur = _make_cursor()
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            _real_init_db()

        cur.execute.assert_called_once()
        sql = cur.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS users" in sql

    def test_schema_includes_key_columns(self):
        cur = _make_cursor()
        conn = _make_conn(cur)

        @contextmanager
        def _mock_conn():
            yield conn

        with patch.object(_db_module, "get_connection", _mock_conn):
            _real_init_db()

        sql = cur.execute.call_args[0][0]
        for col in ("email", "password_hash", "fitness_level", "goals"):
            assert col in sql, f"Column '{col}' missing from init_db SQL"
