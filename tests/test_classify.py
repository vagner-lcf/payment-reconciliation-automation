from src.matching import classify_matching_result


def test_classify_one_match():
    matching_accounts = [
        {"id": 1}
    ]

    classification = classify_matching_result(matching_accounts=matching_accounts)

    assert classification == "unique_match"


def test_classify_no_match():
    matching_accounts = []

    classification = classify_matching_result(matching_accounts=matching_accounts)
    
    assert classification == "no_match"
    

def test_classify_multiple_matches():
    matching_accounts = [
        {"id": 1},
        {"id": 2}
    ]

    classification = classify_matching_result(matching_accounts=matching_accounts)
    
    assert classification == "ambiguous"



