import hashlib,json,re,unicodedata
from collections import Counter
from decimal import Decimal

VERSIONS={"evidence":"pi-6f.5-evidence-v1","normalization":"pi-6f.5-normalize-v1","duplicates":"pi-6f.5-duplicates-v1","candidates":"pi-6f.5-lexical-v1","acceptance":"pi-6f.5-accept-v1","contradiction":"pi-6f.5-conflict-v1","coverage":"pi-6f.5-coverage-v1"}
FINDING_CATALOG={
 "MAPPING_GRAPH_NOT_PUBLISHED":("BLOCKER",True,"RUN"),"MAPPING_EXTRACTION_NOT_READY":("BLOCKER",True,"SOURCE"),
 "SOURCE_RETIRED":("BLOCKER",True,"SOURCE"),"SOURCE_UNLICENSED":("BLOCKER",True,"SOURCE"),"SOURCE_UNSAFE":("BLOCKER",True,"SOURCE"),
 "EVIDENCE_CITATION_INCOMPLETE":("BLOCKER",True,"EVIDENCE"),"EVIDENCE_TEXT_EMPTY":("WARNING",False,"EVIDENCE"),"EVIDENCE_HEADING_ONLY":("INFO",False,"EVIDENCE"),"EVIDENCE_DUPLICATE":("INFO",False,"EVIDENCE"),
 "MAPPING_NO_CANDIDATE":("WARNING",False,"EVIDENCE"),"MAPPING_LOW_LEXICAL_SUPPORT":("WARNING",False,"MAPPING"),"MAPPING_AMBIGUOUS":("WARNING",False,"MAPPING"),"MAPPING_NODE_TYPE_INCOMPATIBLE":("ERROR",True,"MAPPING"),"MAPPING_REQUIRES_REVIEW":("WARNING",False,"MAPPING"),"MAPPING_CONFLICT_DETECTED":("BLOCKER",True,"MAPPING"),
 "COVERAGE_NODE_MISSING":("BLOCKER",True,"GRAPH_NODE"),"COVERAGE_NODE_PARTIAL":("WARNING",False,"GRAPH_NODE"),"COVERAGE_NODE_CONFLICTING":("BLOCKER",True,"GRAPH_NODE"),"COVERAGE_DIRECT_EVIDENCE_MISSING":("WARNING",False,"GRAPH_NODE"),"COVERAGE_DUPLICATE_INFLATION_PREVENTED":("INFO",False,"EVALUATION"),"COVERAGE_STALE_MAPPING_EXCLUDED":("INFO",False,"EVALUATION"),
 "CONFLICT_SOURCE_TO_SOURCE":("BLOCKER",True,"MAPPING"),"CONFLICT_SOURCE_TO_CURRICULUM":("BLOCKER",True,"MAPPING"),"CONFLICT_REQUIRES_REVIEW":("BLOCKER",True,"MAPPING"),
}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def fingerprint(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def normalize(text):return re.sub(r"\s+"," ",unicodedata.normalize("NFKC",text).casefold()).strip()
def tokens(text):return set(re.findall(r"[\w'-]+",normalize(text)))
def lexical_score(text,title,description=""):
 source=tokens(text);target=tokens(f"{title} {description}")
 return Decimal("0") if not source or not target else (Decimal(len(source&target))/Decimal(len(target))).quantize(Decimal(".00001"))
def compatible(evidence_type,node_type):
 if evidence_type=="QUESTION":return node_type in {"ASSESSMENT_OBJECTIVE","COMPETENCY","CONCEPT"}
 if evidence_type=="HEADING":return False
 return node_type in {"OUTCOME","COMPETENCY","CONCEPT","ASSESSMENT_OBJECTIVE","EXTERNAL_PREREQUISITE"}
def mapping_decision(evidence_type,node_type,score,substantive,safe=True,licensed=True):
 if not safe:return "REJECTED","OUT_OF_SCOPE",["SOURCE_UNSAFE"]
 if not licensed:return "REJECTED","OUT_OF_SCOPE",["SOURCE_UNLICENSED"]
 if not substantive or evidence_type=="HEADING":return "REJECTED","SUPPLEMENTARY",["EVIDENCE_HEADING_ONLY"]
 if not compatible(evidence_type,node_type):return "REJECTED","OUT_OF_SCOPE",["MAPPING_NODE_TYPE_INCOMPATIBLE"]
 if score<Decimal(".35"):return "REJECTED","OUT_OF_SCOPE",["MAPPING_LOW_LEXICAL_SUPPORT"]
 if score<Decimal(".65"):return "PROPOSED","SUPPORTING",["MAPPING_REQUIRES_REVIEW"]
 classification="ASSESSMENT_SUPPORT" if evidence_type=="QUESTION" else "DIRECT" if score>=Decimal(".8") else "SUPPORTING"
 return "ACCEPTED",classification,["LEXICAL_GROUNDED"]
def coverage_state(mappings,applicable=True):
 if not applicable:return "NOT_APPLICABLE",[]
 accepted=[x for x in mappings if x["status"]=="ACCEPTED"]
 if any(x["classification"]=="CONFLICTING" for x in accepted):return "CONFLICTING",["COVERAGE_NODE_CONFLICTING"]
 substantive=[x for x in accepted if x["classification"] in {"DIRECT","SUPPORTING","PREREQUISITE_SUPPORT","ASSESSMENT_SUPPORT"}]
 sources={x["source"] for x in substantive};direct=sum(x["classification"]=="DIRECT" for x in substantive)
 if direct and sources:return "COVERED",[]
 if substantive:return "PARTIAL",["COVERAGE_DIRECT_EVIDENCE_MISSING"]
 if any(x["classification"]=="SUPPLEMENTARY" for x in accepted):return "SUPPLEMENTARY",["MAPPING_SUPPLEMENTARY_ONLY"]
 return "MISSING",["COVERAGE_NODE_MISSING"]
