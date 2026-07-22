import hashlib, json
from dataclasses import dataclass
from decimal import Decimal

ALGORITHM_VERSION="pi-6f.4-adaptive-rules-v1"; SCORING_VERSION="pi-6f.4-deterministic-score-v1"; PROFILE_VERSION="pi-6f.4-placement-v1"
DEMONSTRATED_THRESHOLD=Decimal("0.75"); CONFIDENCE_THRESHOLD=Decimal("0.65")

def canonical_hash(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def validate_response(item_type,schema,payload):
    if not isinstance(payload,dict) or set(payload)-{"answer"}: raise ValueError("Response payload is invalid.")
    answer=payload.get("answer")
    if item_type=="SINGLE_CHOICE" and (not isinstance(answer,str) or answer not in schema.get("choices",[])): raise ValueError("A permitted choice is required.")
    if item_type=="MULTIPLE_CHOICE" and (not isinstance(answer,list) or any(x not in schema.get("choices",[]) for x in answer)): raise ValueError("Permitted choices are required.")
    if item_type=="NUMERIC" and (isinstance(answer,bool) or not isinstance(answer,(int,float))): raise ValueError("A numeric answer is required.")
    if item_type in {"SHORT_STRUCTURED","ORDERING","MATCHING"} and answer is None: raise ValueError("An answer is required.")
def score_response(item_type,spec,payload):
    answer=payload["answer"]; expected=spec.get("answer")
    if item_type=="NUMERIC": correct=abs(Decimal(str(answer))-Decimal(str(expected))) <= Decimal(str(spec.get("tolerance",0)))
    elif item_type in {"MULTIPLE_CHOICE","ORDERING"}: correct=list(answer)==list(expected) if item_type=="ORDERING" else set(answer)==set(expected)
    else: correct=answer==expected
    return {"correctness":correct,"normalized_score":"1.0000" if correct else "0.0000","evidence_strength":"1.0000","scoring_confidence":"1.0000"}
def estimate_classification(correct,total):
    if total==0:return Decimal(0),Decimal(0),Decimal(1),"UNOBSERVED"
    estimate=Decimal(correct)/Decimal(total); confidence=min(Decimal("0.95"),Decimal("0.35")+Decimal(total)*Decimal("0.20")); uncertainty=Decimal(1)-confidence
    if total<2: status="TENTATIVE"
    elif estimate>=DEMONSTRATED_THRESHOLD and confidence>=CONFIDENCE_THRESHOLD: status="DEMONSTRATED"
    elif estimate<=Decimal("0.25") and confidence>=CONFIDENCE_THRESHOLD: status="NOT_DEMONSTRATED"
    else: status="UNCERTAIN"
    return estimate.quantize(Decimal(".0001")),confidence.quantize(Decimal(".0001")),uncertainty.quantize(Decimal(".0001")),status

@dataclass(frozen=True)
class ItemCandidate: id:str; domain_key:str; difficulty:int; importance:int; uncertainty:Decimal; presented:bool
def select_candidate(candidates,answered_count):
    eligible=[x for x in candidates if not x.presented]
    if not eligible:return None
    # Uncovered domains first, then uncertainty and graph importance, with stable identity tie-break.
    return sorted(eligible,key=lambda x:(-int(x.uncertainty*1000),-x.importance,abs(x.difficulty-(2 if answered_count<3 else 3)),x.id))[0]
def profile_fingerprint(**parts): return canonical_hash(parts)
