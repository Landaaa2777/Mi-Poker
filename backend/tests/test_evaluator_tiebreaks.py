import pytest

from poker_engine import evaluate, parse_cards


def ev(text):
    return evaluate(parse_cards(text))


@pytest.mark.parametrize(
    "stronger, weaker",
    [
        # Carta alta: decide hasta el quinto kicker.
        ("As Kd 9h 5c 3d", "Ah Kc 9d 5s 2c"),
        ("As Kd 9h 5c 2d", "Ah Qc Jd Ts 8c"),
        # Pareja: primero la pareja, luego cada kicker.
        ("Ks Kd 4h 3c 2d", "Qs Qd Ah Kc Jd"),
        ("As Ad Kh 5c 2d", "Ac Ah Qh 5d 2c"),
        ("As Ad Kh 6c 2d", "Ac Ah Kd 5d 2c"),
        ("As Ad Kh 5c 3d", "Ac Ah Kd 5d 2c"),
        # Doble pareja: pareja alta, pareja baja y kicker.
        ("As Ad 3h 3c 2d", "Ks Kd Qh Qc Jd"),
        ("As Ad 9h 9c 2d", "Ac Ah 8h 8c Kd"),
        ("As Ad 9h 9c Kd", "Ac Ah 9d 9s Qd"),
        # Trío: el trío y luego los dos kickers.
        ("3s 3d 3h 4c 2d", "2s 2h 2c As Kd"),
        ("9s 9d 9h Ac 2d", "9c 9d 9h Kc Qd"),
        ("9s 9d 9h Ac 3d", "9c 9d 9h Ad 2c"),
        # Escalera: la carta más alta.
        ("Ts 9d 8h 7c 6d", "9s 8d 7h 6c 5d"),
        ("As Kd Qh Jc Td", "Ks Qd Jh Tc 9d"),
        # Color: como carta alta, hasta la quinta.
        ("As Js 9s 5s 3s", "Ad Jd 9d 5d 2d"),
        ("Ks Qs Js 9s 8s", "Kd Qd Jd 9d 7d"),
        # Full: manda el trío, luego la pareja.
        ("3s 3d 3h 2c 2d", "2s 2h 2c As Ad"),
        ("9s 9d 9h Ac Ad", "9c 9d 9h Ks Kd"),
        # Póker: el póker y luego el kicker.
        ("3s 3d 3h 3c 2d", "2s 2d 2h 2c Ad"),
        ("9s 9d 9h 9c Ad", "9s 9d 9h 9c Kd"),
        # Escalera de color: la carta más alta.
        ("Ts 9s 8s 7s 6s", "9d 8d 7d 6d 5d"),
    ],
)
def test_stronger_hand_wins(stronger, weaker):
    assert ev(stronger) > ev(weaker)


@pytest.mark.parametrize(
    "first, second",
    [
        # Los palos no desempatan.
        ("As Kd 9h 5c 2d", "Ah Kc 9d 5s 2c"),
        ("As Ad 9h 9c 2d", "Ac Ah 9d 9s 2h"),
        ("As Js 9s 5s 2s", "Ad Jd 9d 5d 2d"),
        ("As Ks Qs Js Ts", "Ad Kd Qd Jd Td"),
    ],
)
def test_exact_ties(first, second):
    assert ev(first) == ev(second)


def test_holdem_kicker_decides():
    board = "As 7d 9h Jc 3s"
    assert ev(f"Ad Kc {board}") > ev(f"Ah Qc {board}")


def test_holdem_sixth_card_does_not_count():
    # Ambos juegan A-K-J-9-7 con pareja de ases; la carta baja propia no cuenta.
    board = "As Kd Jh 9c 7s"
    assert ev(f"Ad 3c {board}") == ev(f"Ah 2c {board}")


def test_holdem_board_plays():
    board = "As Ks Qd Jh Tc"
    assert ev(f"2c 3d {board}") == ev(f"9h 9d {board}")


def test_holdem_counterfeited_pair_ties():
    # La mesa da doble pareja A-K con kicker Q; la pareja de J no mejora nada.
    board = "As Ad Kh Kc Qd"
    assert ev(f"Js Jc {board}") == ev(f"Qs 2c {board}")
