"""Phase 5.1: query classifier tests."""



import pytest



from app.classifier import QueryLabel, classify_query





@pytest.mark.parametrize(

    "message,expected",

    [

        ("Should I invest in HDFC Mid Cap?", QueryLabel.ADVISORY),

        ("Shuld I invest?", QueryLabel.ADVISORY),

        ("Is this a good fund?", QueryLabel.ADVISORY),

        ("Is 0.73% expense ratio good enough to buy?", QueryLabel.ADVISORY),

        ("Which fund is better?", QueryLabel.COMPARISON),

        ("Which is better: Mid Cap or Small Cap?", QueryLabel.COMPARISON),

        ("Compare expense ratios of Mid Cap and Large Cap", QueryLabel.COMPARISON),

        ("What returns will I get in 3 years?", QueryLabel.PERFORMANCE),

        ("Compare 3Y returns of all HDFC funds", QueryLabel.PERFORMANCE),

        ("Expense ratio of HDFC Mid Cap Direct Growth?", QueryLabel.FACTUAL),

        ("Who manages HDFC Defence Fund?", QueryLabel.FACTUAL),

        ("What is the investment objective of HDFC Mid Cap?", QueryLabel.FACTUAL),

        ("What is the minimum SIP for HDFC Mid Cap?", QueryLabel.FACTUAL),

        ("Expense ratio of HDFC Flexi Cap?", QueryLabel.UNSUPPORTED_SCHEME),

        ("SBI Mid Cap expense ratio", QueryLabel.UNSUPPORTED_SCHEME),

        ("Tell me about SBI Small Cap Fund", QueryLabel.UNSUPPORTED_SCHEME),

        ("What is the expense ratio of ICICI Bluechip Fund?", QueryLabel.UNSUPPORTED_SCHEME),

        ("What is the weather in Mumbai?", QueryLabel.UNRELATED),

        ("What is my name?", QueryLabel.UNRELATED),

        ("Who won the World Cup?", QueryLabel.UNRELATED),

        ("Write me a poem", QueryLabel.UNRELATED),

        ("Who is the Prime Minister of India?", QueryLabel.UNRELATED),

    ],

)

def test_classify_query(message: str, expected: QueryLabel) -> None:

    result = classify_query(message)

    assert result.label == expected

