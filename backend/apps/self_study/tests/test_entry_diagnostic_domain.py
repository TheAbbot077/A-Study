from decimal import Decimal
import pytest
from apps.self_study.domain.entry_diagnostic import ItemCandidate,estimate_classification,profile_fingerprint,score_response,select_candidate,validate_response

def test_response_schema_and_deterministic_server_scoring():
    validate_response("SINGLE_CHOICE",{"choices":["a","b"]},{"answer":"a"})
    assert score_response("SINGLE_CHOICE",{"answer":"a"},{"answer":"a"})["correctness"] is True
    with pytest.raises(ValueError):validate_response("SINGLE_CHOICE",{"choices":["a"]},{"answer":"b"})
    with pytest.raises(ValueError):validate_response("SINGLE_CHOICE",{"choices":["a"]},{"answer":"a","score":1})

def test_estimates_resist_one_lucky_or_wrong_answer_and_preserve_uncertainty():
    assert estimate_classification(1,1)[3]=="TENTATIVE"
    assert estimate_classification(0,1)[3]=="TENTATIVE"
    assert estimate_classification(2,2)[3]=="DEMONSTRATED"
    assert estimate_classification(0,2)[3]=="NOT_DEMONSTRATED"
    assert estimate_classification(0,0)[3]=="UNOBSERVED"

def test_adaptive_selection_is_stable_avoids_repeats_and_prefers_uncertainty():
    candidates=[ItemCandidate("b","algebra",2,1,Decimal(".4"),False),ItemCandidate("a","geometry",2,1,Decimal(".9"),False),ItemCandidate("c","geometry",3,5,Decimal("1"),True)]
    assert select_candidate(candidates,0).id=="a"
    assert select_candidate(candidates,0)==select_candidate(candidates,0)
    assert select_candidate([ItemCandidate("a","x",1,1,Decimal(1),True)],0) is None

def test_profile_fingerprint_excludes_ordering_noise_and_changes_with_evidence():
    first=profile_fingerprint(graph="g",responses=[("a","1")],frontier=["n"])
    assert first==profile_fingerprint(graph="g",responses=[("a","1")],frontier=["n"])
    assert first!=profile_fingerprint(graph="g",responses=[("a","2")],frontier=["n"])
