from gene_explorer.auth import _is_valid


def test_valid_key_accepted():
    assert _is_valid("key-b", ["key-a", "key-b"])


def test_invalid_key_rejected():
    assert not _is_valid("key-c", ["key-a", "key-b"])


def test_no_keys_means_nothing_matches():
    assert not _is_valid("anything", [])
