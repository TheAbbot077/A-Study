from decimal import Decimal
from apps.self_study.domain.evidence_mapping import coverage_state,fingerprint,lexical_score,mapping_decision,normalize
def test_manifest_fingerprint_is_ordered_and_ignores_nothing_implicit():
 assert fingerprint({"resources":["a","b"]})==fingerprint({"resources":["a","b"]})
 assert fingerprint({"resources":["a","b"]})!=fingerprint({"resources":["b","a"]})
def test_normalization_and_lexical_scoring_are_deterministic():
 assert normalize("  Linear\nEQUATIONS ")=="linear equations"
 assert lexical_score("linear equations","Linear equations")==Decimal("1.00000")
def test_candidate_rank_is_not_authority_and_hard_constraints_win():
 assert mapping_decision("PROSE","CONCEPT",Decimal("1"),True,safe=False)[0]=="REJECTED"
 assert mapping_decision("HEADING","CONCEPT",Decimal("1"),False)[0]=="REJECTED"
 assert mapping_decision("PROSE","CONCEPT",Decimal(".5"),True)[0]=="PROPOSED"
def test_coverage_states_and_duplicate_source_semantics():
 assert coverage_state([],True)[0]=="MISSING"
 assert coverage_state([],False)[0]=="NOT_APPLICABLE"
 rows=[{"status":"ACCEPTED","classification":"DIRECT","source":"same"},{"status":"ACCEPTED","classification":"DIRECT","source":"same"}]
 assert coverage_state(rows)[0]=="COVERED"
 assert len({x["source"] for x in rows})==1
 assert coverage_state([{"status":"ACCEPTED","classification":"CONFLICTING","source":"a"}])[0]=="CONFLICTING"
