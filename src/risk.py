RISK_KEYWORDS = {
    "refund": ("refund", "return", "chargeback", "退款", "退费"),
    "compensation": ("compensation", "赔偿", "补偿", "credit"),
    "billing": ("billing", "invoice", "payment", "付款", "账单", "发票"),
    "legal": ("legal", "contract", "lawsuit", "合同", "法律", "起诉"),
    "privacy": ("privacy", "personal data", "gdpr", "隐私", "个人信息"),
}


def classify_risks(question: str) -> list[str]:
    lowered = question.lower()
    return [
        risk
        for risk, keywords in RISK_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
