"""
Excel Financial Model Generator — generates a complete .xlsx with REAL financial data.
Uses live data from data_fetcher: income statement, balance sheet, cash flow, DCF results.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io
from datetime import datetime
import pandas as pd
from typing import Optional

# ── Styles ─────────────────────────────────────────────────────────────────────
DARK_NAVY   = PatternFill(start_color='0a0e1a', end_color='0a0e1a', fill_type='solid')
NAVY_FILL   = PatternFill(start_color='1a1f35', end_color='1a1f35', fill_type='solid')
GOLD_FILL   = PatternFill(start_color='f0b429', end_color='f0b429', fill_type='solid')
INPUT_FILL  = PatternFill(start_color='dbeafe', end_color='dbeafe', fill_type='solid')
GREEN_FILL  = PatternFill(start_color='d1fae5', end_color='d1fae5', fill_type='solid')
RED_FILL    = PatternFill(start_color='fee2e2', end_color='fee2e2', fill_type='solid')

WH_BOLD     = Font(bold=True, color='FFFFFF', size=11)
GOLD_TITLE  = Font(bold=True, size=14, color='f0b429')
GOLD_BOLD   = Font(bold=True, color='000000', size=11)
SECTION_F   = Font(bold=True, size=12, color='FFFFFF')
NORMAL_F    = Font(size=10, color='1a1f35')
RED_F       = Font(color='ef4444')
GREEN_F     = Font(color='10b981')

THIN = Border(
    left=Side(style='thin', color='e5e7eb'),
    right=Side(style='thin', color='e5e7eb'),
    top=Side(style='thin', color='e5e7eb'),
    bottom=Side(style='thin', color='e5e7eb'),
)


def _fmt_currency(iso_code: str, decimals: bool = False) -> str:
    iso = (iso_code or 'USD').upper()
    d = '.00' if decimals else ''
    mapping = {'USD': f'$#,##0{d}', 'GBP': f'£#,##0{d}', 'EUR': f'€#,##0{d}',
               'INR': f'₹#,##0{d}', 'JPY': '¥#,##0', 'CAD': f'C$#,##0{d}',
               'AUD': f'A$#,##0{d}', 'CHF': f'CHF #,##0{d}', 'KRW': '₩#,##0'}
    return mapping.get(iso, f'#,##0{d}')


def _pct(d: bool = True) -> str:
    return '0.0%' if d else '0%'


def _safe_get(df: pd.DataFrame, row_names: list, col_idx: int = 0, default: float = 0.0) -> float:
    if df is None or df.empty:
        return default
    for name in row_names:
        if name in df.index:
            try:
                vals = df.loc[name]
                v = vals.iloc[col_idx] if hasattr(vals, 'iloc') else vals
                if pd.notna(v):
                    return float(v)
            except Exception:
                continue
    return default


def _hdr(ws, row: int, col: int, text: str, fill=NAVY_FILL):
    c = ws.cell(row=row, column=col, value=text)
    c.font = WH_BOLD
    c.fill = fill
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.border = THIN
    return c


def _cell(ws, row: int, col: int, value, fmt: str = None, bold: bool = False,
          fill=None, font_color: str = None):
    c = ws.cell(row=row, column=col, value=value)
    font_kwargs = {'size': 10}
    if bold:
        font_kwargs['bold'] = True
    if font_color:
        font_kwargs['color'] = font_color
    c.font = Font(**font_kwargs)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    c.border = THIN
    c.alignment = Alignment(vertical='center')
    return c


def _label(ws, row: int, text: str, bold: bool = False, indent: bool = False):
    val = ('  ' if indent else '') + text
    c = ws.cell(row=row, column=1, value=val)
    c.font = Font(size=10, bold=bold, color='1a1f35')
    c.border = THIN
    return c


def _setup_sheet(ws, title: str, tab_color: str, col_a_width: int = 32):
    ws.title = title
    ws.sheet_properties.tabColor = tab_color
    ws.freeze_panes = 'B3'
    ws.column_dimensions['A'].width = col_a_width
    for i in range(2, 14):
        ws.column_dimensions[get_column_letter(i)].width = 16
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 22


def generate_financial_model(ticker: str, data_fetcher, valuation_data: dict = None) -> io.BytesIO:
    """
    Generates a complete financial model Excel file with REAL financial data.
    """
    wb = openpyxl.Workbook()

    # ── Fetch real data ───────────────────────────────────────────────────────
    info       = data_fetcher.get_info(ticker)
    income_df  = data_fetcher.get_income_stmt(ticker)
    bs_df      = data_fetcher.get_balance_sheet(ticker)
    cf_df      = data_fetcher.get_cashflow(ticker)

    curr        = info.get('currency', 'USD')
    curr_sym    = data_fetcher.get_currency_symbol(curr)
    curr_fmt    = _fmt_currency(curr)
    curr_dec    = _fmt_currency(curr, decimals=True)
    name        = info.get('name') or ticker
    price       = info.get('current_price') or 0.0
    shares      = info.get('shares_outstanding') or 1
    market_cap  = info.get('market_cap') or 0
    beta        = info.get('beta') or 1.0
    sector      = info.get('sector') or 'N/A'

    # Historical columns (most-recent first in yfinance, so reverse)
    def _hist_row(df, names, n_cols=4):
        vals = []
        for i in range(n_cols):
            vals.append(_safe_get(df, names, col_idx=i))
        return list(reversed(vals))  # chronological order

    rev_hist    = _hist_row(income_df, ['Total Revenue', 'TotalRevenue'])
    ebitda_hist = _hist_row(income_df, ['EBITDA', 'Ebitda'])
    ebit_hist   = _hist_row(income_df, ['EBIT', 'Operating Income', 'OperatingIncome'])
    ni_hist     = _hist_row(income_df, ['Net Income', 'NetIncome'])
    da_hist     = _hist_row(cf_df,     ['Depreciation And Amortization', 'Depreciation', 'DepreciationAndAmortization'])
    capex_hist  = [abs(v) for v in _hist_row(cf_df, ['Capital Expenditure', 'CapitalExpenditure', 'Purchase Of Property Plant And Equipment'])]
    fcf_hist    = _hist_row(cf_df,     ['Free Cash Flow', 'FreeCashFlow'])
    cash_vals   = [_safe_get(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents'], i) for i in range(4)]
    lt_debt_v   = _safe_get(bs_df, ['Long Term Debt', 'LongTermDebt'])
    st_debt_v   = _safe_get(bs_df, ['Current Debt', 'Short Long Term Debt'])
    total_debt  = lt_debt_v + st_debt_v
    cash_latest = abs(_safe_get(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents']))
    net_debt    = total_debt - cash_latest

    # Get WACC
    wacc_val = 0.09
    kd_val   = 0.05
    ke_val   = 0.10
    tax_val  = 0.21
    try:
        from api.valuation.wacc_builder import calculate_wacc
        wd = calculate_wacc(ticker, data_fetcher)
        wacc_val = wd.get('wacc', 0.09)
        kd_val   = wd.get('cost_of_debt', 0.05)
        ke_val   = wd.get('cost_of_equity', 0.10)
        tax_val  = wd.get('tax_rate', 0.21)
    except Exception:
        pass

    # DCF result if available
    dcf_val = 0.0
    try:
        from api.valuation.dcf_fcff import calculate_dcf_fcff
        dcf_res = calculate_dcf_fcff(ticker, data_fetcher)
        dcf_val = dcf_res.get('intrinsic_value_per_share', 0)
    except Exception:
        pass

    years_hist = ['FY-3', 'FY-2', 'FY-1', 'FY0 (LTM)']
    years_proj = ['FY+1E', 'FY+2E', 'FY+3E', 'FY+4E', 'FY+5E']

    # ── Sheet 1: Cover ──────────────────────────────────────────────────────────
    ws_cov = wb.active
    ws_cov.title = 'Cover'
    ws_cov.sheet_properties.tabColor = 'f0b429'
    ws_cov.column_dimensions['A'].width = 30
    ws_cov.column_dimensions['B'].width = 40

    # ── Cover header: embed logo ─────────────────────────────────────────────────

    import os as _os
    # Try to find the logo relative to this file or the project root
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _logo_paths = [
        _os.path.join(_here, '..', '..', 'public', 'images', 'logo-full.png'),
        _os.path.join(_here, '../../public/images/logo-full.png'),
        'public/images/logo-full.png',
    ]
    _logo_file = None
    for _p in _logo_paths:
        if _os.path.exists(_p):
            _logo_file = _os.path.abspath(_p)
            break

    if _logo_file:
        try:
            from openpyxl.drawing.image import Image as XlImage
            _img = XlImage(_logo_file)
            # Scale logo to fit nicely in cover (approx 280×80 px on screen)
            _img.width  = 280
            _img.height = 70
            ws_cov.add_image(_img, 'A1')
            ws_cov.row_dimensions[1].height = 55
            ws_cov.row_dimensions[2].height = 10
        except Exception:
            # Fallback to text if image fails
            ws_cov.merge_cells('A1:C2')
            c = ws_cov['A1']
            c.value = 'Stock Valuation'
            c.font = Font(bold=True, size=20, color='1e3a5f')
            c.fill = PatternFill('solid', fgColor='FFFFFF')
            c.alignment = Alignment(horizontal='left', vertical='center')
    else:
        ws_cov.merge_cells('A1:C2')
        c = ws_cov['A1']
        c.value = 'Stock Valuation | Market • Insights • Analysis'
        c.font = Font(bold=True, size=16, color='1e3a5f')
        c.fill = PatternFill('solid', fgColor='FFFFFF')
        c.alignment = Alignment(horizontal='left', vertical='center')

    # Sub-header bar
    ws_cov.merge_cells('A3:C3')
    c3 = ws_cov['A3']
    c3.value = f'{name} ({ticker.upper()}) — Financial Valuation Model'
    c3.font = Font(bold=True, size=12, color='FFFFFF')
    c3.fill = PatternFill('solid', fgColor='1e3a5f')
    c3.alignment = Alignment(horizontal='left', vertical='center')
    ws_cov.row_dimensions[3].height = 24

    details = [
        ('Company', name),
        ('Ticker', ticker.upper()),
        ('Sector', sector),
        ('Currency', f'{curr} ({curr_sym})'),
        ('Current Price', f'{curr_sym}{price:,.2f}'),
        ('Market Cap', f'{curr_sym}{market_cap/1e9:,.1f}B' if market_cap else 'N/A'),
        ('Shares Outstanding', f'{shares/1e6:,.1f}M' if shares else 'N/A'),
        ('Generated', datetime.now().strftime('%Y-%m-%d %H:%M')),
        ('', ''),
        ('DISCLAIMER', 'For educational purposes only. Not financial advice.'),
    ]
    for i, (lbl, val) in enumerate(details, start=4):
        ws_cov.cell(row=i, column=1, value=lbl).font = Font(bold=True, size=11)
        ws_cov.cell(row=i, column=2, value=val).font = Font(size=11)


    # ── Sheet 2: Summary ────────────────────────────────────────────────────────
    ws_sum = wb.create_sheet('Summary')
    _setup_sheet(ws_sum, 'Summary', 'f0b429')
    ws_sum.merge_cells('A1:F1')
    _hdr(ws_sum, 1, 1, f'{ticker.upper()} — Valuation Summary', GOLD_FILL)
    ws_sum['A1'].font = Font(bold=True, size=13, color='000000')

    summary_data = [
        ('Current Market Price', price, curr_dec),
        ('DCF Intrinsic Value (FCFF)', dcf_val, curr_dec),
        ('Upside / Downside', (dcf_val / price - 1) if price and dcf_val else 0, _pct()),
        ('', None, None),
        ('WACC', wacc_val, _pct()),
        ('Cost of Equity', ke_val, _pct()),
        ('Cost of Debt (after-tax)', kd_val * (1 - tax_val), _pct()),
        ('Effective Tax Rate', tax_val, _pct()),
        ('Net Debt', net_debt, curr_fmt),
        ('Beta', beta, '0.00'),
    ]
    for i, (lbl, val, fmt) in enumerate(summary_data, start=3):
        _label(ws_sum, i, lbl, bold=(lbl in ['Current Market Price', 'DCF Intrinsic Value (FCFF)']))
        if val is not None:
            fc = None
            if lbl == 'Upside / Downside':
                fc = '10b981' if (val or 0) >= 0 else 'ef4444'
            _cell(ws_sum, i, 2, val, fmt=fmt, bold=(val == price or val == dcf_val), font_color=fc,
                  fill=GOLD_FILL if lbl == 'DCF Intrinsic Value (FCFF)' else None)

    # ── Sheet 3: Income Statement ───────────────────────────────────────────────
    ws_is = wb.create_sheet('Income Statement')
    _setup_sheet(ws_is, 'Income Statement', '10b981')
    ws_is.merge_cells('A1:I1')
    _hdr(ws_is, 1, 1, f'{ticker.upper()} — Income Statement ({curr}M)', NAVY_FILL)

    # Column headers
    all_years = years_hist + years_proj
    for j, yr in enumerate(all_years, start=2):
        fill = NAVY_FILL if j <= 5 else INPUT_FILL
        fnt  = WH_BOLD if j <= 5 else Font(bold=True, size=10, color='1e40af')
        c = ws_is.cell(row=2, column=j, value=yr)
        c.font = fnt; c.fill = fill
        c.alignment = Alignment(horizontal='center'); c.border = THIN

    # Build revenue growth from history
    r_growth = 0.07
    if len(rev_hist) >= 2 and rev_hist[0] and rev_hist[-1]:
        try:
            r_growth = (rev_hist[-1] / rev_hist[0]) ** (1/3) - 1
            r_growth = max(min(r_growth, 0.40), -0.10)
        except Exception:
            pass

    ebitda_margin = (ebitda_hist[-1] / rev_hist[-1]) if rev_hist[-1] else 0.20
    ebitda_margin = max(min(ebitda_margin, 0.80), 0.01)
    da_pct = (da_hist[-1] / rev_hist[-1]) if rev_hist[-1] else 0.05
    capex_pct = (capex_hist[-1] / rev_hist[-1]) if rev_hist[-1] else 0.05

    # Project revenue
    last_rev = rev_hist[-1] or (market_cap * 0.25)
    proj_rev = []
    for yr in range(5):
        g = r_growth if yr < 2 else r_growth * (1 - yr * 0.1)
        last_rev = last_rev * (1 + max(g, 0.01))
        proj_rev.append(last_rev)

    proj_ebitda = [r * ebitda_margin for r in proj_rev]
    proj_da     = [r * da_pct for r in proj_rev]
    proj_ebit   = [e - d for e, d in zip(proj_ebitda, proj_da)]
    proj_ni     = [e * (1 - tax_val) for e in proj_ebit]
    proj_capex  = [r * capex_pct for r in proj_rev]
    proj_fcf    = [ni + da - cap for ni, da, cap in zip(proj_ni, proj_da, proj_capex)]

    is_rows = [
        ('Revenue',         rev_hist,     [r/1e6 for r in proj_rev],    curr_fmt, False),
        ('YoY Growth',      [None,None,None,None], [None]*5,             _pct(),   True),
        ('',                [None]*4,     [None]*5,                      None,     False),
        ('EBITDA',          ebitda_hist,  [r/1e6 for r in proj_ebitda], curr_fmt, False),
        ('EBITDA Margin',   [None]*4,     [None]*5,                      _pct(),   True),
        ('D&A',             da_hist,      [r/1e6 for r in proj_da],     curr_fmt, False),
        ('EBIT',            ebit_hist,    [r/1e6 for r in proj_ebit],   curr_fmt, False),
        ('',                [None]*4,     [None]*5,                      None,     False),
        ('Net Income',      ni_hist,      [r/1e6 for r in proj_ni],     curr_fmt, False),
    ]

    row = 3
    for label, hist_vals, proj_vals, fmt, is_sub in is_rows:
        if label == '':
            row += 1
            continue
        _label(ws_is, row, label, bold=(label in ['Revenue','EBITDA','Net Income']), indent=is_sub)
        for j, v in enumerate(hist_vals, start=2):
            if v is not None and v != 0:
                _cell(ws_is, row, j, v/1e6, fmt=fmt)
        for j, v in enumerate(proj_vals, start=6):
            if v is not None:
                _cell(ws_is, row, j, v, fmt=fmt, fill=INPUT_FILL if fmt else None)
        row += 1

    # ── Sheet 4: Cash Flow Statement ───────────────────────────────────────────
    ws_cf = wb.create_sheet('Cash Flow')
    _setup_sheet(ws_cf, 'Cash Flow', '8b5cf6')
    ws_cf.merge_cells('A1:I1')
    _hdr(ws_cf, 1, 1, f'{ticker.upper()} — Cash Flow Statement ({curr}M)', NAVY_FILL)

    for j, yr in enumerate(all_years, start=2):
        fill = NAVY_FILL if j <= 5 else INPUT_FILL
        fnt  = WH_BOLD if j <= 5 else Font(bold=True, size=10, color='1e40af')
        c = ws_cf.cell(row=2, column=j, value=yr)
        c.font = fnt; c.fill = fill
        c.alignment = Alignment(horizontal='center'); c.border = THIN

    cf_rows = [
        ('Net Income',          ni_hist,    [r/1e6 for r in proj_ni]),
        ('D&A',                 da_hist,    [r/1e6 for r in proj_da]),
        ('Capital Expenditure', [-v for v in capex_hist], [-r/1e6 for r in proj_capex]),
        ('Free Cash Flow',      fcf_hist,   [r/1e6 for r in proj_fcf]),
    ]

    row = 3
    for label, hist_vals, proj_vals in cf_rows:
        bold = label == 'Free Cash Flow'
        _label(ws_cf, row, label, bold=bold)
        for j, v in enumerate(hist_vals, start=2):
            if v is not None and v != 0:
                fc = 'ef4444' if v < 0 else None
                _cell(ws_cf, row, j, v/1e6, fmt=curr_fmt, bold=bold, font_color=fc)
        for j, v in enumerate(proj_vals, start=6):
            fill = GOLD_FILL if bold else INPUT_FILL
            _cell(ws_cf, row, j, v, fmt=curr_fmt, bold=bold, fill=fill)
        row += 1

    # ── Sheet 5: Balance Sheet ──────────────────────────────────────────────────
    ws_bs_sheet = wb.create_sheet('Balance Sheet')
    _setup_sheet(ws_bs_sheet, 'Balance Sheet', '3b82f6')
    ws_bs_sheet.merge_cells('A1:C1')
    _hdr(ws_bs_sheet, 1, 1, f'{ticker.upper()} — Balance Sheet ({curr}M)', NAVY_FILL)
    _hdr(ws_bs_sheet, 2, 1, 'Item', NAVY_FILL)
    _hdr(ws_bs_sheet, 2, 2, 'Latest', NAVY_FILL)

    bs_items = [
        ('ASSETS', None),
        ('Cash & Equivalents',  abs(_safe_get(bs_df, ['Cash And Cash Equivalents', 'CashAndCashEquivalents']))/1e6),
        ('Total Current Assets', abs(_safe_get(bs_df, ['Current Assets', 'TotalCurrentAssets']))/1e6),
        ('Total Assets',         abs(_safe_get(bs_df, ['Total Assets', 'TotalAssets']))/1e6),
        ('',                    None),
        ('LIABILITIES', None),
        ('Short-Term Debt',      abs(st_debt_v)/1e6),
        ('Long-Term Debt',       abs(lt_debt_v)/1e6),
        ('Total Liabilities',    abs(_safe_get(bs_df, ['Total Liabilities Net Minority Interest', 'TotalLiabilitiesNetMinorityInterest']))/1e6),
        ('',                    None),
        ('EQUITY', None),
        ('Total Equity',         abs(_safe_get(bs_df, ['Stockholders Equity', 'StockholdersEquity', 'Total Equity Gross Minority Interest']))/1e6),
        ('',                    None),
        ('Net Debt',             net_debt/1e6),
        ('NAV Per Share',        (_safe_get(bs_df, ['Stockholders Equity', 'StockholdersEquity']) / shares) if shares else 0),
    ]

    row = 3
    for label, val in bs_items:
        if label == '':
            row += 1; continue
        bold = label in ('ASSETS', 'LIABILITIES', 'EQUITY', 'Total Assets', 'Total Liabilities', 'Total Equity')
        fill = NAVY_FILL if label in ('ASSETS','LIABILITIES','EQUITY') else None
        font_c = 'FFFFFF' if label in ('ASSETS','LIABILITIES','EQUITY') else None
        c = ws_bs_sheet.cell(row=row, column=1, value=label)
        c.font = Font(bold=bold, color=font_c or '1a1f35', size=10)
        if fill: c.fill = fill
        c.border = THIN
        if val is not None:
            fmt = curr_fmt if label != 'NAV Per Share' else curr_dec
            fc = 'ef4444' if (val or 0) < 0 else None
            _cell(ws_bs_sheet, row, 2, val, fmt=fmt, bold=bold, font_color=fc)
        row += 1

    # ── Sheet 6: WACC ──────────────────────────────────────────────────────────
    ws_wacc = wb.create_sheet('WACC')
    _setup_sheet(ws_wacc, 'WACC', 'f59e0b', col_a_width=35)
    ws_wacc.merge_cells('A1:C1')
    _hdr(ws_wacc, 1, 1, 'WACC Build-Up', NAVY_FILL)
    _hdr(ws_wacc, 2, 1, 'Component', NAVY_FILL)
    _hdr(ws_wacc, 2, 2, 'Value', NAVY_FILL)
    _hdr(ws_wacc, 2, 3, 'Notes', NAVY_FILL)

    try:
        from api.valuation.wacc_builder import calculate_wacc
        wd = calculate_wacc(ticker, data_fetcher)
    except Exception:
        wd = {}

    wacc_rows = [
        ('Risk-Free Rate',           wd.get('risk_free_rate', 0.04),     _pct(), '10Y Treasury Yield'),
        ('Beta (Levered)',            wd.get('beta_raw', beta),            '0.00', 'From market data'),
        ('Beta (Unlevered)',          wd.get('beta_unlevered', 0.8),       '0.00', 'Hamada equation'),
        ('Equity Risk Premium',       wd.get('equity_risk_premium', 0.055),_pct(), 'Damodaran ERP'),
        ('Cost of Equity (CAPM)',     wd.get('cost_of_equity', ke_val),    _pct(), 'Rf + β × ERP'),
        ('',                          None, None, ''),
        ('Cost of Debt (pre-tax)',     wd.get('cost_of_debt', kd_val),     _pct(), 'Interest / Avg Debt'),
        ('Effective Tax Rate',         wd.get('tax_rate', tax_val),        _pct(), 'Tax / Pre-tax Income'),
        ('Cost of Debt (after-tax)',   kd_val * (1 - tax_val),             _pct(), 'Kd × (1-t)'),
        ('',                          None, None, ''),
        ('Weight — Equity (E/V)',      wd.get('weight_equity', 0.7),       _pct(), 'Market cap / EV'),
        ('Weight — Debt (D/V)',        wd.get('weight_debt', 0.3),         _pct(), 'Debt / EV'),
        ('',                          None, None, ''),
        ('WACC',                       wd.get('wacc', wacc_val),            _pct(), '(E/V)×Ke + (D/V)×Kd×(1-t)'),
    ]

    row = 3
    for label, val, fmt, note in wacc_rows:
        if label == '':
            row += 1; continue
        bold = label == 'WACC'
        fill = GOLD_FILL if bold else None
        _label(ws_wacc, row, label, bold=bold)
        if val is not None:
            _cell(ws_wacc, row, 2, val, fmt=fmt, bold=bold, fill=fill)
        ws_wacc.cell(row=row, column=3, value=note).font = Font(size=9, color='6b7280', italic=True)
        row += 1

    # ── Sheet 7: DCF (FCFF) ────────────────────────────────────────────────────
    ws_dcf = wb.create_sheet('DCF (FCFF)')
    _setup_sheet(ws_dcf, 'DCF (FCFF)', 'f0b429')
    ws_dcf.merge_cells('A1:G1')
    _hdr(ws_dcf, 1, 1, f'{ticker.upper()} — DCF FCFF Valuation ({curr}M)', NAVY_FILL)

    for j, yr in enumerate(years_proj, start=2):
        _hdr(ws_dcf, 2, j, yr)

    dcf_section = [
        ('Revenue',         proj_rev,    curr_fmt),
        ('EBITDA',          proj_ebitda, curr_fmt),
        ('EBIT',            proj_ebit,   curr_fmt),
        ('NOPAT (EBIT×(1-t))', [e*(1-tax_val) for e in proj_ebit], curr_fmt),
        ('+ D&A',           proj_da,     curr_fmt),
        ('- CapEx',         [-c for c in proj_capex], curr_fmt),
        ('Free Cash Flow (FCFF)', proj_fcf, curr_fmt),
    ]

    row = 3
    for label, vals, fmt in dcf_section:
        bold = 'Free Cash Flow' in label
        _label(ws_dcf, row, label, bold=bold)
        for j, v in enumerate(vals, start=2):
            fill = GOLD_FILL if bold else None
            fc = 'ef4444' if (v or 0) < 0 else None
            _cell(ws_dcf, row, j, v/1e6, fmt=fmt, bold=bold, fill=fill, font_color=fc)
        row += 1

    row += 1
    terminal_growth = 0.025
    last_fcf = proj_fcf[-1]
    tv = last_fcf * (1 + terminal_growth) / (wacc_val - terminal_growth) if wacc_val > terminal_growth else 0
    pv_fcfs = [fcf / ((1 + wacc_val) ** (i+1)) for i, fcf in enumerate(proj_fcf)]
    pv_tv   = tv / ((1 + wacc_val) ** 5)
    ev      = sum(pv_fcfs) + pv_tv

    bridge_rows = [
        ('WACC',                    wacc_val,           _pct(),   True),
        ('Terminal Growth Rate',    terminal_growth,    _pct(),   False),
        ('',                        None, None, False),
        ('Sum PV of FCFs',          sum(pv_fcfs)/1e6,   curr_fmt, False),
        ('PV of Terminal Value',    pv_tv/1e6,           curr_fmt, False),
        ('Enterprise Value',        ev/1e6,              curr_fmt, True),
        ('Less: Net Debt',          net_debt/1e6,        curr_fmt, False),
        ('Equity Value',            (ev - net_debt)/1e6, curr_fmt, True),
        ('Shares Outstanding (M)',  shares/1e6,          '#,##0.0',False),
        ('Intrinsic Value / Share', (ev - net_debt)/max(shares, 1), curr_dec, True),
        ('Current Price',           price,               curr_dec, False),
        ('Upside / (Downside)',     ((ev - net_debt)/max(shares,1)/price - 1) if price else 0, _pct(), True),
    ]

    for label, val, fmt, bold in bridge_rows:
        if label == '':
            row += 1; continue
        fill = GOLD_FILL if label in ('Enterprise Value','Equity Value','Intrinsic Value / Share') else None
        fc = 'ef4444' if label == 'Upside / (Downside)' and (val or 0) < 0 else \
             '10b981' if label == 'Upside / (Downside)' and (val or 0) >= 0 else None
        _label(ws_dcf, row, label, bold=bold)
        if val is not None:
            _cell(ws_dcf, row, 2, val, fmt=fmt, bold=bold, fill=fill, font_color=fc)
        row += 1

    # ── Sheet 8: Sensitivity ────────────────────────────────────────────────────
    ws_sens = wb.create_sheet('Sensitivity')
    _setup_sheet(ws_sens, 'Sensitivity', 'ec4899')
    ws_sens.merge_cells('A1:J1')
    _hdr(ws_sens, 1, 1, 'WACC vs Terminal Growth Rate — Implied Price Per Share', NAVY_FILL)

    tg_steps   = [0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040]
    wacc_steps = [wacc_val - 0.020, wacc_val - 0.015, wacc_val - 0.010, wacc_val - 0.005,
                  wacc_val, wacc_val + 0.005, wacc_val + 0.010, wacc_val + 0.015, wacc_val + 0.020]

    ws_sens.cell(row=2, column=1, value='WACC \\ TGR').font = Font(bold=True, size=10)
    for j, tg in enumerate(tg_steps, start=2):
        _hdr(ws_sens, 2, j, f'{tg:.1%}')

    for i, w in enumerate(wacc_steps, start=3):
        ws_sens.cell(row=i, column=1, value=f'{w:.2%}').font = Font(bold=True, size=10)
        for j, tg in enumerate(tg_steps, start=2):
            if w > tg:
                tv_s    = last_fcf * (1 + tg) / (w - tg)
                pv_fcf_s= sum(fcf / ((1+w)**(k+1)) for k, fcf in enumerate(proj_fcf))
                pv_tv_s = tv_s / ((1+w)**5)
                ev_s    = pv_fcf_s + pv_tv_s
                imp_p   = (ev_s - net_debt) / max(shares, 1)
                c = _cell(ws_sens, i, j, round(imp_p, 2), fmt=curr_dec)
                if price > 0:
                    if imp_p > price * 1.1:
                        c.fill = GREEN_FILL
                    elif imp_p < price * 0.9:
                        c.fill = RED_FILL
            else:
                ws_sens.cell(row=i, column=j, value='N/A')

    # ── Save & return ───────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
