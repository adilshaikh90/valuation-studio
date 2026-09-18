"""
Institutional Peer Matching Engine.
Provides business-model and geography-aligned comparable company universes
across major global financial centres (London, New York, Frankfurt, Paris, Tokyo, Mumbai, etc.).
"""
from typing import List, Dict, Any, Optional

SUB_INDUSTRY_PEERS: Dict[str, Dict[str, List[str]]] = {
    # ── FINANCIAL SERVICES & INSURANCE ─────────────────────────────────────────
    "insurance": {
        "UK": ["HSX.L", "BEZ.L", "AV.L", "PRU.L", "LGEN.L", "ALV.DE", "CS.PA"],
        "EU": ["ALV.DE", "CS.PA", "ZURN.SW", "MUV2.DE", "G.MI", "SAMPO.HE", "AV.L"],
        "US": ["PGR", "ALL", "TRV", "CB", "HIG", "WRB", "AIG", "MET"],
        "GLOBAL": ["PGR", "ALL", "TRV", "ALV.DE", "CS.PA", "AV.L", "CB"],
    },
    "insurance - property & casualty": {
        "UK": ["HSX.L", "BEZ.L", "AV.L", "ALV.DE", "CS.PA", "ZURN.SW"],
        "EU": ["ALV.DE", "CS.PA", "ZURN.SW", "MUV2.DE", "G.MI", "SAMPO.HE"],
        "US": ["PGR", "ALL", "TRV", "CB", "HIG", "WRB", "ACGL"],
        "GLOBAL": ["PGR", "ALL", "TRV", "ALV.DE", "CS.PA", "HSX.L", "BEZ.L"],
    },
    "insurance - life": {
        "UK": ["PRU.L", "AV.L", "LGEN.L", "ALV.DE", "CS.PA"],
        "EU": ["ALV.DE", "CS.PA", "G.MI", "NN.AS", "ZURN.SW"],
        "US": ["MET", "PRU", "AFL", "GL", "LNC"],
        "GLOBAL": ["PRU.L", "MET", "PRU", "ALV.DE", "AFL"],
    },
    "insurance - specialty": {
        "UK": ["BEZ.L", "HSX.L", "AV.L", "MUV2.DE"],
        "EU": ["MUV2.DE", "HNR1.DE", "SCOR.PA"],
        "US": ["WRB", "RE", "RNR", "EG"],
        "GLOBAL": ["BEZ.L", "HSX.L", "WRB", "MUV2.DE"],
    },
    "banks - diversified": {
        "UK": ["BARC.L", "LLOY.L", "NWG.L", "STAN.L", "HSBA.L"],
        "EU": ["BNP.PA", "SAN.MC", "INGA.AS", "DBK.DE", "ISP.MI", "UCG.MI", "BBVA.MC"],
        "US": ["JPM", "BAC", "WFC", "C", "USB", "PNC"],
        "IN": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
        "GLOBAL": ["JPM", "BAC", "HSBA.L", "BNP.PA", "BARC.L"],
    },
    "banks - regional": {
        "UK": ["NWG.L", "LLOY.L", "BARC.L"],
        "US": ["FITB", "MTB", "KEY", "CFG", "HBAN", "RF", "CMA"],
        "EU": ["CABK.MC", "BPE.MC", "EBS.VI", "BAMI.MI"],
        "GLOBAL": ["FITB", "MTB", "NWG.L", "LLOY.L"],
    },
    "asset management": {
        "UK": ["SDR.L", "ABDN.L", "MNG.L", "HL.L", "AJB.L", "LGEN.L"],
        "EU": ["AMUN.PA", "DWS.DE", "EXO.AS"],
        "US": ["BLK", "BX", "KKR", "APO", "BEN", "TROW", "AMP"],
        "GLOBAL": ["BLK", "BX", "SDR.L", "KKR", "APO"],
    },
    "capital markets": {
        "UK": ["LSEG.L", "IGG.L", "PLUS.L", "SDR.L"],
        "US": ["MS", "GS", "SCHW", "CME", "ICE", "COIN"],
        "EU": ["DB1.DE", "EURX.PA"],
        "GLOBAL": ["MS", "GS", "LSEG.L", "SCHW", "CME"],
    },

    # ── ENERGY & OIL & GAS ─────────────────────────────────────────────────────
    "oil & gas integrated": {
        "UK": ["BP.L", "SHEL.L", "TTE.PA", "ENI.MI", "EQNR.OL"],
        "EU": ["TTE.PA", "ENI.MI", "EQNR.OL", "REP.MC", "BP.L", "SHEL.L"],
        "US": ["XOM", "CVX", "COP", "OXY", "HES"],
        "IN": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS"],
        "GLOBAL": ["XOM", "CVX", "SHEL.L", "BP.L", "TTE.PA"],
    },
    "oil & gas e&p": {
        "UK": ["HBR.L", "ENQ.L", "BP.L", "SHEL.L"],
        "US": ["EOG", "PXD", "DVN", "FANG", "APA", "MRO"],
        "GLOBAL": ["EOG", "COP", "HBR.L", "DVN"],
    },
    "utilities - regulated electric": {
        "UK": ["NG.L", "SSE.L", "SVT.L", "UU.L"],
        "EU": ["IBE.MC", "ENEL.MI", "RWE.DE", "ENGIE.PA", "EDP.LS"],
        "US": ["NEE", "DUK", "SO", "D", "AEP", "SRE"],
        "GLOBAL": ["NEE", "IBE.MC", "NG.L", "DUK", "ENEL.MI"],
    },

    # ── PHARMACEUTICALS & HEALTHCARE ──────────────────────────────────────────
    "drug manufacturers - general": {
        "UK": ["AZN.L", "GSK.L", "HIK.L", "NOVN.SW", "ROG.SW", "SAN.PA"],
        "EU": ["NOVN.SW", "ROG.SW", "SAN.PA", "BAYN.DE", "UCB.BR", "AZN.L"],
        "US": ["LLY", "JNJ", "ABBV", "MRK", "PFE", "BMY", "AMGN"],
        "IN": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
        "GLOBAL": ["LLY", "AZN.L", "NOVN.SW", "JNJ", "GSK.L", "ABBV"],
    },
    "biotechnology": {
        "UK": ["AZN.L", "GSK.L"],
        "US": ["VRTX", "REGN", "GILD", "BIIB", "MRNA", "BNTX"],
        "EU": ["GEN.CO", "ARGX.BR", "BNTX"],
        "GLOBAL": ["VRTX", "REGN", "GILD", "AZN.L"],
    },
    "medical devices": {
        "UK": ["SN.L", "CONV.L"],
        "US": ["MDT", "ABT", "BSX", "ISRG", "SYK", "EW"],
        "EU": ["PHG.AS", "SIE.DE", "STMN.SW"],
        "GLOBAL": ["MDT", "ABT", "BSX", "SN.L", "ISRG"],
    },

    # ── CONSUMER GOODS, FOOD & BEVERAGES ──────────────────────────────────────
    "beverages - non-alcoholic": {
        "UK": ["FEVR.L", "BVIC.L", "DGE.L"],
        "US": ["KO", "PEP", "MNST", "KDP", "CELH"],
        "EU": ["HEIA.AS", "CARL-B.CO"],
        "GLOBAL": ["KO", "PEP", "MNST", "DGE.L"],
    },
    "beverages - brewers / distillers": {
        "UK": ["DGE.L", "HEIA.AS", "CARL-B.CO", "ABI.BR"],
        "EU": ["HEIA.AS", "ABI.BR", "CARL-B.CO", "RI.PA"],
        "US": ["STZ", "BF-B", "TAP"],
        "GLOBAL": ["DGE.L", "ABI.BR", "HEIA.AS", "STZ"],
    },
    "packaged foods": {
        "UK": ["ABF.L", "PRG.L", "ULVR.L"],
        "EU": ["NESN.SW", "BN.PA", "KCOM.CO"],
        "US": ["MDLZ", "GIS", "K", "KHC", "HRL", "CPB"],
        "GLOBAL": ["NESN.SW", "MDLZ", "ULVR.L", "BN.PA"],
    },
    "household & personal products": {
        "UK": ["ULVR.L", "RKT.L"],
        "EU": ["OR.PA", "BEI.DE"],
        "US": ["PG", "CL", "KMB", "EL", "CHD"],
        "IN": ["HINDUNILVR.NS", "ITC.NS", "GODREJCP.NS", "DABUR.NS"],
        "GLOBAL": ["PG", "ULVR.L", "OR.PA", "RKT.L", "CL"],
    },
    "tobacco": {
        "UK": ["BATS.L", "IMB.L"],
        "US": ["PM", "MO"],
        "GLOBAL": ["PM", "BATS.L", "MO", "IMB.L"],
    },

    # ── RETAIL & CONSUMER DISCRETIONARY ───────────────────────────────────────
    "grocery stores": {
        "UK": ["TSCO.L", "SBRY.L", "MKS.L", "BME.L"],
        "EU": ["CA.PA", "AD.AS", "COLR.BR"],
        "US": ["KR", "WMT", "COST", "TGT", "SFM"],
        "GLOBAL": ["TSCO.L", "WMT", "COST", "CA.PA", "SBRY.L"],
    },
    "apparel retail / luxury": {
        "UK": ["NEXT.L", "JD.L", "MKS.L", "BRBY.L"],
        "EU": ["MC.PA", "RMS.PA", "KER.PA", "ITX.MC", "HMB.ST", "CFR.SW", "MONC.MI"],
        "US": ["NKE", "TJX", "ROST", "LULU", "ANF"],
        "GLOBAL": ["MC.PA", "ITX.MC", "NKE", "NEXT.L", "RMS.PA"],
    },
    "auto manufacturers": {
        "UK": ["AML.L", "VOW3.DE", "BMW.DE"],
        "EU": ["VOW3.DE", "BMW.DE", "MBG.DE", "STLAM.MI", "RNO.PA", "PAH3.DE"],
        "US": ["TSLA", "GM", "F", "RIVN"],
        "JP": ["7203.T", "7267.T", "7201.T"],
        "IN": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS"],
        "GLOBAL": ["TSLA", "7203.T", "VOW3.DE", "BMW.DE", "GM"],
    },
    "residential construction / housebuilders": {
        "UK": ["BDEV.L", "TW.L", "PSN.L", "BWY.L", "VTY.L"],
        "US": ["DHI", "LEN", "PHM", "TOL", "NVR", "KBH"],
        "GLOBAL": ["BDEV.L", "TW.L", "DHI", "LEN", "PSN.L"],
    },

    # ── AEROSPACE, DEFENSE & INDUSTRIALS ───────────────────────────────────────
    "aerospace & defense": {
        "UK": ["BA.L", "RR.L", "QQ.L", "BAB.L", "AIR.PA", "SAF.PA"],
        "EU": ["AIR.PA", "SAF.PA", "RHM.DE", "LDO.MI", "THAL.PA", "SAAB-B.ST"],
        "US": ["RTX", "LMT", "BA", "NOC", "GD", "TDG", "HEI"],
        "GLOBAL": ["RTX", "LMT", "BA.L", "AIR.PA", "SAF.PA", "RR.L"],
    },
    "specialty industrial machinery": {
        "UK": ["SMIN.L", "SPX.L", "IMI.L", "WEIR.L"],
        "EU": ["SAND.ST", "ATCO-A.ST", "ANDR.VI", "KNEBV.HE"],
        "US": ["CAT", "DE", "EMR", "ITW", "PH", "ROK", "IR"],
        "GLOBAL": ["CAT", "DE", "SMIN.L", "SAND.ST", "EMR"],
    },

    # ── MINING & NATURAL RESOURCES ────────────────────────────────────────────
    "other industrial metals & mining": {
        "UK": ["RIO.L", "GLEN.L", "AAL.L", "ANTO.L", "FRES.L"],
        "US": ["FCX", "SCCO", "AA", "CLF", "NUE"],
        "AU": ["BHP.AX", "RIO.AX", "FMG.AX"],
        "GLOBAL": ["BHP.AX", "RIO.L", "GLEN.L", "VALE", "FCX", "AAL.L"],
    },

    # ── TELECOMMUNICATIONS ────────────────────────────────────────────────────
    "telecom services": {
        "UK": ["BT-A.L", "VOD.L", "AIRN.L"],
        "EU": ["DTE.DE", "ORA.PA", "TEF.MC", "TEL.OL", "TELIA.ST"],
        "US": ["VZ", "T", "TMUS", "CMCSA"],
        "GLOBAL": ["DTE.DE", "TMUS", "VZ", "VOD.L", "ORA.PA"],
    },

    # ── TECHNOLOGY & SOFTWARE ─────────────────────────────────────────────────
    "software - infrastructure / cloud": {
        "UK": ["SGE.L", "SAP.DE"],
        "EU": ["SAP.DE", "DSY.PA", "SUSE.DE"],
        "US": ["MSFT", "ORCL", "CRM", "NOW", "SNOW", "PLTR", "DDOG"],
        "GLOBAL": ["MSFT", "ORCL", "SAP.DE", "CRM", "NOW", "SGE.L"],
    },
    "semiconductors": {
        "UK": ["ASML.AS", "IFX.DE", "NVDA"],
        "EU": ["ASML.AS", "IFX.DE", "STMPA.PA", "ASM.AS", "BESI.AS"],
        "US": ["NVDA", "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "ADI"],
        "GLOBAL": ["NVDA", "ASML.AS", "AVGO", "AMD", "QCOM"],
    },

    # ── REAL ESTATE & REITS ───────────────────────────────────────────────────
    "reit - diversified / commercial": {
        "UK": ["LAND.L", "BLND.L", "SEGRO.L", "UTG.L"],
        "EU": ["URW.AS", "GFC.PA", "LEG.DE", "VNA.DE"],
        "US": ["PLD", "AMT", "EQIX", "SPG", "O", "PSA", "DLR"],
        "GLOBAL": ["PLD", "AMT", "LAND.L", "SEGRO.L", "SPG"],
    },

    # ── TRAVEL, AIRLINES & LODGING ────────────────────────────────────────────
    "airlines": {
        "UK": ["IAG.L", "EZJ.L", "WIZZ.L", "AF.PA", "LHA.DE"],
        "EU": ["AF.PA", "LHA.DE", "RYA.IR"],
        "US": ["DAL", "UAL", "AAL", "LUV"],
        "GLOBAL": ["DAL", "IAG.L", "LHA.DE", "UAL", "RYA.IR"],
    },
    "lodging": {
        "UK": ["IHG.L", "WTB.L"],
        "EU": ["AC.PA"],
        "US": ["MAR", "HLT", "H", "ABNB"],
        "GLOBAL": ["MAR", "HLT", "IHG.L", "ABNB"],
    },
}

SECTOR_PEERS_BY_REGION: Dict[str, Dict[str, List[str]]] = {
    "Financial Services": {
        "UK": ["AV.L", "HSX.L", "BEZ.L", "PRU.L", "LGEN.L", "BARC.L", "LLOY.L"],
        "EU": ["ALV.DE", "CS.PA", "ZURN.SW", "BNP.PA", "SAN.MC", "INGA.AS"],
        "US": ["JPM", "BAC", "WFC", "BLK", "PGR", "TRV", "MS", "GS"],
        "GLOBAL": ["JPM", "BAC", "ALV.DE", "AV.L", "CS.PA", "BLK"],
    },
    "Energy": {
        "UK": ["BP.L", "SHEL.L", "HBR.L", "TTE.PA", "ENI.MI"],
        "EU": ["TTE.PA", "ENI.MI", "EQNR.OL", "REP.MC"],
        "US": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "GLOBAL": ["XOM", "CVX", "SHEL.L", "BP.L", "TTE.PA"],
    },
    "Healthcare": {
        "UK": ["AZN.L", "GSK.L", "HIK.L", "NOVN.SW", "ROG.SW"],
        "EU": ["NOVN.SW", "ROG.SW", "SAN.PA", "BAYN.DE"],
        "US": ["LLY", "JNJ", "ABBV", "MRK", "PFE"],
        "GLOBAL": ["LLY", "AZN.L", "JNJ", "NOVN.SW", "GSK.L"],
    },
    "Consumer Defensive": {
        "UK": ["ULVR.L", "DGE.L", "RKT.L", "BATS.L", "TSCO.L", "ABF.L"],
        "EU": ["NESN.SW", "OR.PA", "BN.PA", "HEIA.AS"],
        "US": ["PG", "KO", "PEP", "COST", "WMT", "MDLZ"],
        "GLOBAL": ["PG", "NESN.SW", "KO", "ULVR.L", "DGE.L"],
    },
    "Consumer Cyclical": {
        "UK": ["NEXT.L", "JD.L", "MKS.L", "BDEV.L", "TW.L"],
        "EU": ["MC.PA", "RMS.PA", "KER.PA", "ITX.MC", "VOW3.DE", "BMW.DE"],
        "US": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX"],
        "GLOBAL": ["AMZN", "MC.PA", "TSLA", "ITX.MC", "HD"],
    },
    "Technology": {
        "UK": ["SGE.L", "SAP.DE", "ASML.AS", "NVDA", "MSFT"],
        "EU": ["ASML.AS", "SAP.DE", "IFX.DE", "STMPA.PA"],
        "US": ["MSFT", "AAPL", "NVDA", "ORCL", "CRM", "GOOGL"],
        "GLOBAL": ["MSFT", "AAPL", "NVDA", "ASML.AS", "SAP.DE"],
    },
    "Industrials": {
        "UK": ["BA.L", "RR.L", "SMIN.L", "SPX.L", "IMI.L", "WEIR.L"],
        "EU": ["AIR.PA", "SAF.PA", "RHM.DE", "SAND.ST", "SIE.DE"],
        "US": ["CAT", "DE", "RTX", "LMT", "GE", "HON"],
        "GLOBAL": ["CAT", "RTX", "BA.L", "AIR.PA", "RR.L"],
    },
    "Basic Materials": {
        "UK": ["RIO.L", "GLEN.L", "AAL.L", "ANTO.L"],
        "EU": ["BAS.DE", "MT.AS", "ARKM.PA"],
        "US": ["FCX", "NEM", "LIN", "APD", "ECL"],
        "GLOBAL": ["BHP.AX", "RIO.L", "GLEN.L", "LIN", "FCX"],
    },
    "Communication Services": {
        "UK": ["BT-A.L", "VOD.L", "DTE.DE", "ORA.PA"],
        "EU": ["DTE.DE", "ORA.PA", "TEF.MC"],
        "US": ["GOOGL", "META", "DIS", "NFLX", "TMUS", "VZ"],
        "GLOBAL": ["GOOGL", "META", "DTE.DE", "VOD.L", "DIS"],
    },
    "Utilities": {
        "UK": ["NG.L", "SSE.L", "SVT.L", "UU.L", "CNA.L"],
        "EU": ["IBE.MC", "ENEL.MI", "RWE.DE", "ENGIE.PA"],
        "US": ["NEE", "DUK", "SO", "D", "AEP"],
        "GLOBAL": ["NEE", "IBE.MC", "NG.L", "ENEL.MI"],
    },
    "Real Estate": {
        "UK": ["LAND.L", "BLND.L", "SEGRO.L", "UTG.L"],
        "EU": ["URW.AS", "VNA.DE", "LEG.DE"],
        "US": ["PLD", "AMT", "EQIX", "SPG", "O"],
        "GLOBAL": ["PLD", "AMT", "LAND.L", "SEGRO.L"],
    },
}


def detect_ticker_region(ticker: str, info: Optional[Dict[str, Any]] = None) -> str:
    """Detects the primary geographic market of a ticker."""
    sym = ticker.upper().strip()
    if sym.endswith('.L'):
        return 'UK'
    if sym.endswith(('.DE', '.F')):
        return 'EU'
    if sym.endswith(('.PA', '.AS', '.BR', '.MI', '.MC', '.SW', '.VX', '.HE', '.ST', '.OL', '.CO', '.LS')):
        return 'EU'
    if sym.endswith(('.NS', '.BO')):
        return 'IN'
    if sym.endswith('.T'):
        return 'JP'
    if sym.endswith(('.TO', '.V')):
        return 'CA'
    if sym.endswith('.AX'):
        return 'AU'
    if sym.endswith(('.HK', '.SS', '.SZ')):
        return 'ASIA'

    if info:
        country = str(info.get('country') or '').lower()
        if any(c in country for c in ['united kingdom', 'uk', 'britain', 'england', 'scotland', 'wales']):
            return 'UK'
        if any(c in country for c in ['germany', 'france', 'italy', 'spain', 'switzerland', 'netherlands', 'sweden', 'norway', 'finland', 'denmark', 'belgium']):
            return 'EU'
        if 'india' in country:
            return 'IN'
        if 'japan' in country:
            return 'JP'
        if 'canada' in country:
            return 'CA'
        if 'australia' in country:
            return 'AU'

    return 'US'


def get_institutional_peers(
    ticker: str,
    data_fetcher: Any = None,
    info: Optional[Dict[str, Any]] = None,
    custom_peers: Optional[List[str]] = None,
    limit: int = 6
) -> Dict[str, Any]:
    """
    Resolves an institutional, industry-aligned peer universe for a company.
    """
    ticker = ticker.upper().strip()
    
    if info is None and data_fetcher is not None:
        try:
            info = data_fetcher.get_info(ticker)
        except Exception:
            info = {}
    info = info or {}

    industry_raw = str(info.get('industry') or '').strip().lower()
    sector_raw = str(info.get('sector') or '').strip()
    region = detect_ticker_region(ticker, info)

    selected_peers: List[str] = []
    if custom_peers:
        for p in custom_peers:
            p_clean = p.strip().upper()
            if p_clean and p_clean != ticker and p_clean not in selected_peers:
                selected_peers.append(p_clean)

    matched_industry_name = industry_raw or sector_raw or "General"
    peer_source = "Sector / Industry Database"

    found_sub_peers = False
    for sub_key, region_map in SUB_INDUSTRY_PEERS.items():
        if sub_key in industry_raw or (industry_raw and industry_raw in sub_key):
            found_sub_peers = True
            matched_industry_name = sub_key.title()
            
            # Regional candidates
            region_candidates = region_map.get(region, [])
            for cand in region_candidates:
                if cand != ticker and cand not in selected_peers:
                    selected_peers.append(cand)

            # European / UK cross-pollination
            if region in ['UK', 'EU'] and len(selected_peers) < limit:
                alt_region = 'EU' if region == 'UK' else 'UK'
                for cand in region_map.get(alt_region, []):
                    if cand != ticker and cand not in selected_peers:
                        selected_peers.append(cand)

            # Global sub-industry peers
            if len(selected_peers) < limit:
                for cand in region_map.get('GLOBAL', []):
                    if cand != ticker and cand not in selected_peers:
                        selected_peers.append(cand)

            peer_source = f"Direct Sub-Industry: {matched_industry_name} ({region})"
            break

    if not found_sub_peers or len(selected_peers) < 3:
        for sec_name, sec_region_map in SECTOR_PEERS_BY_REGION.items():
            if sec_name.lower() in sector_raw.lower() or sector_raw.lower() in sec_name.lower():
                for cand in sec_region_map.get(region, []):
                    if cand != ticker and cand not in selected_peers:
                        selected_peers.append(cand)
                for cand in sec_region_map.get('GLOBAL', []):
                    if cand != ticker and cand not in selected_peers:
                        selected_peers.append(cand)
                peer_source = f"Regional Sector: {sec_name} ({region})"
                break

    if not selected_peers:
        selected_peers = ['MSFT', 'AAPL', 'GOOGL', 'AMZN'] if ticker != 'AAPL' else ['MSFT', 'GOOGL', 'META']

    final_peers = [p for p in selected_peers if p != ticker][:limit]

    return {
        "ticker": ticker,
        "region": region,
        "industry": info.get('industry') or matched_industry_name,
        "sector": sector_raw,
        "peer_source": peer_source,
        "peers": final_peers,
    }
