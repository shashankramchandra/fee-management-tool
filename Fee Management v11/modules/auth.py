"""Auth module - login, sessions, audit logging"""
from database.db import get_db
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session

def login_user(username, password):
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
        if not user:
            return {"success": False, "error": "Invalid username or password"}
        if not check_password_hash(user["password_hash"], password):
            return {"success": False, "error": "Invalid username or password"}
        conn.execute("UPDATE users SET last_login=datetime('now','localtime') WHERE id=?", (user["id"],))
        conn.commit()
        return {"success": True, "user": dict(user)}
    finally:
        conn.close()

def verify_password(username, password):
    """Just verify password without session - for protected actions"""
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,)).fetchone()
        if not user: return False
        return check_password_hash(user["password_hash"], password)
    finally:
        conn.close()

def get_all_users():
    conn = get_db()
    try:
        rows = conn.execute("SELECT id,username,role,display_name,is_active,created_at,last_login FROM users").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def create_user(username, password, role, display_name, created_by):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username,password_hash,role,display_name) VALUES (?,?,?,?)",
            (username, generate_password_hash(password), role, display_name)
        )
        conn.commit()
        audit(created_by, "management", "CREATE_USER", f"Created user: {username} role:{role}")
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def update_password(username, new_password, changed_by):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                     (generate_password_hash(new_password), username))
        conn.commit()
        audit(changed_by, "management", "CHANGE_PASSWORD", f"Changed password for: {username}")
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def toggle_user(username, active, changed_by):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET is_active=? WHERE username=?", (1 if active else 0, username))
        conn.commit()
        action = "ENABLE_USER" if active else "DISABLE_USER"
        audit(changed_by, "management", action, f"User: {username}")
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def audit(username, role, action, details, ip=""):
    """Log any action to audit_log"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO audit_log (username,role,action,details,ip_address) VALUES (?,?,?,?,?)",
            (username, role, action, details, ip)
        )
        conn.commit()
    except:
        pass
    finally:
        conn.close()


def rename_user(old_username, new_username, display_name, changed_by):
    """Rename a user (change login ID and/or display name)"""
    conn = get_db()
    try:
        if not new_username.strip():
            return {"success": False, "error": "Username cannot be empty"}
        # Check new username not taken
        existing = conn.execute("SELECT id FROM users WHERE username=? AND username!=?",
                                (new_username, old_username)).fetchone()
        if existing:
            return {"success": False, "error": f"Username '{new_username}' already exists"}
        conn.execute("UPDATE users SET username=?, display_name=? WHERE username=?",
                     (new_username.strip(), display_name.strip() or new_username.strip(), old_username))
        conn.commit()
        audit(changed_by, "management", "RENAME_USER",
              f"Renamed user: {old_username} -> {new_username}")
        return {"success": True}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

def get_audit_log(page=1, per_page=200, username="", action=""):
    conn = get_db()
    try:
        conditions = []
        params = []
        if username:
            conditions.append("username=?")
            params.append(username)
        if action:
            conditions.append("action LIKE ?")
            params.append(f"%{action}%")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        total = conn.execute(f"SELECT COUNT(*) FROM audit_log {where}", params).fetchone()[0]
        offset = (page-1)*per_page
        rows = conn.execute(
            f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params+[per_page, offset]
        ).fetchall()
        return {"total": total, "logs": [dict(r) for r in rows]}
    finally:
        conn.close()
