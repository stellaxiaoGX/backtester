import argparse
import os
import sys
import pandas as pd

"""Class-based allocation script using building blocks and config examples.

It expects:
- working/building_blocks.csv
- portfolio_config/config.csv

It groups strategies by STRATEGY_ID and SUB_STRATEGY, computes notional, collateral, and dependency.
"""

DEFAULT_CASH = 1000000


def parse_percent(value):
    if pd.isna(value) or value == "":
        return 0.0
    v = str(value).strip().replace("%", "")
    try:
        val = float(v)
        return val / 100.0 if abs(val) > 1 else val
    except Exception:
        return 0.0


def parse_moneyness(value):
    if pd.isna(value) or value == "":
        return 100.0
    v = str(value).strip().replace("%", "")
    try:
        m = float(v)
        return m if m > 1 else m * 100
    except Exception:
        return 100.0


def parse_direction(value):
    if pd.isna(value) or str(value).strip() == "":
        return "long"
    s = str(value).strip().lower()
    if s in {"1", "long", "l", "+"}:
        return "long"
    if s in {"-1", "short", "s", "-"}:
        return "short"
    return "long"


class BuildingBlock:
    def __init__(self, id, pos, type_, aka, description, collateral, ctype):
        self.id = id
        self.pos = pos
        self.type = type_
        self.aka = aka
        self.description = description
        self.collateral = collateral
        self.ctype = ctype

    def __repr__(self):
        return f"<BuildingBlock {self.id} {self.type} {self.pos}>"


class StrategyLeg:
    def __init__(self, strategy_id, sub_strategy, asset, direction, weight, option_type, dtm, moneyness):
        self.strategy_id = str(strategy_id).strip()
        self.sub_strategy = str(sub_strategy).strip()
        self.asset = str(asset).strip()
        self.direction = parse_direction(direction)
        self.weight = parse_percent(weight)
        self.option_type = str(option_type).strip().upper()
        self.dtm = int(dtm) if pd.notna(dtm) and str(dtm).strip() != "" else 0
        self.moneyness = parse_moneyness(moneyness)

    def is_option(self):
        return self.asset.lower() == "option"

    def is_equity(self):
        return self.asset.lower() == "equity"

    def is_bond(self):
        return self.asset.lower() == "bond"

    def notional(self, cash):
        return self.weight * cash

    def contract_qty(self, cash, underlying_price=100.0):
        if not self.is_option():
            return 0.0
        strike = underlying_price * self.moneyness / 100.0
        if strike <= 0:
            strike = underlying_price
        notional = self.notional(cash)
        if strike * 100.0 == 0:
            return 0.0
        return abs(notional) / (100.0 * strike)

    def collateral_required(self, cash, underlying_price=100.0):
        if self.direction == "long":
            return 0.0
        if self.is_option():
            qty = self.contract_qty(cash, underlying_price)
            strike = underlying_price * self.moneyness / 100.0
            return qty * 100.0 * strike
        if self.is_equity() or self.is_bond():
            return self.notional(cash)
        return 0.0

    def __repr__(self):
        return f"<StrategyLeg {self.strategy_id}:{self.sub_strategy} {self.asset} {self.direction} {self.weight:.1%}>"


class StrategyGroup:
    def __init__(self, strategy_id, sub_strategy, block=None):
        self.strategy_id = strategy_id
        self.sub_strategy = sub_strategy
        self.block = block
        self.legs = []

    def add_leg(self, leg: StrategyLeg):
        self.legs.append(leg)

    def total_weight(self):
        return sum(l.weight for l in self.legs)

    def total_notional(self, cash):
        return sum(l.notional(cash) for l in self.legs)

    def total_collateral(self, cash, underlying_price=100.0):
        return sum(l.collateral_required(cash, underlying_price) for l in self.legs)

    def dependencies(self):
        sid = self.strategy_id.strip().upper()
        if sid == "CC":
            return "Equity + Call"
        if sid == "STRANGLE":
            return "Call + Put"
        if sid == "SYNTHETIC":
            return "Call + Put"
        if sid in {"IC", "IRON CONDOR"}:
            return "Call Spread + Put Spread"
        if sid == "SPREAD":
            return "Option Spread"
        if sid == "EQUITY":
            return "Equity"
        if sid == "RESIDUAL":
            return "Cash/Bond"
        if self.block and self.block.collateral:
            return self.block.collateral
        return "Unknown"

    def as_dict(self, cash, underlying_price=100.0):
        return {
            "STRATEGY_ID": self.strategy_id,
            "SUB_STRATEGY": self.sub_strategy,
            "LEGS": len(self.legs),
            "TOTAL_WEIGHT": self.total_weight(),
            "NOTIONAL": self.total_notional(cash),
            "COLLATERAL_REQUIRED": self.total_collateral(cash, underlying_price),
            "DEPENDENCY": self.dependencies(),
        }


class Portfolio:
    def __init__(self, cash=DEFAULT_CASH, underlying_price=100.0):
        self.cash = cash
        self.underlying_price = underlying_price
        self.groups = {}
        self.blocks = self.load_building_blocks()

    def load_building_blocks(self):
        path = os.path.join(os.path.dirname(__file__), "working", "building_blocks.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing building blocks: {path}")
        df = pd.read_csv(path)
        df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
        blocks = {}
        for _, r in df.iterrows():
            id_ = str(r.get("ID", "")).strip()
            if not id_:
                continue
            blocks[id_.upper()] = BuildingBlock(
                id=id_,
                pos=str(r.get("POS", "")).strip(),
                type_=str(r.get("TYPE", "")).strip(),
                aka=str(r.get("AKA", "")).strip(),
                description=str(r.get("DES", "")).strip(),
                collateral=str(r.get("COLLATERAL", "")).strip(),
                ctype=str(r.get("CTYPE", "")).strip(),
            )
        return blocks

    def add_leg(self, leg: StrategyLeg):
        key = (leg.strategy_id.strip().upper(), leg.sub_strategy.strip())
        if key not in self.groups:
            block = self.blocks.get(leg.strategy_id.strip().upper())
            self.groups[key] = StrategyGroup(leg.strategy_id, leg.sub_strategy, block)
        self.groups[key].add_leg(leg)

    def load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found: {path}")
        df = pd.read_csv(path)
        if df.empty:
            raise ValueError("Config file is empty")

        keys = {c.strip().upper().replace(' ', '_'): c for c in df.columns}

        for _, r in df.iterrows():
            leg = StrategyLeg(
                strategy_id=r.get(keys.get("STRATEGY_ID", "STRATEGY ID"), ""),
                sub_strategy=r.get(keys.get("SUB_STRATEGY", "SUB STRATEGY"), ""),
                asset=r.get(keys.get("ASSET", ""), ""),
                direction=r.get(keys.get("DIRECTION", ""), ""),
                weight=r.get(keys.get("WEIGHT", ""), "0%"),
                option_type=r.get(keys.get("OPTION_TYPE", "OPTION TYPE"), ""),
                dtm=r.get(keys.get("DTM", ""), 0),
                moneyness=r.get(keys.get("MONEYNESS", ""), "100%"),
            )
            self.add_leg(leg)

    def allocation_summary(self):
        rows = [g.as_dict(self.cash, self.underlying_price) for g in self.groups.values()]
        group_df = pd.DataFrame(rows)
        total_notional = float(group_df["NOTIONAL"].sum()) if not group_df.empty else 0.0
        required_collateral = float(group_df["COLLATERAL_REQUIRED"].sum()) if not group_df.empty else 0.0
        allocation = {
            "TOTAL_CASH": self.cash,
            "TOTAL_NOTIONAL": total_notional,
            "REQUIRED_COLLATERAL": required_collateral,
            "CASH_REMAINING": self.cash - required_collateral,
        }
        return group_df, allocation

    def display(self):
        group_df, allocation = self.allocation_summary()
        print("\n--- Strategy Group Summary ---")
        print(group_df.to_string(index=False, float_format="{:.2f}".format))
        print("\n--- Cash Allocation ---")
        for k, v in allocation.items():
            print(f"{k}: {v:,.2f}")
        return group_df, allocation


def prompt_yes_no(question):
    a = input(question + " [y/n]: ").strip().lower()
    while a not in {"y", "n", "yes", "no"}:
        a = input("Please enter y or n: ").strip().lower()
    return a in {"y", "yes"}


def main():
    parser = argparse.ArgumentParser(description="Class-based allocation preview from config")
    parser.add_argument("--portfolio", required=True, help="Path to config CSV")
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH, help="Total cash amount")
    parser.add_argument("--underlying", type=float, default=100.0, help="Underlying price assumption")
    parser.add_argument("--no-prompt", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    p = Portfolio(cash=args.cash, underlying_price=args.underlying)
    p.load_config(args.portfolio)
    p.display()

    if not args.no_prompt:
        if prompt_yes_no("Confirm allocation?"):
            print("Allocation confirmed.")
        else:
            print("Allocation declined.")
            sys.exit(0)


if __name__ == "__main__":
    main()