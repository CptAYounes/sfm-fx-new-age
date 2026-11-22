"""Pure offline port of the supplied SFM FX Calculator 1.4.0 .deb calculations.

No feed, credentials, execution or account side effects. Values are user estimates.
"""
from decimal import Decimal, InvalidOperation

GROUPS = {
    'Majors': 'EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD',
    'Crosses': 'EURGBP EURJPY EURCHF EURAUD EURCAD EURNZD GBPJPY GBPCHF GBPAUD GBPCAD GBPNZD AUDJPY AUDCHF AUDCAD AUDNZD NZDJPY NZDCHF NZDCAD CADJPY CADCHF CHFJPY',
    'Exotics': 'USDTRY USDZAR USDMXN USDPLN USDCNH USDCNY USDSGD USDHKD USDINR USDKRW USDSEK USDNOK USDDKK USDHUF USDCZK USDTHB USDILS USDRON USDBRL USDCLP USDCOP USDIDR USDMYR USDPHP USDTWD USDAED USDSAR USDEGP USDKZT USDVND EURTRY EURZAR EURMXN EURPLN EURSEK EURNOK EURDKK EURHUF EURCZK EURSGD EURHKD EURCNH GBPTRY GBPZAR GBPMXN GBPPLN GBPSEK GBPNOK GBPSGD AUDSGD NZDSGD SGDJPY HKDJPY NOKSEK SEKJPY NOKJPY ZARJPY MXNJPY TRYJPY CNHJPY',
}
PAIRS = {pair:group for group, names in GROUPS.items() for pair in names.split()}


def calculate(pair,side,entry,exit_price,lots,contract=Decimal('100000'),pip_size=None):
    if pair not in PAIRS: raise ValueError('Choose a supported currency pair.')
    if side not in ('BUY','SELL'): raise ValueError('Choose BUY or SELL.')
    try: entry,exit_price,lots,contract=(Decimal(str(v).strip()) for v in (entry,exit_price,lots,contract))
    except (ValueError,InvalidOperation): raise ValueError('Enter valid numeric prices and lots.') from None
    if any(not v.is_finite() for v in (entry,exit_price,lots,contract)): raise ValueError('Prices and lots must be finite.')
    if entry<=0 or exit_price<=0 or contract<=0: raise ValueError('Prices and contract size must be positive.')
    if lots<Decimal('.01') or lots>1 or lots*100!=(lots*100).to_integral_value():
        raise ValueError('Lots must be 0.01–1.00, in steps of 0.01.')
    try:pip=Decimal(str(pip_size)) if pip_size is not None else Decimal('.01') if pair[3:]=='JPY' else Decimal('.0001')
    except InvalidOperation:raise ValueError('Positive finite pip size required') from None
    if not pip.is_finite() or pip<=0:raise ValueError('Positive finite pip size required')
    delta=(exit_price-entry)*(1 if side=='BUY' else -1);units=lots*contract
    return dict(pnl=delta*units,pips=delta/pip,pip_value=pip*units,units=units,quote=pair[3:],base=pair[:3],pip_size=pip)


def convert_pnl(pnl,quote,account,rate):
    if account in ('Quote currency',quote): return pnl
    try: value=Decimal(str(rate).strip())
    except (ValueError,InvalidOperation): raise ValueError('Enter a positive quote-to-account conversion rate.') from None
    if not value.is_finite() or value<=0: raise ValueError('Conversion rate must be positive and finite.')
    return pnl*value
