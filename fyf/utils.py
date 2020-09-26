DO_NOT_SORT=0
SORT_BY_SUIT_THEN_NUMBER=1
SORT_BY_NUMBER_THEN_SUIT=2
NO_AUTO_SORT = 0
AUTO_SORT_NEW_CARD_ONLY = 1
AUTO_SORT_ALL_CARDS = 2


def sort_card_value(value_list, sorting_rule=None):
    # sort value of cards
    if sorting_rule is None:
        return value_list
    elif sorting_rule == DO_NOT_SORT:
        return value_list
    elif sorting_rule == SORT_BY_SUIT_THEN_NUMBER:
        sorted_values = sorted([(w, w % 54) for w in value_list], key=lambda x: x[1])
        return [w for w,_ in sorted_values]
    elif sorting_rule == SORT_BY_NUMBER_THEN_SUIT:
        sorted_values = sorted([(w, (((w % 54) % 13) * 5+ (w // 52) * 65 + (w % 54)//13)) for w in value_list], key=lambda x: x[1])
        return [w for w, _ in sorted_values]

def sort_cards(card_list, sorting_rule=None):
    if sorting_rule is None:
        return card_list
    elif sorting_rule == DO_NOT_SORT:
        return card_list
    elif sorting_rule == SORT_BY_SUIT_THEN_NUMBER:
        sorted_cards = sorted([(w, w.value % 54) for w in card_list], key=lambda x: x[1])
        return [w for w,_ in sorted_cards]
    elif sorting_rule == SORT_BY_NUMBER_THEN_SUIT:
        sorted_cards = sorted([(w, (((w.value % 54) % 13) * 5+ (w.value // 52) * 65 + (w.value % 54)//13)) for w in card_list], key=lambda x: x[1])
        return [w for w, _ in sorted_cards]


SCORE_RULE_510K = 0
SCORE_RULE_COUNT = 1
def calculate_score(value_list, score_rule):
    if score_rule == SCORE_RULE_510K:
        score_list = [(w % 54) % 13 for w in value_list]
        return score_list.count(3)*5 + score_list.count(8)*10 + score_list.count(11) *10
    elif score_rule == SCORE_RULE_COUNT:
        return len(value_list)

