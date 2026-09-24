"""
Utilidades de contraseñas.
Mantiene compatibilidad con el sistema actual (texto plano en settings)
pero agrega hashing opcional para futuras mejoras.
"""
import hashlib
import os
import base64

# Flag global: si se activa, las nuevas contraseñas se guardan hasheadas
# (por defecto se mantiene texto plano para no romper compatibilidad).
USE_HASHING = False


def hash_password(password):
    """Devuelve un hash seguro (PBKDF2-SHA256) con salt aleatorio."""
    if password is None:
        return ""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'), salt, 100000)
    return "pbkdf2$" + base64.b64encode(salt).decode('ascii') + "$" + base64.b64encode(dk).decode('ascii')


def verify_password(password, stored):
    """Verifica una contraseña contra un valor almacenado (hash o texto plano)."""
    if not stored:
        return False
    if stored.startswith("pbkdf2$"):
        try:
            _, salt_b64, dk_b64 = stored.split("$", 2)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(dk_b64)
            dk = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'), salt, 100000)
            return dk == expected
        except Exception:
            return False
    # Compatibilidad: contraseña en texto plano
    return str(password) == str(stored)


def store_password(db_manager, key, password):
    """Guarda la contraseña (hash si USE_HASHING, texto plano si no)."""
    if not password:
        db_manager.set_setting(key, "")
        return
    if USE_HASHING:
        db_manager.set_setting(key, hash_password(password))
    else:
        db_manager.set_setting(key, str(password))


def check_password(db_manager, key, password):
    """Verifica la contraseña almacenada en la clave dada."""
    stored = db_manager.get_setting(key, "") or ""
    if not stored:
        return False
    return verify_password(password, stored)


def has_password(db_manager, key="startup_password"):
    """Indica si hay una contraseña configurada."""
    return bool((db_manager.get_setting(key, "") or "").strip())