from gene_explorer.auth import _is_valid


def test_valid_key_accepted():
    assert _is_valid("key-b", ["key-a", "key-b"])


def test_invalid_key_rejected():
    assert not _is_valid("key-c", ["key-a", "key-b"])


def test_no_keys_means_nothing_matches():
    assert not _is_valid("anything", [])


def test_non_ascii_candidate_is_rejected_not_raised():
    # Starlette decodes header bytes as latin-1, so a byte above 0x7F yields a
    # non-ASCII str. hmac.compare_digest raises TypeError on such a str, which
    # would surface as a 500 instead of a 401.
    high_byte_header = b"k\xe9y".decode("latin-1")
    assert not _is_valid(high_byte_header, ["key-a"])


def test_unicode_key_still_matches_itself():
    assert _is_valid("clé-secrète", ["clé-secrète"])
