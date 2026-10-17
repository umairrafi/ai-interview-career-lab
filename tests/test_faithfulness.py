from ledgerlab.faithfulness import is_faithful, unsupported_numbers


def test_an_invented_number_is_not_supported():
    context = ["A domestic wire fee is 25 dirhams."]
    assert is_faithful("The domestic wire fee is 25 dirhams.", context)
    assert unsupported_numbers("The domestic wire fee is 99 dirhams.", context) == ["99"]
