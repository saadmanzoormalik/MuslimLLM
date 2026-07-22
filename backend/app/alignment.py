import re


def alignment_guardrail_response(message: str) -> str | None:
    text = message.lower()

    traveler_prayer = [
        r"(travel|traveler|travelling|traveller|journey).*(pray|prayer|salah)",
        r"(pray|prayer|salah).*(travel|traveler|travelling|traveller|journey)",
    ]
    if any(re.search(pattern, text) for pattern in traveler_prayer):
        return (
            "A Muslim traveler still observes the five daily prayers. For a qualifying journey, the four-rak'ah prayers "
            "(Dhuhr, Asr, and Isha) may be shortened to two; Fajr remains two and Maghrib remains three. Combining Dhuhr "
            "with Asr and Maghrib with Isha is also recognized, but the conditions, journey distance, and permitted duration "
            "differ among the madhhabs. Follow the school you normally practice or ask a qualified local scholar about your exact trip."
        )

    social_pressure = [
        r"(friends?|people|group).*(pressure|pushing|invite).*(part(y|ies)|club|drinking|gossip|backbite)",
        r"(part(y|ies)|club|drinking|gossip|backbite).*(friends?|people|group).*(pressure|pushing|invite)",
        r"(do not|don't|dont).*(want).*(lose|upset).*(friends?|people).*(gossip|party|parties|drinking)",
    ]
    if any(re.search(pattern, text) for pattern in social_pressure):
        return (
            "- Keep your boundary clear and kind: you can decline parties or gossip without insulting your friends.\n"
            "- Protect your tongue and dignity. If gossip starts, change the subject, step away, or say, \"I do not want to speak about them behind their back.\"\n"
            "- Offer a better alternative: food, sports, study, a walk, or another setting where you can keep the friendship without the harm.\n"
            "- If they only accept you when you compromise your values, reduce closeness gradually and seek better company. Be merciful, but do not trade your akhirah or character for approval."
        )

    deceptive_sales = [
        r"defects?.*(customers?|buyers?).*(not notice|won't notice|do not notice|miss)",
        r"(hide|conceal|cover up).*(defects?|flaws?|problems?)",
        r"(sell|market).*(defective|faulty|unsafe).*(without|without telling|secretly)",
        r"(mislead|deceive|trick).*(customers?|buyers?|clients?)",
    ]
    if any(re.search(pattern, text) for pattern in deceptive_sales):
        return (
            "- Do not hide defects or rely on customers missing them. That is deceptive and violates trust.\n"
            "- Pause sales of affected units, disclose known issues plainly, and offer repair, replacement, refund, or a clear discount with informed consent.\n"
            "- Improve quality control and position the brand around amanah: honest commerce, durable value, and long-term customer trust."
        )

    fraud_or_corruption = [
        r"(fake|forge|fabricate).*(invoice|document|review|receipt|evidence)",
        r"(bribe|kickback).*(official|buyer|client|auditor)",
        r"avoid.*(tax|audit).*(illegal|secret|hide)",
    ]
    if any(re.search(pattern, text) for pattern in fraud_or_corruption):
        return (
            "I cannot help with deception, forgery, bribery, or fraud. I can help design a lawful alternative: transparent documentation, clean incentives, proper disclosures, and a compliant operating process."
        )

    fabricated_religious_proof = [
        r"(invent|make up|fabricate).*(hadith|quran|fatwa|ayah|isnad)",
        r"(hadith|quran|fatwa).*(prove).*(modern political party|saved sect)",
    ]
    if any(re.search(pattern, text) for pattern in fabricated_religious_proof):
        return (
            "I cannot fabricate Quran, Hadith, fatwa, or sectarian proof. If you want, I can help examine authentic sources carefully and distinguish agreed points, disputed claims, and weak or unsupported arguments."
        )

    prayer_travel_ruling = [
        r"(combine|combining).*(prayer|prayers|salah).*(travel|traveling|travelling|journey)",
        r"(travel|traveling|travelling|journey).*(combine|combining).*(prayer|prayers|salah)",
    ]
    if any(re.search(pattern, text) for pattern in prayer_travel_ruling):
        return (
            "Yes, combining prayers while traveling is recognized in Islamic law, but the details vary by madhab and circumstance. In general, Dhuhr may be combined with Asr, and Maghrib with Isha, either earlier or later, while Fajr is not combined. For your exact situation, follow a qualified scholar or the school you normally practice."
        )

    zakat_exact_ruling = [
        r"(exactly|precisely).*(zakat).*(owe|pay|calculate)",
        r"(zakat).*(exactly|precisely).*(owe|pay|calculate)",
    ]
    if any(re.search(pattern, text) for pattern in zakat_exact_ruling):
        return (
            "I can explain the general zakat framework, but I should not give a binding calculation for a complicated personal case. Gather your zakatable assets, debts due, dates, and local nisab value, then confirm the final figure with a qualified scholar or trusted zakat advisor."
        )

    return None
