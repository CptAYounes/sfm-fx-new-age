"""Shared cached closed-bar chart studies; display only, no signal/execution authority."""
from collections import OrderedDict
from sfm_fx_new_age.contracts.analytics import digest


def moving_average(values,period,*,exponential=False):
    out=[None]*len(values)
    if len(values)<period:return out
    value=sum(values[:period])/period;out[period-1]=value
    for i in range(period,len(values)):
        value=(values[i]*2/(period+1)+value*(1-2/(period+1))) if exponential else value+(values[i]-values[i-period])/period
        out[i]=value
    return out


class ChartStudyService:
    def __init__(self):self.cache=OrderedDict();self.computations=0
    def query(self,rows,identity):
        key=digest([identity,[(r['open_time'],r.get('revision',1),r['close'],r['available_at']) for r in rows]])
        if key not in self.cache:
            values=[float(r['close']) for r in rows]
            self.cache[key]={'SMA 20':moving_average(values,20),'EMA 50':moving_average(values,50,exponential=True)}
            self.computations+=1
            if len(self.cache)>64:self.cache.popitem(last=False)
        else:self.cache.move_to_end(key)
        return {name:list(values) for name,values in self.cache[key].items()}
