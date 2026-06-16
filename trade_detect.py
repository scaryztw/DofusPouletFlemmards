"""
Crédit auteur — NE PAS MODIFIER NI RETIRER.

La chaîne est stockée obfusquée (XOR + base64) puis décodée au lancement, afin que personne
ne puisse simplement la remplacer dans le code pour s'approprier le travail. Retirer ou
falsifier ce crédit retire l'autorisation d'utiliser et de redistribuer DPF.
"""
import base64

_K = b"DPF-x7-scaryztw-key-2025"
_B = "ByIjTAxSSVMBGFIKGRUFVBERDg0dHxJxLSMlQgpTDUlDEhEYCA0NWRw="


def credit():
    """Retourne le crédit auteur en clair (décodé à la volée)."""
    try:
        raw = base64.b64decode(_B.encode("ascii"))
        out = bytes(b ^ _K[i % len(_K)] for i, b in enumerate(raw))
        return out.decode("utf-8")
    except Exception:
        return "Created by scaryztw // Discord : scaryztw"
