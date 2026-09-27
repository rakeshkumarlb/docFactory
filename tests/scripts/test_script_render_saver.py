import render_saver


def test_changed_field_mutates_a_plain_string_example():
    spec = {"fields": [{"name": "name", "example": '"Test-Env"'}]}
    assert render_saver.changed_field(spec) == ("name", "'Test-Env-changed'")


def test_changed_field_finds_a_string_leaf_inside_a_nested_dict_example():
    """A document field bound to a composed section has a dict example (see render_model.payload_literal);
    there is no top-level string to mutate, so changed_field must look inside it."""
    spec = {
        "fields": [
            {
                "name": "application_summary",
                "example": '{"application_name": "Test-App", "purpose": "Test purpose statement."}',
            },
        ],
    }
    name, changed = render_saver.changed_field(spec)
    assert name == "application_summary"
    assert changed == "{'application_name': 'Test-App-changed', 'purpose': 'Test purpose statement.'}"


def test_changed_field_finds_a_string_leaf_inside_a_list_of_dicts_example():
    spec = {"fields": [{"name": "kpis", "example": '[{"name": "Uptime", "target": "99.9%"}]'}]}
    name, changed = render_saver.changed_field(spec)
    assert name == "kpis"
    assert changed == "[{'name': 'Uptime-changed', 'target': '99.9%'}]"


def test_changed_field_skips_fields_with_no_string_leaf_and_uses_the_next_one():
    spec = {
        "fields": [
            {"name": "count", "example": "3"},
            {"name": "label", "example": '"Test"'},
        ],
    }
    assert render_saver.changed_field(spec) == ("label", "'Test-changed'")


def test_changed_field_is_none_when_no_field_has_a_mutable_string_leaf():
    spec = {"fields": [{"name": "count", "example": "3"}, {"name": "ratio", "example": "0.5"}]}
    assert render_saver.changed_field(spec) is None
