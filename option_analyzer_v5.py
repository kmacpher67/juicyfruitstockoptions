from option_analyzers import OptionChainAnalyzer


def main():
    analyzer = OptionChainAnalyzer()
    analyzer.analyze(
        ticker_symbol="ORCL",
        min_volume=50,
        max_expirations=2,
        min_annual_tv_pct=9.9,
        max_otm_pct=5.0,
    )


if __name__ == "__main__":
    main()

