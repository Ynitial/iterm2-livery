from livery.title import root_name, tab_title


def test_root_name_is_basename():
    assert root_name("/Users/yoni/Sites/vanderkrabben") == "vanderkrabben"


def test_tab_title_with_and_without_custom():
    assert tab_title("vanderkrabben", "dev") == "vanderkrabben | dev"
    assert tab_title("vanderkrabben", None) == "vanderkrabben"
    assert tab_title("vanderkrabben", "") == "vanderkrabben"
