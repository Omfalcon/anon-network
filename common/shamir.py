# common/shamir.py

def split_ip(ip: str):
    return ip.split(".")


def reconstruct_ip(fragments_in_order: list[str]) -> str:
    """Rebuild dotted IPv4 from ordered octet strings (Phase 5 reconstruction)."""
    return ".".join(fragments_in_order)