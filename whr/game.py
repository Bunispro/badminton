from __future__ import annotations

import sys
from typing import Any

from whr import player as P
from whr import playerday as PD


import math

class Game:
    def __init__(
        self,
        side_a: list[P.Player] | P.Player,
        side_b: list[P.Player] | P.Player,
        winner: str,
        time_step: int,
        handicap: float = 0,
        weight: float = 1.0,
        extras: dict[str, Any] | None = None,
    ):
        self.day = time_step
        self.side_a_players = side_a if isinstance(side_a, list) else [side_a]
        self.side_b_players = side_b if isinstance(side_b, list) else [side_b]
        self.winner = winner.upper()
        self.handicap = handicap
        self.handicap_proc = handicap
        self.weight = weight
        self.player_days: dict[P.Player, PD.PlayerDay] = {}
        if extras is None:
            self.extras = {"komi": 6.5}
        else:
            self.extras = extras
            self.extras.setdefault("komi", 6.5)

    def __str__(self) -> str:
        side_a_names = "+".join(p.name for p in self.side_a_players)
        side_b_names = "+".join(p.name for p in self.side_b_players)
        return f"A:{side_a_names} B:{side_b_names} winner = {self.winner}, handicap = {self.handicap}"

    def opponents_adjusted_gamma(self, player: P.Player) -> float:
        if player in self.side_a_players:
            my_team = self.side_a_players
            opp_team = self.side_b_players
            sign = -1 # A corresponds to Black in original
        elif player in self.side_b_players:
            my_team = self.side_b_players
            opp_team = self.side_a_players
            sign = 1  # B corresponds to White in original
        else:
            raise AttributeError(f"No opponent for {player.__str__()}, since they're not in this game: {self.__str__()}.")
            
        opp_elo = sum(self.player_days[p].elo for p in opp_team)
        partner_elo = sum(self.player_days[p].elo for p in my_team if p != player)
        
        opponent_elo = opp_elo - partner_elo + (sign * self.handicap)
        rval = 10 ** (opponent_elo / 400.0)
        if rval == 0 or rval > sys.maxsize:
            raise AttributeError("bad adjusted gamma")
        return rval

    def opponent(self, player: P.Player) -> list[P.Player]:
        if player in self.side_a_players:
            return self.side_b_players
        return self.side_a_players

    def prediction_score(self) -> float:
        if self.side_a_win_probability() == 0.5:
            return 0.5
        return (
            1.0
            if (
                (self.winner == "B" and self.side_b_win_probability() > 0.5)
                or (self.winner == "A" and self.side_a_win_probability() > 0.5)
            )
            else 0.0
        )

    def side_b_win_probability(self) -> float:
        gamma_b = math.prod(self.player_days[p].gamma() for p in self.side_b_players)
        gamma_a = math.prod(self.player_days[p].gamma() for p in self.side_a_players)
        return gamma_b / (gamma_b + gamma_a * (10 ** (self.handicap / 400.0)))

    def side_a_win_probability(self) -> float:
        gamma_b = math.prod(self.player_days[p].gamma() for p in self.side_b_players)
        gamma_a = math.prod(self.player_days[p].gamma() for p in self.side_a_players)
        return gamma_a / (gamma_a + gamma_b * (10 ** (-self.handicap / 400.0)))
