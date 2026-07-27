from gene_explorer.prompts import build_system_prompt


def test_prompt_lists_supplied_cancers():
    p = build_system_prompt(["breast", "lung"])
    assert "breast" in p and "lung" in p


def test_prompt_states_the_refusal_sentence():
    p = build_system_prompt(["breast"])
    assert "I don't have data for that cancer type in this dataset." in p


def test_prompt_requires_chaining():
    p = build_system_prompt(["breast"])
    assert "get_targets" in p and "get_expressions" in p
