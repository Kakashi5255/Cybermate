import re
from typing import Tuple, List, Dict

URGENT = r"\b(urgent|immediately|act\s*now|final\s*notice|verify)\b"
PAY    = r"\b(pay|payment|fee|transfer|send\s*money|gift\s*card|deposit)\b"
SHORT  = r"(bit\.ly|tinyurl\.com|t\.co|ow\.ly|is\.gd|goo\.gl)"
BRAND  = r"\b(ato|mygov|auspost|paypal|apple|dhl|commbank|anz|nab|westpac)\b"

def eval_rules(text: str) -> Tuple[int, List[Dict], List[str]]:
    t = text.lower()
    score = 0; hits = []; reasons = []
    if re.search(URGENT, t): score += 2; hits.append({"type":"urgency"}); reasons.append("Uses urgency.")
    if re.search(PAY, t):    score += 2; hits.append({"type":"payment"}); reasons.append("Requests payment/transfer.")
    if re.search(SHORT, t):  score += 1; hits.append({"type":"short_link"}); reasons.append("Contains a shortened link.")
    if re.search(BRAND, t):  score += 1; hits.append({"type":"brand_ref"}); reasons.append("Mentions a well-known brand; verify via official site.")
    return score, hits, reasons
