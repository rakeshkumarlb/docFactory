import hashlib

from docfactory.canonical import canonical_json, sha256_hex


def test_key_order_does_not_change_output():
    assert canonical_json({"b": 1, "a": {"y": 2, "x": [3, {"d": 4, "c": 5}]}}) == canonical_json(
        {"a": {"x": [3, {"c": 5, "d": 4}], "y": 2}, "b": 1}
    )


def test_output_has_sorted_keys_and_no_whitespace():
    assert canonical_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


def test_non_ascii_is_kept_as_utf8():
    assert canonical_json({"name": "Küche"}) == '{"name":"Küche"}'


def test_list_order_is_significant():
    assert canonical_json([1, 2]) != canonical_json([2, 1])


def test_known_hash():
    # SHA-256 of the empty string and of "abc" are published test vectors.
    assert sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_hash_is_of_the_utf8_bytes():
    assert sha256_hex("Küche") == hashlib.sha256("Küche".encode("utf-8")).hexdigest()
