from app.graph.guardrails import _asserts_figure_on_deferred_topic, _triggered_deferral

F1 = {"triggers": ["F-1", "OPT", "international"], "refer_to": "ISS", "because": "Visa rules."}
DEFERRALS = [F1]


def test_trigger_matches_case_insensitively():
    assert _triggered_deferral("Can I work on OPT after graduating?", DEFERRALS) is F1
    assert _triggered_deferral("i'm an f-1 student", DEFERRALS) is F1


def test_trigger_respects_word_boundaries():
    # "opt" must not fire on "option" or "optional".
    assert _triggered_deferral("Is there a meal plan option?", DEFERRALS) is None
    assert _triggered_deferral("Is the orientation optional?", DEFERRALS) is None


def test_no_deferrals_configured_never_triggers():
    assert _triggered_deferral("F-1 OPT question", []) is None


def test_figure_near_trigger_in_answer_is_flagged():
    answer = "As an F-1 student you may work up to 20 hours per week."
    assert _asserts_figure_on_deferred_topic(answer, DEFERRALS) is F1


def test_naming_the_topic_without_a_figure_is_fine():
    # "f-1" itself contains a digit; the trigger must not match itself.
    answer = "F-1 work rules are set by International Student Services."
    assert _asserts_figure_on_deferred_topic(answer, DEFERRALS) is None


def test_phone_and_room_numbers_in_a_referral_are_not_figures():
    answer = (
        "Please contact International Student Services in Brister Hall "
        "room 120 at 901.678.4271."
    )
    assert _asserts_figure_on_deferred_topic(answer, DEFERRALS) is None


def test_digits_inside_a_source_url_are_ignored():
    answer = "See https://example.edu/international/2026/faq for details."
    assert _asserts_figure_on_deferred_topic(answer, DEFERRALS) is None


def test_figure_far_from_any_trigger_is_not_flagged():
    padding = " ".join(["word"] * 40)
    answer = f"Housing costs $4,200 per semester. {padding} International students are welcome."
    assert _asserts_figure_on_deferred_topic(answer, DEFERRALS) is None
